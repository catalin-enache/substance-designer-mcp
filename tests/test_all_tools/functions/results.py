"""What functions' set_function checks (checks.py) expect and read: the result's first line, the pixels Python computes
for the normal map they build and for $pos, the pixels node_stats reads, and what describe_graph shows of a function;
and the Pixel Processor a check builds, to call function graphs from or to sample images. How close a pixel must be,
and describe_graph of the graph's nodes: common.py (near, described)."""

import ast
import math
import re

from function_compiler import Constant, Function, Node, Resource, compile_expression, image_input
from test_all_tools.common import Ctx, Json, Ops, near, pixel_values, refs, text
from test_all_tools.functions.parsing import listed_nodes

POINTS = [[0, 0], [3, 3], [5, 2]]  # pixels of the 8 px Pixel Processor: Z is 0, 0.98 and 0.85 there


def built(
    node: str,
    expression: str,
    parameter: str = 'perpixel',
    inputs: dict[str, str] | None = None,
    before: str = '',
    functions: dict[str, Resource] | None = None,
    images: bool = False,
) -> str:
    """set_function's first line for `expression` built on `node`'s `parameter`, replacing the function of the
    expression `before`, if given, of the same `inputs`, and calling the function graphs `functions`; `images` whether
    the node is a processor, which has input images to sample."""
    function = compile_expression(expression, inputs or {}, functions, images=images)
    replaced = compile_expression(before, inputs or {}, images=images) if before else None
    return '%s.%s: %s' % (node, parameter, outcome(function, replaced))


def function_built(
    name: str, inputs: dict[str, str], expression: str, before: tuple[str, dict[str, str]] | None = None
) -> tuple[str, str]:
    """set_function's first line for the function graph `name` with `inputs`, built of `expression`, calling no other
    function graph: what it starts with, and what it ends with. Between them, a new one's line names the package it was
    made in. `before` is the expression it replaced and its inputs (REVIEW.md TST-737)."""
    where = '%s(%s)' % (name, ', '.join('%s %s' % pair for pair in inputs.items()))
    function = compile_expression(expression, inputs, defining=name, images=True)
    replaced = compile_expression(before[0], before[1], defining=name, images=True) if before else None
    return where, ': ' + outcome(function, replaced)


def outcome(function: Function, replaced: Function | None) -> str:
    """What set_function's first line says after the place it built `function`, replacing the nodes of `replaced`."""
    said = 'built %s, its output a %s' % (counted(function['nodes'], 'function node'), function['type'])
    return said + ('; deleted the %s it replaced' % counted(replaced['nodes'], 'node') if replaced else '')


def counted(items: list[Node], what: str) -> str:
    """'1 node', '3 nodes', as set_function says them."""
    return '%d %s%s' % (len(items), what, '' if len(items) == 1 else 's')


def normal(x: int, y: int) -> list[float]:
    """The normal map's R, G, B and A at pixel (x, y) of the 8 px Pixel Processor, as Python computes them: x and y are
    $pos, the pixel's centre over the size, and Z is rebuilt from them taken from -1 to 1."""
    px, py = at(x, y)
    nx, ny = px * 2 - 1, py * 2 - 1
    return [px, py, math.sqrt(max(0.0, 1 - nx * nx - ny * ny)), 1.0]


def all_near(got: dict[tuple[int, int], list[float]], want: dict[tuple[int, int], list[float]]) -> bool:
    """Whether every pixel wanted was read, near its values; never with none wanted, such as a baseline read that failed
    (REVIEW.md TST-722)."""
    return bool(want) and all(near(got.get(p), w) for p, w in want.items())


async def pixels(ctx: Ctx, node: str, points: list[list[int]] = POINTS) -> dict[tuple[int, int], list[float]]:
    """`node`'s values at `points`, read with node_stats: {(x, y): [R, G, B, A]}, or [L] for a grayscale one."""
    return pixel_values(text(await ctx.c('node_stats', {'node_id': node, 'points': points, **ctx.G})))


async def pixel_at(ctx: Ctx, node: str) -> list[float] | None:
    """`node`'s values at pixel (0, 0), as pixels reads them, or None if none were read."""
    return (await pixels(ctx, node)).get((0, 0))


async def sampler(ctx: Ctx, sources: list[str], size_log2: int | None = None) -> dict[str, str]:
    """A Pixel Processor feeding an output, `sources` connected into its input images in order (input, input:1...), of
    2^size_log2 px if given, else the graph's: {'pp': its id, 'out': the output's}."""
    sized: dict[str, Json] = {'params': {'$outputsize': [size_log2, size_log2]}} if size_log2 is not None else {}
    inputs: Ops = [{'op': 'connect', 'from': s, 'to': 'pp', 'input': image_input(k)} for k, s in enumerate(sources)]
    ops: Ops = [
        {'op': 'add', 'definition': 'pixelprocessor', 'ref': 'pp', **sized},
        {'op': 'add', 'definition': 'output', 'ref': 'out'},
        {'op': 'connect', 'from': 'pp', 'to': 'out', 'input': 'inputNodeOutput'},
        *inputs,
    ]
    return refs(text(await ctx.c('apply_edits', {'ops': ops, **ctx.G})))


def differing(t: str, expected: str) -> str:
    """What a check comparing `t` with `expected` prints: the first line of `t` that differs from the line in its place,
    else its last line, past what check() keeps of a long result's head (REVIEW.md TST-747)."""
    got = t.splitlines()
    return next((g for g, w in zip(got, expected.splitlines(), strict=False) if g != w), got[-1] if got else '')


def nothing(node: str, image: str, before: str = '') -> str:
    """What set_function says of `node`'s input image `image` sampled with nothing connected (GUIDE.md, Sampling an
    image), the inputs `before` it to connect first, if any, such as 'input to input:1'."""
    order = ', and into %s before it, in order' % before if before else ''
    return (
        '%s.%s has nothing connected: sampling it reads (0, 0, 0, 0) until an image is connected into it%s '
        "(apply_edits' connect)." % (node, image, order)
    )


def at(x: int, y: int) -> tuple[float, float]:
    """$pos at pixel (x, y) of an 8 px Pixel Processor: the pixel's centre over the size."""
    return (x + 0.5) / 8, (y + 0.5) / 8


def _close(shown: str | None, compiled: Constant | None) -> bool:
    """Whether a constant describe_graph shows (fmt's form, as Python writes it) is the one compiled, floats within
    the 4 decimals fmt keeps."""
    if shown is None or compiled is None:
        return shown is None and compiled is None
    value: object = ast.literal_eval(shown)
    values = value if isinstance(value, tuple) else (value,)
    wanted = compiled if isinstance(compiled, tuple) else (compiled,)
    return len(values) == len(wanted) and all(_same(a, b) for a, b in zip(values, wanted, strict=True))


def _same(shown: object, compiled: object) -> bool:
    """One component: numbers within 1e-4, anything else equal."""
    if isinstance(shown, (int, float)) and isinstance(compiled, (int, float)):
        return abs(shown - compiled) < 1e-4
    return shown == compiled


def function_differs(t: str, function: Function) -> str:
    """How describe_graph's text `t` of a function differs from the compiled `function`: '' when it lists as many nodes,
    its output node the compiled output, and each node, walked from it through its connections, of the compiled kind,
    constant and output type, fed into the same inputs; else the first difference, short enough for a check's line."""
    nodes = listed_nodes(t)
    output = re.search(r'output node (\d+) ', t)
    if output is None or len(nodes) != len(function['nodes']):
        return '%d nodes listed, not %d, or no output node: %s' % (len(nodes), len(function['nodes']), t[:100])
    ids = {function['output']: output.group(1)}
    waiting, seen = [function['output']], set()
    while waiting:
        index = waiting.pop()
        if index in seen:
            continue
        seen.add(index)
        compiled, node = function['nodes'][index], ids[index]
        listed = nodes.get(node)
        instance = compiled['definition'] == 'instance'
        constant = None if instance else compiled['constant']
        kind = 'instance:%s' % compiled['constant'] if instance else compiled['definition']
        want = (kind, compiled['type'], sorted(compiled['inputs']))
        if listed is None or (listed.kind, listed.types, sorted(listed.inputs)) != want:
            return 'node %s is %s, not %s' % (node, listed, want)
        if not _close(listed.constant, constant):
            return 'node %s holds %s, not %r' % (node, listed.constant, constant)
        for input_id, source in compiled['inputs'].items():
            if ids.setdefault(source, listed.inputs[input_id]) != listed.inputs[input_id]:
                return 'node %s: %s fed by %s, not %s' % (node, input_id, listed.inputs[input_id], ids[source])
            waiting.append(source)
    if len(ids) != len(function['nodes']) or len(set(ids.values())) != len(ids):
        return 'the output reaches %d of the %d nodes, as %s' % (len(ids), len(nodes), sorted(ids.items()))
    return ''
