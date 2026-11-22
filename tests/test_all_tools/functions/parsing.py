"""The definitions that functions/designer_scripts/definitions.py prints, read and their shape checked, for functions'
checks (checks.py): another shape is a failed check that says what is wrong, not a KeyError (REVIEW.md TST-699).
pydantic checks the shape against the TypedDicts below. described_definition() reads one in that shape from what
describe_node says of a function node, and described_differs() how it differs from the table's. compiler_table() gives the compiler's table in that shape, and difference() how
one of Designer's definitions differs from the table's, short enough for a check's line. listed_nodes() reads the
nodes describe_graph lists of a function."""

import re
from typing import NamedTuple, TypedDict

from pydantic import TypeAdapter, ValidationError

import function_compiler


class Connector(TypedDict):
    """A definition's input or output, as definitions.py prints it."""

    id: str
    types: list[str]


class Input(Connector):
    connectable: bool


class Definition(TypedDict):
    inputs: list[Input]
    outputs: list[Connector]


DEFINITIONS = TypeAdapter(dict[str, Definition])


def definitions_in(t: str) -> tuple[dict[str, Definition], str]:
    """The definitions in the script's output `t`, by their id without `sbs::function::`, and what is wrong with them:
    '' when nothing is, else the first fault pydantic found, where it is and what, with no definitions."""
    found = re.search(r'^DEFINITIONS=(.*)$', t, re.M)
    if not found:
        return {}, 'no DEFINITIONS= line'
    try:
        # strict: a JSON number isn't taken for a bool, nor a string for a list
        printed = DEFINITIONS.validate_json(found.group(1), strict=True)
    except ValidationError as e:
        first = e.errors()[0]
        return {}, '%s: %s' % ('.'.join(str(part) for part in first['loc']) or 'the whole', first['msg'])
    return {d.removeprefix('sbs::function::'): definition for d, definition in printed.items()}, ''


# an input or output line of describe_node's text of a function node: its id, CONNECTOR for an input that connects,
# then its types
CONNECTOR_LINE = re.compile(r'^  (\S+)\s+(CONNECTOR )?(\S+)')


def described_definition(t: str) -> tuple[Definition | None, str]:
    """The definition describe_node's text `t` gives of a function node: its `outputs:` and `inputs:` lines, each id with
    its types, an input's CONNECTOR saying it connects; and what is wrong with it, '' when nothing is, else None and
    which section is missing."""
    found: dict[str, list[tuple[str, str, bool]]] = {}
    section: list[tuple[str, str, bool]] | None = None
    for line in t.splitlines():
        if line in ('outputs:', 'inputs:'):
            section = found.setdefault(line[:-1], [])
        elif section is not None and (shown := CONNECTOR_LINE.match(line)):
            section.append((shown.group(1), shown.group(3), shown.group(2) is not None))
    missing = [name for name in ('outputs', 'inputs') if name not in found]
    if missing:
        return None, 'no %s: in %s' % (' or '.join(missing), t[:100])
    return {
        'inputs': [
            {'id': i, 'types': types.split(','), 'connectable': connects} for i, types, connects in found['inputs']
        ],
        'outputs': [{'id': i, 'types': types.split(',')} for i, types, _ in found['outputs']],
    }, ''


def compiler_table() -> dict[str, Definition]:
    """function_compiler.DEFINITIONS in the shape definitions.py prints: every input but `__constant__` connectable,
    and one output, `unique_filter_output`."""
    return {
        name: {
            'inputs': [
                {'id': i, 'types': list(types), 'connectable': i != '__constant__'} for i, types in d.inputs.items()
            ],
            'outputs': [{'id': 'unique_filter_output', 'types': list(d.output)}],
        }
        for name, d in function_compiler.DEFINITIONS.items()
    }


def difference(designer: Definition | None, table: Definition | None) -> str:
    """The first way Designer's definition differs from the table's: missing from one, its inputs' ids, one input's
    types or whether it connects, or its outputs."""
    if designer is None or table is None:
        return 'not in Designer' if designer is None else 'not in the table'
    ids = [','.join(p['id'] for p in d['inputs']) for d in (designer, table)]
    if ids[0] != ids[1]:
        return 'inputs: Designer %s; the table %s' % (ids[0], ids[1])
    for mine, theirs in zip(designer['inputs'], table['inputs'], strict=True):
        if mine != theirs:
            shown = [','.join(p['types']) + ('' if p['connectable'] else ', not connectable') for p in (mine, theirs)]
            return 'input %s: Designer %s; the table %s' % (mine['id'], shown[0], shown[1])
    outputs = [' '.join('%s %s' % (p['id'], ','.join(p['types'])) for p in d['outputs']) for d in (designer, table)]
    return 'outputs: Designer %s; the table %s' % (outputs[0], outputs[1])


def described_differs(t: str, table: Definition) -> str:
    """How the definition describe_node's text `t` gives of a function node differs from the table's: '' when it is
    the same, else what is wrong with the text or the first difference (difference())."""
    got, wrong = described_definition(t)
    return wrong or ('' if got == table else difference(got, table))


# a function's node as describe_graph lists it: id, kind, position, then its constant, its output's types and its
# connections, each when it has them
FUNCTION_NODE = re.compile(r'^(\d+) (\S+) @\(-?\d+,-?\d+\)(?: = (.*?))?(?: -> (\S+))?(?:  in: (.*))?$', re.M)


class Listed(NamedTuple):
    """A function's node as describe_graph lists it: its kind, its constant as written (None without one), its output's
    types, and the node feeding each connected input, by the input's id."""

    kind: str
    constant: str | None
    types: str
    inputs: dict[str, str]


def listed_nodes(t: str) -> dict[str, Listed]:
    """The function nodes describe_graph's text `t` lists, by id."""
    return {
        node: Listed(kind, constant or None, types, dict(re.findall(r'(\w+)<-(\d+)\.unique_filter_output', links)))
        for node, kind, constant, types, links in FUNCTION_NODE.findall(t)
    }
