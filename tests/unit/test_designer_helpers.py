"""The helpers are a folder of parts (mcp_server/designer_helpers/) joined into one script that the
server sends to Designer: every part must be in it, once, with core first."""

import ast
import os
from typing import TypeGuard, cast

import pytest

import designer_helpers
from conftest import patch_server, server


def _part_files() -> list[str]:
    return sorted(f[:-3] for f in os.listdir(designer_helpers.HERE) if f.endswith('.py') and f != '__init__.py')


def test_every_part_is_sent_once() -> None:
    # a part file left out of PARTS would silently drop its functions from every call
    assert sorted(designer_helpers.PARTS) == _part_files()
    assert len(set(designer_helpers.PARTS)) == len(designer_helpers.PARTS)


def _parts() -> list[tuple[str, ast.Module]]:
    """[(name, syntax tree)] of every part as it is sent (without its imports of other parts), in PARTS
    order: the script as it is joined."""
    return [(name, ast.parse(designer_helpers.part_source(name))) for name in designer_helpers.PARTS]


_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def _bindings(stmt: ast.AST) -> set[str]:
    """The names a top-level statement binds in the script's namespace: def and class names, import
    aliases, assigned names (any target form) and `except ... as` names, also inside a top-level
    try/if/with/for; not what is local to a function, lambda or comprehension."""
    names: set[str] = set()

    def visit(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
            return
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update((a.asname or a.name).split('.')[0] for a in node.names)
            return
        if isinstance(node, _SCOPES):
            return
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        if isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(stmt)
    return names


def _load_time_uses(stmt: ast.AST) -> set[str]:
    """The names a top-level statement reads while the script loads: module- and class-level code,
    decorators, default values and annotations, not function bodies (those run at call time). A class
    body's own earlier names count as bound inside it (REVIEW.md TST-78)."""
    uses: set[str] = set()
    local: set[str] = set()

    def visit(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            args = node.args
            params = args.posonlyargs + args.args + args.kwonlyargs + [a for a in (args.vararg, args.kwarg) if a]
            evaluated = (
                getattr(node, 'decorator_list', [])
                + args.defaults
                + list(args.kw_defaults)
                + [a.annotation for a in params]
                + [getattr(node, 'returns', None)]
            )
            for child in evaluated:
                if child is not None:
                    visit(child)
            return
        if isinstance(node, ast.ClassDef):
            for child in node.decorator_list + node.bases + node.keywords:
                visit(child)
            own: set[str] = set()
            for child in node.body:
                uses.update(_load_time_uses(child) - own)
                own |= _bindings(child)
            return
        if isinstance(node, ast.comprehension):
            local.update(n.id for n in ast.walk(node.target) if isinstance(n, ast.Name))
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            uses.add(node.id)
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(stmt)
    return uses - local


def _redefined(parts: list[tuple[str, ast.Module]]) -> list[tuple[str, str, str]]:
    """(name, first part, second part) for each name bound by two parts."""
    seen: dict[str, str] = {}
    twice: list[tuple[str, str, str]] = []
    for part, tree in parts:
        for name in set().union(*[_bindings(stmt) for stmt in tree.body]):
            if name in seen:
                twice.append((name, seen[name], part))
            seen.setdefault(name, part)
    return twice


def _used_before_bound(parts: list[tuple[str, ast.Module]]) -> list[tuple[str, str]]:
    """(part, name) for each name read at load time before the script has bound it (in an earlier
    part, or earlier in the same one)."""
    import builtins

    bound: set[str] = set(dir(builtins)) | {'__file__', '__name__', '__doc__'}
    early: list[tuple[str, str]] = []
    for part, tree in parts:
        for stmt in tree.body:
            early += [(part, name) for name in sorted(_load_time_uses(stmt) - bound)]
            bound |= _bindings(stmt)
    return early


def _globals_read(source: str) -> set[str]:
    """The global names a piece of code reads anywhere: at module level and inside its functions,
    lambdas, classes and comprehensions (their own locals left out)."""
    import symtable

    names: set[str] = set()

    def walk(table: symtable.SymbolTable) -> None:
        for symbol in table.get_symbols():
            if symbol.is_referenced() and (
                symbol.is_global()
                if table.get_type() != 'module'
                else not (symbol.is_assigned() or symbol.is_imported())
            ):
                names.add(symbol.get_name())
        for child in table.get_children():
            walk(child)

    walk(symtable.symtable(source, 'part', 'exec'))
    return names


def _import_mismatches(parts: list[tuple[str, str]]) -> list[tuple[str, str, str | None, str | None]]:
    """For [(name, full text)] parts: (part, name, imported from, defined in) for every name a part
    reads from the others that it doesn't import from the part defining it, imports and doesn't
    read, or reads although no part defines it (None)."""
    import builtins

    names = {name for name, _ in parts}

    def from_parts(node: ast.stmt) -> TypeGuard[ast.ImportFrom]:
        return isinstance(node, ast.ImportFrom) and node.level == 1 and node.module in names

    trees = {name: ast.parse(text) for name, text in parts}
    sent = {name: [stmt for stmt in tree.body if not from_parts(stmt)] for name, tree in trees.items()}
    owner: dict[str, str] = {}
    for name, _ in parts:
        for stmt in sent[name]:
            for bound in _bindings(stmt):
                owner.setdefault(bound, name)
    wrong: list[tuple[str, str, str | None, str | None]] = []
    for name, _ in parts:
        imported = {
            a.asname or a.name: stmt.module for stmt in trees[name].body if from_parts(stmt) for a in stmt.names
        }
        own = set().union(*[_bindings(stmt) for stmt in sent[name]])
        read = _globals_read(ast.unparse(ast.Module(body=sent[name], type_ignores=[]))) - own - set(dir(builtins))
        for n in sorted(read | set(imported)):
            if (n in read) != (n in imported) or imported.get(n) != owner.get(n):
                wrong.append((name, n, imported.get(n), owner.get(n)))
    return wrong


def test_each_part_imports_what_it_uses_from_the_others() -> None:
    # the parts are joined into one script, so a name another part defines needs no import to work;
    # the imports are there so editors (PyCharm) and readers see where a name comes from, and this
    # keeps them exact. It also finds a name no part defines (a typo that would fail only in Designer)
    parts: list[tuple[str, str]] = []
    for name in designer_helpers.PARTS:
        with open(os.path.join(designer_helpers.HERE, name + '.py'), encoding='utf-8') as f:
            parts.append((name, f.read()))
    assert _import_mismatches(parts) == []
    assert _relative_imports(designer_helpers.source()) == []


def _relative_imports(source: str) -> list[str]:
    """Every relative import left in a script, at any depth: part_source() drops only the top-level ones,
    and one inside a function would fail in Designer when it runs (REVIEW.md TST-80)."""
    return [
        '%s%s (line %d)' % ('.' * node.level, node.module or '', node.lineno)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.level
    ]


def test_the_import_check_can_fail() -> None:
    parts = [
        ('a', 'X = 1\ndef f():\n    return X'),
        ('b', 'from .a import X, f\ndef g():\n    return f() + X + Y + h()'),  # Y: defined nowhere
        ('c', 'from .a import h\ndef h():\n    pass'),
    ]  # h: from c, not a
    assert _import_mismatches(parts) == [('b', 'Y', None, None), ('b', 'h', None, 'c'), ('c', 'h', 'a', 'c')]
    assert _import_mismatches([('a', 'def f():\n    return 1'), ('b', 'from .a import f\nZ = 2')]) == [
        ('b', 'f', 'a', 'a')
    ]  # imported, never read
    # a part import inside a function: part_source() keeps it, so it is left in the joined script
    nested = 'def g():\n    from .core import X\n    return X'
    assert _import_mismatches([('core', 'X = 1'), ('b', nested)]) == []  # (the check above can't see it)
    assert _relative_imports(nested) == ['.core (line 2)']


def test_the_checks_below_can_fail() -> None:
    # REVIEW.md TST-75, TST-76: each check finds what it is for
    def p(name: str, code: str) -> tuple[str, ast.Module]:
        return name, ast.parse(code)

    assert _redefined(
        [p('a', 'try:\n    import x as f\nexcept ImportError:\n    f = None'), p('b', 'async def f():\n    pass')]
    ) == [('f', 'a', 'b')]
    assert _redefined([p('a', 'A, (B, C) = 1, (2, 3)'), p('b', 'C: int = 4')]) == [('C', 'a', 'b')]
    assert _used_before_bound(
        [p('a', 'TABLE = {"x": later}\n@deco\ndef g(v=LIMIT):\n    return gone'), p('b', 'def later():\n    pass')]
    ) == [('a', 'later'), ('a', 'LIMIT'), ('a', 'deco')]
    assert _used_before_bound([p('a', 'X = [i for i in range(3)]\nY = X')]) == []
    # annotations are evaluated at load time too; a class body sees its own earlier names (REVIEW.md TST-78)
    assert _used_before_bound(
        [p('a', 'def f(x: Later, *a: Rest, k: Kw = 1) -> Back:\n    pass'), p('b', 'Later = Rest = Kw = Back = int')]
    ) == [('a', 'Back'), ('a', 'Kw'), ('a', 'Later'), ('a', 'Rest')]
    assert _used_before_bound([p('a', 'class A(Base):\n    X = 1\n    Y = X + Z'), p('b', 'Base = Z = 1')]) == [
        ('a', 'Base'),
        ('a', 'Z'),
    ]


def test_core_comes_first_and_nothing_else_depends_on_the_order() -> None:
    # REVIEW.md TST-76: core itself (not a slice of the joined text) holds what the others use, and no
    # part reads at load time a name that only a later part binds (__init__.py's claim)
    parts = _parts()
    assert parts[0][0] == 'core'
    assert {'sd', '_APP', '_PM'} <= set().union(*[_bindings(stmt) for stmt in parts[0][1].body])
    assert _used_before_bound(parts) == []


def test_no_name_is_defined_by_two_parts() -> None:
    # one namespace: a second binding silently replaces the first (REVIEW.md TST-75: any binding, not
    # only plain defs and assignments; an import the parts need goes in core, once)
    assert _redefined(_parts()) == []


def _sent_by_tools(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The scripts two tools send to Designer: describe_graph (helpers + call) and apply_edits (an edit,
    the helpers + call wrapped in an undo group, as the argument of compile())."""
    sent: list[str] = []

    def bridge(code: str, path: str | None = None, timeout: float | None = None) -> str:
        sent.append(code)
        return 'ok'

    patch_server(monkeypatch, '_bridge', bridge)
    server.describe_graph('g')
    server.apply_edits([{'op': 'add', 'definition': 'levels'}], graph='g')
    wrapped = next(
        n for n in ast.walk(ast.parse(sent[1])) if isinstance(n, ast.Call) and getattr(n.func, 'id', None) == 'compile'
    )
    return [sent[0], cast(str, cast(ast.Constant, wrapped.args[0]).value)]


def test_tools_send_the_joined_parts_ahead_of_their_call(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-77: comparing server.HELPERS with source() couldn't fail (one is defined as the
    # other); this checks what a tool actually sends, on both paths (plain call, quick edit)
    expected = designer_helpers.source() + '\n\n'
    for code in _sent_by_tools(monkeypatch):
        assert code.startswith(expected) and code[len(expected) :].split('(')[0] in ('describe_graph', 'apply_edits')
    compile(designer_helpers.source(), 'designer_helpers', 'exec')
