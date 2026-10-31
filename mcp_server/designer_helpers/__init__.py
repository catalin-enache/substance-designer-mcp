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
and _PM at load time; nothing else depends on the order.
"""

import ast
import os

PARTS = (
    'core',
    'describe',
    'screenshots',
    'save_export',
    'edits',
    'quit',
    'editor',
    'graph_inputs',
    'batch',
    'sweep',
    'layout',
    'files',
)

HERE = os.path.dirname(os.path.abspath(__file__))


def is_part_import(node: ast.stmt) -> bool:
    """True for a top-level `from .<part> import ...`: an import of another part, for editors only."""
    return isinstance(node, ast.ImportFrom) and node.level == 1 and node.module in PARTS


def part_source(name: str) -> str:
    """One part as it is sent: its text without its imports of other parts."""
    with open(os.path.join(HERE, name + '.py'), encoding='utf-8') as f:
        text = f.read()
    lines = text.split('\n')
    drop: set[int] = set()
    for node in ast.parse(text).body:
        if is_part_import(node):
            drop.update(range(node.lineno - 1, node.end_lineno or node.lineno))
    return '\n'.join(line for i, line in enumerate(lines) if i not in drop)


def source() -> str:
    """The helpers as one script: every part, in PARTS order."""
    return '\n\n'.join(part_source(name) for name in PARTS)
