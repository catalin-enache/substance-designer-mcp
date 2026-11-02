"""A guard for the live self-test (REVIEW.md TST-111, TST-27): a snippet that loads one of Designer's library packages
belongs in a branch that runs only in a Designer the self-test started. It reads the source text, so it sees only one
string naming both `loadUserPackage` and `DefaultResourcesDir`: not a snippet joined by `+`, an f-string or a path
built elsewhere, and not tool calls (`describe_node`, `add` ops), which reuse what is loaded and are undone by
`restore_library_packages`. The self-test's own scratch packages may load anywhere."""

import ast
import re

from conftest import selftest_sources


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


def test_no_snippet_loads_a_library_package_in_the_users_designer() -> None:
    counted = {name: _library_loads(source) for name, source in selftest_sources().items()}
    assert sum(loads for loads, _ in counted.values()) >= 1  # safeguards.py's subfolder check: the guard still sees it
    where = [name for name, (_, outside) in counted.items() if outside]
    assert not where, 'runs in a Designer the user may be working in: %s' % where
