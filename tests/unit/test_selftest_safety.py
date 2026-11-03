"""Guards for the live self-test's source (it reads text, so it runs without Designer): that library packages load only
where it's safe, that scripts sit in the right folder, and that snippets of several lines use dedent, which also covers
the server's modules.

A guard for the live self-test (REVIEW.md TST-111, TST-27): a snippet that loads one of Designer's library packages
belongs in a branch that runs only in a Designer the self-test started. It reads the source text, so it sees only one
string naming both `loadUserPackage` and `DefaultResourcesDir`: not a snippet joined by `+`, an f-string or a path
built elsewhere, and not tool calls (`describe_node`, `add` ops), which reuse what is loaded and are undone by
`restore_library_packages`. The self-test's own scratch packages may load anywhere. A script in designer_scripts/ may
not name both at all, since its load and the branch around it are in two files; a library path it gets through ARGS
goes unseen."""

import ast
import os
import re
import textwrap
from typing import cast

import pytest

import server_tools
from conftest import SELFTEST_DIR, selftest_sources


def _protected(tree: ast.AST) -> set[ast.AST]:
    """Everything that runs only when the self-test started Designer: `if was_running: ... else: <here>` and
    `if not was_running: <here>`."""
    inside: set[ast.AST] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if isinstance(test, ast.Name) and test.id == 'was_running':
            branch = node.orelse
        elif (
            isinstance(test, ast.UnaryOp)
            and isinstance(test.op, ast.Not)
            and isinstance(test.operand, ast.Name)
            and test.operand.id == 'was_running'
        ):
            branch = node.body
        else:
            continue
        for statement in branch:
            inside.update(ast.walk(statement))
    return inside


def _library_loads(source: str) -> tuple[int, int]:
    """(snippets that load a library package, how many of them can run in the user's Designer)."""
    tree = ast.parse(source)
    protected = _protected(tree)
    loads = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and re.search(r'(?<!un)loadUserPackage', n.value)  # not its unload, which the same text is inside
        and 'DefaultResourcesDir' in n.value
    ]
    return len(loads), len([n for n in loads if n not in protected])


LOAD = "'root = app.getPath(DefaultResourcesDir)\\npkg = pm.loadUserPackage(root)'"


def test_the_guard_tells_the_cases_apart() -> None:
    assert _library_loads('c(%s)' % LOAD) == (1, 1)
    assert _library_loads('if was_running:\n    c(%s)\n' % LOAD) == (1, 1)
    assert _library_loads('if was_running:\n    skip()\nelse:\n    c(%s)\n' % LOAD) == (1, 0)
    assert _library_loads('if not was_running:\n    c(%s)\n' % LOAD) == (1, 0)
    assert _library_loads("c('pkg = pm.loadUserPackage(path)')") == (0, 0)  # the self-test's own file
    assert _library_loads("c('root = DefaultResourcesDir\\npm.unloadUserPackage(p)')") == (0, 0)  # only unloads


def _names_a_library_load(text: str) -> bool:
    """A script's whole text naming both: in a real file a load is code, not a string, and the `was_running` branch
    around it would be in the module that runs the script, so `_library_loads` can't judge it."""
    return bool(re.search(r'(?<!un)loadUserPackage', text)) and 'DefaultResourcesDir' in text


@pytest.mark.parametrize(
    'text, named',
    [
        ('root = app.getPath(DefaultResourcesDir)\npkg = pm.loadUserPackage(root)\n', True),
        ('pkg = pm.loadUserPackage(ARGS["path"])\n', False),  # its own scratch file: allowed, and all it can see
        ('root = app.getPath(DefaultResourcesDir)\n', False),
        ('root = app.getPath(DefaultResourcesDir)\npm.unloadUserPackage(p)\n', False),
    ],
)
def test_the_script_guard_tells_the_cases_apart(text: str, named: bool) -> None:
    assert _names_a_library_load(text) == named


def test_no_script_loads_a_library_package() -> None:
    """Such a load stays inline in a module, in a branch that runs only where the self-test started Designer, where the
    guard above can see both (AGENTS.md; REVIEW.md TST-118)."""
    scripts = {
        name: source for name, source in selftest_sources().items() if name.startswith('designer_scripts' + os.sep)
    }
    assert scripts
    assert not [name for name, source in scripts.items() if _names_a_library_load(source)]


def test_no_snippet_loads_a_library_package_in_the_users_designer() -> None:
    counted = {name: _library_loads(source) for name, source in selftest_sources().items()}
    assert sum(loads for loads, _ in counted.values()) >= 1  # safeguards.py's subfolder check: the guard still sees it
    where = [name for name, (_, outside) in counted.items() if outside]
    assert not where, 'runs in a Designer the user may be working in: %s' % where


def test_designer_scripts_are_grouped_by_the_module_that_runs_them() -> None:
    """designer_script(c, '<module>/<script>') from <module>.py, or 'shared/<script>' from more than one module:
    every script exists, sits in the right folder, and is run by something."""
    root = os.path.join(SELFTEST_DIR, 'designer_scripts')
    runners: dict[str, set[str]] = {}
    for name, source in selftest_sources().items():
        module = name.removesuffix('.py')
        for script in re.findall(r"designer_script\(\s*c,\s*'([^']+)'", source):
            assert script.split('/')[0] in (module, 'shared'), '%s runs %s' % (name, script)
            runners.setdefault(script, set()).add(module)
    found = {
        os.path.relpath(os.path.join(folder, f), root).replace(os.sep, '/').removesuffix('.py')
        for folder, _, files in os.walk(root)
        for f in files
        if f.endswith('.py')
    }
    assert set(runners) == found
    for script, modules in runners.items():
        assert not script.startswith('shared/') or len(modules) > 1, '%s is only run by %s' % (script, modules)


def _is_several_lines_of_python(text: str) -> bool:
    """A string of several lines that compiles, with statements other than bare values or NAME=value lines of data:
    not a message, a separator or expected output. %-placeholders count as names. Not caught: an f-string, and code
    built at run time, such as '\\n'.join(lines)."""
    if text.strip().count('\n') < 1:
        return False
    try:
        body = ast.parse(re.sub(r'%%', '%', re.sub(r'%(\(\w+\))?[-.\d]*[rsdfx]', 'x0', text))).body
    except SyntaxError:
        return False
    return any(
        not (isinstance(s, ast.Expr) and not isinstance(s.value, ast.Call))
        and not (
            isinstance(s, ast.Assign)
            and isinstance(s.value, (ast.Name, ast.Constant))
            and all(isinstance(t, ast.Name) and t.id.isupper() for t in s.targets)
        )
        for s in body
    )


def _joined_snippets(source: str) -> list[int]:
    """Lines where Python of several lines is written other than as dedent(\"\"\"...\"\"\"): a plain string, a
    dedent of one, or plain strings joined with +, also beside other values."""
    tree = ast.parse(source)
    dedented = {
        id(n.args[0])
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'dedent'
    }
    written_right = {
        i
        for n in ast.walk(tree)
        if id(n) in dedented
        for i in [id(n)]
        if (ast.get_source_segment(source, n) or '').startswith('"""')
    }
    for n in ast.walk(tree):
        if (
            isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and n.body
            and isinstance(n.body[0], ast.Expr)
        ):
            written_right.add(id(n.body[0].value))  # a docstring

    def leaves(n: ast.AST) -> list[str]:
        """The plain strings of a `+` join, whatever else it holds, each `%`-formatted one included."""
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            return [n.value]
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            return leaves(n.left) + leaves(n.right)
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod):
            return leaves(n.left)
        return []

    lines = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            text = textwrap.dedent(n.value) if id(n) in dedented else n.value
            if id(n) not in written_right and _is_several_lines_of_python(text):
                lines.append(n.lineno)
        elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            parts = leaves(n)
            if len(parts) > 1 and _is_several_lines_of_python(''.join(parts)):
                lines.append(n.lineno)
    return lines


@pytest.mark.parametrize(
    'source, flagged',
    [
        ("x = 'import sd\\nprint(1)\\n'", True),
        ("x = 'import sd\\n' 'print(1)\\n'", True),
        ("x = 'import sd\\n' + 'print(1)\\n'", True),
        ("x = dedent('import sd\\nprint(1)\\n')", True),
        ("x = 'y = %f\\nprint(y)\\n'", True),
        ("x = 'y = %(v)r\\nprint(y)\\n'", True),
        ("x = 'import %s\\nprint(1)\\n'", True),
        ('x = dedent("""\\\n    import sd\n    print(1)\n""")', False),
        ("x = 'print(1)'", False),
        ("x = '\\nprint(1)'", False),
        ("x = 'FILE=x\\nGRAPH=g\\nOPEN=0'", False),
        ("x = 'an error:\\nsomething went wrong'", False),
        ("x = name + 'print(1)\\n'", False),
        ("x = helpers + 'import sd\\n' + 'print(1)\\n'", True),
        ("x = GRAPH_OF % G + 'import sd\\n' + 'print(1)\\n'", True),
        ("x = 'y = %r\\n' % v + 'print(y)\\n'", True),
        ("x = dedent('    import sd\\n    print(1)\\n')", True),
        ('x = helpers + dedent("""\\\n    import sd\n    print(1)\n""") % v', False),
        ("x = '        if self.h:\\n            self.release()'", False),
        ("x = 'an error:\\n' + detail + 'what to do\\n'", False),
        ("x = 'ARGS = load(%r)\\n%s'", True),
    ],
)
def test_the_dedent_guard_tells_the_cases_apart(source: str, flagged: bool) -> None:
    assert bool(_joined_snippets(source)) == flagged


def _dedent_rule_sources() -> dict[str, str]:
    """What the rule is checked in: {name: source} of the self-test's modules and the server's."""
    sources = {name: source for name, source in selftest_sources().items() if os.sep not in name}
    for module in server_tools.MODULES:
        with open(cast(str, module.__file__), encoding='utf-8') as f:
            sources['server_tools/' + os.path.basename(cast(str, module.__file__))] = f.read()
    return sources


def test_the_dedent_rule_reads_every_module_of_both() -> None:
    """Same-named files of the self-test and the server each count (REVIEW.md TST-126)."""
    selftest = [name for name in selftest_sources() if os.sep not in name]
    sources = _dedent_rule_sources()
    assert len(sources) == len(selftest) + len(server_tools.MODULES)
    assert set(selftest) <= set(sources)


def test_a_snippet_of_several_lines_is_written_with_dedent() -> None:
    """dedent(\"\"\"...\"\"\"), not joined pieces with \\n (AGENTS.md): the self-test's modules and every module
    of the server. The scripts in designer_scripts/ are real files, and tests/unit isn't in the rule."""
    sources = _dedent_rule_sources()
    joined = ['%s:%d' % (name, line) for name, source in sources.items() for line in _joined_snippets(source)]
    assert not joined
