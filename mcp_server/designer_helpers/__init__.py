"""
Helpers executed INSIDE Substance Designer (sent over the bridge ahead of each tool call).
They only use Designer's bundled Python and the `sd` API.

The parts in this folder are never imported, here or in Designer: source() joins them, in PARTS
order, into one script that the server sends ahead of each call. So they share one namespace, and a
script that follows can redefine any of their names (the self-test does).

Each part still imports what it uses from the other parts (`from .core import find_graph, ...`, at
the top), so editors and readers see where a name comes from. Those imports can't run in Designer
(the joined script is no package), so part_source() drops them: the names are already there.
tests/unit/test_designer_helpers.py keeps them exact (each name a part uses from another part is
imported, from the part that defines it). core comes first, since the others use its imports, _APP
and _PM at load time. Each other part comes after the parts that bind the names it reads at load time, its annotations'
among them, as describe_functions comes after functions (_Kind, _Typed). tests/unit/test_designer_helpers.py fails on a
part that reads at load time a name only a later part binds.

A part that takes only the standard library's names from the others (state3d) also runs outside Designer, as a module
of its own: standalone() gives it those names, so the tests run the code the helpers hold.
"""

import ast
import functools
import os
import sys
import types

PARTS = (
    'core',
    'describe',
    'waits',
    'screenshots',
    'frames3d',
    'state3d',
    'view3d',
    'scene3d',
    'mac_window',
    'shot3d',
    'save_export',
    'edits',
    'quit',
    'editor',
    'graph_inputs',
    'functions',
    'describe_functions',
    'batch',
    'sweep',
    'layout',
    'files',
)

HERE = os.path.dirname(os.path.abspath(__file__))


def is_part_import(node: ast.stmt) -> bool:
    """True for a top-level `from .<part> import ...`: an import of another part, for editors only."""
    return isinstance(node, ast.ImportFrom) and node.level == 1 and node.module in PARTS


def _text(name: str) -> str:
    """One part's file, as written."""
    with open(os.path.join(HERE, name + '.py'), encoding='utf-8') as f:
        return f.read()


def part_source(name: str) -> str:
    """One part as it is sent: its text without its imports of other parts."""
    text = _text(name)
    lines = text.split('\n')
    drop: set[int] = set()
    for node in ast.parse(text).body:
        if is_part_import(node):
            drop.update(range(node.lineno - 1, node.end_lineno or node.lineno))
    return '\n'.join(line for i, line in enumerate(lines) if i not in drop)


def source() -> str:
    """The helpers as one script: every part, in PARTS order."""
    return '\n\n'.join(part_source(name) for name in PARTS)


def _of_the_standard_library(node: ast.stmt) -> bool:
    """True for a top-level import of the standard library's modules alone."""
    if isinstance(node, ast.Import):
        return all(alias.name.split('.')[0] in sys.stdlib_module_names for alias in node.names)
    return (
        isinstance(node, ast.ImportFrom)
        and not node.level
        and (node.module or '').split('.')[0] in sys.stdlib_module_names
    )


@functools.cache
def standalone(name: str) -> types.ModuleType:
    """The part `name` run outside Designer as a module of its own, for the tests: one module, whoever asks, so its
    classes are one. Each name it imports from another part is bound by that part's own imports of the standard
    library. Raises ImportError for a name the other part binds otherwise: one it defines, or takes from sd or PySide6,
    which only Designer has (state3d takes none)."""
    module = types.ModuleType('designer_helpers.' + name)
    module.__file__ = os.path.join(HERE, name + '.py')
    tree = ast.parse(_text(name))
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or not node.module or not is_part_import(node):
            continue
        other = node.module
        given: dict[str, object] = {}
        imports = [stmt for stmt in ast.parse(_text(other)).body if _of_the_standard_library(stmt)]
        exec(compile(ast.Module(body=imports, type_ignores=[]), other, 'exec'), given)
        for alias in node.names:
            if alias.name not in given:
                raise ImportError(
                    "%s imports %s from %s, which isn't the standard library's there" % (name, alias.name, other)
                )
            vars(module)[alias.asname or alias.name] = given[alias.name]
    # its code without its imports of other parts, at the file's own lines, which tracebacks show (REVIEW.md HLP-262)
    tree.body = [node for node in tree.body if not is_part_import(node)]
    exec(compile(tree, module.__file__, 'exec'), vars(module))
    return module
