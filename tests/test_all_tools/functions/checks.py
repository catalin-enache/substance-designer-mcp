"""Function graphs (ROADMAP item 9): the Designer facts that building and opening one rely on, each script that makes a
package closing it; then set_function on the graph the preparation builds (preparations.py), and the tools reading
functions: describe_graph, describe_node, search_nodes and open_graph."""

import re
from textwrap import dedent

from function_compiler import COMPARISONS, NUMBERS, VARIABLES, Resource, compile_expression, getter_of
from test_all_tools.common import (
    GRAPH_IN_EDITOR,
    TEST_GRAPH,
    Ctx,
    Ops,
    ToolArgs,
    added_id,
    check,
    designer_script,
    is_image,
    picture,
    positions,
    refs,
    text,
)
from test_all_tools.functions.parsing import compiler_table, definitions_in, described_differs, difference
from test_all_tools.functions.preparations import RAMP
from test_all_tools.functions.results import (
    POINTS,
    all_near,
    at,
    built,
    described,
    differing,
    function_built,
    function_differs,
    near,
    normal,
    nothing,
    pixel_at,
    pixels,
    sampler,
)

F = 'designer facts'
S = 'set_function'


ALL = 'int,int2,int3,int4,float,float2,float3,float4'  # what an unconnected add's inputs and output list
ONE = 'raised nothing, 1 connection'  # a connection made and read back on its input
BOTH = '%s; %s' % (ONE, ONE)  # a vector's two components
# the results perpixel computes as black
BLACK = (
    'float2 (0.2, 0.4)',
    'float3 (0.2, 0.4, 0.6)',
    'bool True',
    'int1 1',
    'int2 (1, 1)',
    'int3 (1, 1, 1)',
    'int4 (1, 1, 1, 1)',
)


async def run(ctx: Ctx) -> None:
    await check_the_function_definitions(ctx)
    await check_function_node_types(ctx)
    await check_constants_and_indices(ctx)
    await check_a_processors_function(ctx)
    await check_replacing_a_function(ctx)
    await check_a_pixel_processors_size(ctx)
    await check_a_function_on_a_dollar_parameter(ctx)
    await check_atan2(ctx)
    await check_system_variables(ctx)
    await check_what_nodes_compute(ctx)
    await check_input_values(ctx)
    await check_function_resources(ctx)
    await check_sampling_an_image(ctx)
    await check_a_processors_image_inputs(ctx)
    await check_opening_a_function_in_the_editor(ctx)
    await check_set_function_computes_known_pixels(ctx)
    await check_set_function_on_a_value_processor(ctx)
    await check_a_value_connection_into_a_library_graphs_instance(ctx)
    await check_set_function_reads_an_input_value_in_a_pixel_processor(ctx)
    await check_value_connection_refusals(ctx)
    await check_set_function_on_a_parameter(ctx)
    await check_set_function_keeps_the_nodes_connections_and_parameters(ctx)
    await check_set_function_with_colorswitch_off(ctx)
    await check_set_function_on_a_dollar_parameter(ctx)
    await check_set_function_builds_a_function_graph_a_pixel_processor_calls(ctx)
    await check_dropping_a_function_graphs_input_keeps_the_calls_connections_into_the_others(ctx)
    await check_function_graph_refusals_leave_the_package_unchanged(ctx)
    await check_set_function_samples_with_each_filter_and_wrap(ctx)
    await check_set_function_rebuilds_a_normal_maps_z_from_its_r_and_g(ctx)
    await check_set_function_samples_two_inputs(ctx)
    await check_set_function_samples_in_a_value_processor(ctx)
    await check_set_function_samples_an_input_with_nothing_connected(ctx)
    await check_set_function_refusals_leave_the_graph_unchanged(ctx)
    await check_describe_node_and_search_nodes_know_the_function_nodes(ctx)
    await check_describe_graph_shows_a_processors_function_and_what_feeds_its_input_values(ctx)
    await check_describe_graph_shows_a_value_processors_function_and_says_when_there_is_none(ctx)
    await check_describe_graph_shows_a_parameters_function(ctx)
    await check_describe_graph_lists_a_parameter_set_function_refuses(ctx)
    await check_describe_graph_shows_a_function_graph_of_the_package(ctx)
    await check_open_graph_opens_a_function_graph(ctx)


def said(t: str, label: str) -> str:
    """What the line of `t` starting with `label |` says after it, or a note that there is none."""
    found = re.search(r'^%s \| (.*)$' % re.escape(label), t, re.M)
    return found.group(1) if found else 'no line %r: %s' % (label, t.strip()[-200:])


def expect(t: str, name: str, lines: dict[str, str]) -> None:
    """One check per line of `lines`, {label: what it must say}, named `name: <label>`."""
    for label, expected in lines.items():
        got = said(t, label)
        check(F, '%s: %s' % (name, label), got == expected, got)


async def check_the_function_definitions(ctx: Ctx) -> None:
    """The `sbs::function` module's definitions (functions/designer_scripts/definitions.py) are the compiler's table,
    function_compiler.DEFINITIONS: the same 85, each with its inputs in order, their types, every input but
    `__constant__` connectable, and one output, `unique_filter_output`. A Designer whose definitions changed fails it,
    its line naming the first difference in short, and the other definitions that differ. Printed in another shape, they fail a check saying what is wrong (parsing.py).
    Each has a label and a description, none None or empty, which the helpers guard all the same (REVIEW.md HLP-241:
    core._FunctionDefinition)."""
    c = ctx.c
    t = text(await designer_script(c, 'functions/definitions'))
    defs, wrong_shape = definitions_in(t)
    check(
        F, 'function definitions: the printed definitions have the shape the checks read', not wrong_shape, wrong_shape
    )
    table = compiler_table()
    differ = sorted(name for name in defs.keys() | table.keys() if defs.get(name) != table.get(name))
    detail = ''
    if differ:
        also = '; also %s' % ', '.join(differ[1:]) if differ[1:] else ''
        detail = '%s: %s%s' % (differ[0], difference(defs.get(differ[0]), table.get(differ[0])), also)
    check(
        F, "function definitions: getDefinitions() gives the compiler's table, all %d" % len(table), not differ, detail
    )
    expect(
        t,
        'function definitions',
        {'with no label': '[]', 'with no description': '[]'},
    )


async def check_function_node_types(ctx: Ctx) -> None:
    """The types function nodes list (getTypes()): an unconnected add lists all 8, and getType() only the first; its
    first connection, into a or into b, settles its inputs and output. A connection of another type raises nothing and
    is read back on its input, and an add of a float2 and a float computes the float2 alone."""
    c = ctx.c
    t = text(await designer_script(c, 'functions/function_nodes', part='types'))
    expect(
        t,
        'function node types',
        {
            'add, nothing connected': 'a %s | b %s | out %s | getType int' % (ALL, ALL, ALL),
            'add, a float2 connected': 'a float2 | b float2 | out float2',
            'add, two float2 connected': 'a float2 | b float2 | out float2',
            'add, a float2 into b first': 'a float2 | b float2 | out float2',
            'add, a float2 then a float1 connected': ONE + ' | a float2 | b float2 | out float2',
            'add, a float1 then a float2 connected': ONE + ' | a float | b float | out float',
            'samplecol, a float1 into pos': ONE + ' | pos float2',
            'gt': 'a int,float | b int,float | out bool',
            'ifelse, nothing connected': 'out bool,%s,string,void' % ALL,
            'ifelse, a float3 ifpath': 'elsepath float3 | out float3',
            'dot, a float2 connected': 'a float2 | b float2 | out float',
            'mulscalar, a float3 connected': 'a float3 | scalar float | out float3',
            'add of float2 (0.2, 0.4) and float1 (0.1), computed': '0.20 0.40 0.00 1.00',
            'add of float2 (0.2, 0.4) and float2 (0.1, 0.1), computed': '0.30 0.50 0.00 1.00',
        },
    )


async def check_constants_and_indices(ctx: Ctx) -> None:
    """The value class each const_* node takes on __constant__, and that another raises InvalidType; a swizzle's index
    (0 is x, 3 is w; swizzle2 to swizzle4 take an int2 to int4, one index per component); vector3 and vector4 connect
    components of any size, read back on their inputs, filling the missing ones with 0 and dropping the extra ones."""
    c = ctx.c
    t = text(await designer_script(c, 'functions/function_nodes', part='constants'))
    classes = (
        'bool SDValueBool | float1 SDValueFloat | float2 SDValueFloat2 | float3 SDValueFloat3 | float4 SDValueFloat4 '
        '| int1 SDValueInt | int2 SDValueInt2 | int3 SDValueInt3 | int4 SDValueInt4 | string SDValueString'
    )
    expect(
        t,
        'function constants',
        {
            'const_* __constant__': classes,
            'const_float2 given an SDValueFloat': 'raised APIException SDApiError.InvalidType',
            'const_float1 given an SDValueInt': 'raised APIException SDApiError.InvalidType',
            **{'swizzle1 %d of (0.1, 0.2, 0.3, 0.4)' % i: '%.2f' % (0.1 * (i + 1)) for i in range(4)},
            'swizzle2 (2, 0) of (0.1, 0.2, 0.3, 0.4), then (0.5, 1)': '0.30 0.10 0.50 1.00',
            'swizzle3 (2, 0, 1) of (0.1, 0.2, 0.3, 0.4), then 1': '0.30 0.10 0.20 1.00',
            'swizzle4 (3, 2, 1, 0) of (0.1, 0.2, 0.3, 0.4)': '0.40 0.30 0.20 0.10',
            # componentsin counts from 0.1, componentslast goes on from there; a vector3 is read with a last 1
            'vector4 of 3 and 1 components': BOTH + ' | 0.10 0.20 0.30 0.40',
            'vector4 of 1 and 3 components': BOTH + ' | 0.10 0.20 0.30 0.40',
            'vector4 of 2 and 2 components': BOTH + ' | 0.10 0.20 0.30 0.40',
            'vector4 of 1 and 1 components': BOTH + ' | 0.10 0.20 0.00 0.00',
            'vector4 of 2 and 3 components': BOTH + ' | 0.10 0.20 0.30 0.40',
            'vector3 of 1 and 2 components': BOTH + ' | 0.10 0.20 0.30 1.00',
            'vector3 of 2 and 1 components': BOTH + ' | 0.10 0.20 0.30 1.00',
            'vector3 of 1 and 1 components': BOTH + ' | 0.10 0.20 0.00 1.00',
            'vector3 of 2 and 2 components': BOTH + ' | 0.10 0.20 0.30 1.00',
        },
    )


async def check_a_processors_function(ctx: Ctx) -> None:
    """A new Pixel or Value Processor has no function graph, and a Pixel Processor's colorswitch is on; perpixel lists
    float4 whatever colorswitch says, also with a float output node; what each type of function output computes, by
    colorswitch; a Value Processor's output takes its function's output type."""
    c = ctx.c
    t = text(await designer_script(c, 'functions/function_nodes', part='processors'))
    expect(
        t,
        "a processor's function",
        {
            'a new pixelprocessor': 'perpixel graph None | resource None | colorswitch True',
            'a new valueprocessor': 'function graph None | resource None',
            'perpixel takes': 'colorswitch True float4 | colorswitch False float4 '
            '| a float output node, colorswitch True float4 | a float output node, colorswitch False float4',
            "a Value Processor's output": 'no output node float | float2 float2 | bool bool | int3 int3 | float4 float4 '
            '| function takes bool,%s' % ALL,
            'colorswitch True, perpixel float1 (0.5)': 'RGBA8 0.50 0.50 0.50 1.00',
            'colorswitch True, perpixel float4 (0.2, 0.4, 0.6, 0.8)': 'RGBA8 0.20 0.40 0.60 0.80',
            'colorswitch False, perpixel float1 (0.5)': 'LUM8 0.50',
            # the other types compute black, with colorswitch on or off
            **{
                'colorswitch %s, perpixel %s' % (on, result): black
                for on, black in ((True, 'RGBA8 0.00 0.00 0.00 1.00'), (False, 'LUM8 0.00'))
                for result in BLACK
            },
            # a float4 with colorswitch off: the mean of R, G and B, alpha left out
            'colorswitch False, perpixel float4 (0.2, 0.4, 0.6, 0.8)': 'LUM8 0.40',
            'colorswitch False, perpixel float4 (0.6, 0, 0, 1)': 'LUM8 0.20',
            'colorswitch False, perpixel float4 (0, 0.6, 0, 1)': 'LUM8 0.20',
            'colorswitch False, perpixel float4 (0, 0, 0.6, 1)': 'LUM8 0.20',
            'colorswitch False, perpixel float4 (0, 0, 0, 0.6)': 'LUM8 0.00',
        },
    )


async def check_replacing_a_function(ctx: Ctx) -> None:
    """Three ways of replacing a Pixel Processor's function each keep its connections, its $randomseed and its
    Absolute $outputsize, and compute the new function: the old one was (0.2, 0.4, 0.6, 1), the new one (0.8, 0.6,
    0.4, 1)."""
    c = ctx.c
    t = text(await designer_script(c, 'functions/function_nodes', part='replacements'))
    kept = 'input and output connected True | $randomseed 7 | $outputsize Absolute 3,3 | 1 nodes, output'
    expect(
        t,
        'replacing a function',
        {
            'replaced: untouched': '%s (0.2, 0.4, 0.6, 1) | 8 px 0.20 0.40 0.60 1.00' % kept,
            **{
                'replaced: %s' % way: '%s (0.8, 0.6, 0.4, 1) | 8 px 0.80 0.60 0.40 1.00' % kept
                for way in (
                    'built beside, output moved, old deleted',
                    'old deleted, then built',
                    'deletePropertyGraph, newPropertyGraph',
                )
            },
        },
    )


async def check_a_pixel_processors_size(ctx: Ctx) -> None:
    """A Pixel Processor computes at the graph's size (64 px), not its input's (8 px, as a levels node on it does),
    also with its $outputsize RelativeToInput: only Absolute sets its own."""
    c = ctx.c
    t = text(await designer_script(c, 'functions/function_nodes', part='size'))
    on = 'a Pixel Processor on it, $outputsize '
    expect(
        t,
        "a Pixel Processor's size",
        {
            'the input, Absolute 3,3': '8 px',
            'a levels node on it': '8 px',
            on + 'its default (RelativeToParent 0,0)': '64 px',
            on + 'its default, no input (RelativeToParent 0,0)': '64 px',
            on + 'RelativeToInput 0,0': '64 px',
            on + 'RelativeToInput 1,1': '128 px',
            on + 'Absolute 4,4': '16 px',
        },
    )


async def check_a_function_on_a_dollar_parameter(ctx: Ctx) -> None:
    """A function on a uniform's $outputsize or $format, in a 64 px graph: at the uniform's default inheritance, the
    size it gives is an offset and the format is ignored; made Absolute after the function is built, the function
    stays and both take effect."""
    c = ctx.c
    t = text(await designer_script(c, 'functions/function_nodes', part='dollar'))
    expect(
        t,
        'a function on a $ parameter',
        {
            'a function on $outputsize giving (1, 1), at its default, RelativeToParent': (
                '128 px RGBA8 | the function kept True'
            ),
            'a function on $outputsize giving (1, 1), made Absolute after it': '2 px RGBA8 | the function kept True',
            'a function on $format giving 1, at its default, RelativeToParent': '64 px RGBA8 | the function kept True',
            'a function on $format giving 1, made Absolute after it': '64 px RGBA16 | the function kept True',
        },
    )


async def check_atan2(ctx: Ctx) -> None:
    """atan2's one float2 (x, y) gives atan2(y, x) in radians: read in units of pi/2, (1, 0) gives 0, (0, 1) 1, (-1, 0)
    2 and (0, -1) -1. So y is the second component, componentslast of a vector2."""
    c = ctx.c
    t = text(await designer_script(c, 'functions/function_nodes', part='atan2'))
    expect(
        t,
        'atan2',
        {
            'atan2 of float2 (1, 0), in units of pi/2': '0.0',
            'atan2 of float2 (0, 1), in units of pi/2': '1.0',
            'atan2 of float2 (-1, 0), in units of pi/2': '2.0',
            'atan2 of float2 (0, -1), in units of pi/2': '-1.0',
        },
    )


# the get_* definition reading each `$` variable a computed pixel can show, the compiler's (function_compiler.VARIABLES)
GETTERS = {v: getter_of(VARIABLES[v]) for v in ('$pos', '$size', '$sizelog2', '$tiling')}


async def check_system_variables(ctx: Ctx) -> None:
    """The `$` variables a computed pixel can show, each read with the get_* node the compiler reads it with
    (function_compiler.VARIABLES), in a Pixel Processor of an 8 px graph: `$pos` is the pixel's centre over the size (a
    gradient, y from the top row), `$size` (8, 8), `$sizelog2` (3, 3) and `$tiling` 3, each scaled to fit a pixel. In a
    Value Processor's function, `$pos` reads (0, 0) and `$size` (8, 8) (REVIEW.md SRV-212). In a parameter's, a blend's
    opacitymult, white over black, `$size` reads (8, 8), and `$pos` isn't the pixel's: neither component read at pixel
    (5, 2) is the pixel's (0.69, 0.31), whatever else it reads (SRV-214, TST-758)."""
    c = ctx.c
    t = text(await designer_script(c, 'functions/function_nodes', part='variables', getters=GETTERS))
    expect(
        t,
        'system variables',
        {
            '$pos read with get_float2, at pixel (0, 0)': '0.06 0.06 0.00 1.00',
            '$pos read with get_float2, at pixel (5, 2)': '0.69 0.31 0.00 1.00',
            '$size read with get_float2, over 16': '0.50 0.50 0.00 1.00',
            '$sizelog2 read with get_float2, over 4': '0.75 0.75 0.00 1.00',
            '$tiling read with get_integer1, over 4': '0.75',
            "$pos read with get_float2 in a Value Processor's function": '0.00 0.00',
            "$size read with get_float2 in a Value Processor's function": '8.00 8.00',
            "$size.x over 16 in a blend's opacitymult, at pixel (5, 2)": '0.50 0.50 0.50 1.00',
            "$size.y over 16 in a blend's opacitymult, at pixel (5, 2)": '0.50 0.50 0.50 1.00',
        },
    )
    for component, pixel in zip('xy', at(5, 2), strict=True):
        label = "$pos.%s in a blend's opacitymult, at pixel (5, 2)" % component
        got = said(t, label)
        read = re.match(r'\d\.\d\d ', got)
        elsewhere = read is not None and not near([float(read.group())], [pixel])
        check(F, "system variables: %s, not the pixel's position" % label, elsewhere, got)


async def check_what_nodes_compute(ctx: Ctx) -> None:
    """What the nodes the compiler builds compute, each of asymmetric constants, against the value Python gives: the
    order of a vector's components and of a swizzle's, the operands' order on floats and float2, the maths functions,
    the comparisons, ifelse's paths, lerp's x, cartesian's angle, a product of two vectors, and how a cast to int
    rounds. rand of 0.1 is checked for its range, and rand of 1 for its values varying from pixel to pixel. Where
    Designer differs, with negative ints, the line holds Designer's value. A result that can be negative or above 1 is
    shifted first, as its label says. A bool is read as 1 or 0 (an ifelse, measured too), each node with a true and a
    false cell, so that one computing nothing shows. The comparisons' labels take their operators from the compiler's
    (function_compiler.COMPARISONS), so a label left without its line means the compiler maps another."""
    c = ctx.c
    symbols = dict(COMPARISONS.values())
    t = text(await designer_script(c, 'functions/function_nodes', part='computed', symbols=symbols))
    true, false = '1.00', '0.00'
    expect(
        t,
        'what nodes compute',
        {
            # vectors and swizzles
            'vector2 of 0.1 and 0.2': '0.10 0.20 0.00 1.00',
            'ivector2 of 1 and 2, over 4': '0.25 0.50 0.00 1.00',
            'ivector3 of 1 and (2, 3), over 4': '0.25 0.50 0.75 1.00',
            'ivector4 of (1, 2) and (3, 5), over 10': '0.10 0.20 0.30 0.50',
            'iswizzle1 2 of (1, 2, 3), over 4': '0.75',
            'iswizzle2 (1, 0) of (1, 2, 3), over 4': '0.50 0.25 0.00 1.00',
            'iswizzle3 (2, 0, 1) of (1, 2, 3), over 4': '0.75 0.25 0.50 1.00',
            'iswizzle4 (3, 2, 1, 0) of (1, 2, 3, 5), over 10': '0.50 0.30 0.20 0.10',
            # arithmetic
            'sub 0.7 - 0.2': '0.50',
            'div 0.2 / 0.8': '0.25',
            'pow 0.5 ** 2': '0.25',
            'mod 0.7 % 0.4': '0.30',
            'mod -0.3 % 1, then (x + 1) / 2': '0.85',
            'sub of (0.7, 0.9) - (0.2, 0.1)': '0.50 0.80 0.00 1.00',
            'div of (0.2, 0.3) / (0.8, 0.5)': '0.25 0.60 0.00 1.00',
            'mod of (0.7, 0.9) % (0.4, 0.5)': '0.30 0.40 0.00 1.00',
            'pow of (0.5, 0.9) ** (2, 1)': '0.25 0.90 0.00 1.00',
            'min of (0.7, 0.1) and (0.2, 0.6)': '0.20 0.10 0.00 1.00',
            'max of (0.7, 0.1) and (0.2, 0.6)': '0.70 0.60 0.00 1.00',
            # an int can't hold Python's 3.5: truncated, as C does
            'div of ints 7 / 2, then (x + 5) / 10': '0.80',
            'mul of (0.2, 0.5) and (0.5, 0.4)': '0.10 0.20 0.00 1.00',
            'mulscalar of (0.2, 0.6) and 0.5': '0.10 0.30 0.00 1.00',
            'lerp from 0.2 to 0.6 at 0.25': '0.30',
            'cartesian of rho 0.5 and theta pi/3': '0.25 0.43 0.00 1.00',
            # maths functions: angles in radians, log the natural one
            'abs -0.3': '0.30',
            'sqrt 0.25': '0.50',
            'sin pi/6': '0.50',
            'cos pi/3': '0.50',
            'tan 0.4': '0.42',
            'exp -1.2': '0.30',
            'log 1.5': '0.40',
            'log2 1.5': '0.58',
            'floor -0.3, then (x + 2) / 4': '0.25',
            'ceil -0.3, then (x + 2) / 4': '0.50',
            'neg 0.3, then (x + 1) / 2': '0.35',
            'min 0.7, 0.2': '0.20',
            'max 0.2, 0.7': '0.70',
            'dot of (0.2, 0.5) and (0.5, 0.4)': '0.30',
            # choices and comparisons
            'ifelse true, 0.2, 0.7': '0.20',
            'ifelse false, 0.2, 0.7': '0.70',
            'lr 0.2 < 0.7': true,
            'lr 0.7 < 0.7': false,
            'lreq 0.7 <= 0.7': true,
            'lreq 0.7 <= 0.2': false,
            'gt 0.7 > 0.2': true,
            'gt 0.7 > 0.7': false,
            'gteq 0.7 >= 0.7': true,
            'gteq 0.2 >= 0.7': false,
            'eq 0.7 == 0.7': true,
            'eq 0.2 == 0.7': false,
            'noteq 0.2 != 0.7': true,
            'noteq 0.7 != 0.7': false,
            'and true, false': false,
            'and true, true': true,
            'or true, false': true,
            'not true': false,
            'not false': true,
            # casts: Python's int() truncates
            'toint1 1.7, then (x + 5) / 10': '0.60',
            'toint1 2.5, then (x + 5) / 10': '0.70',
            'toint2 of (1.7, 2.2), over 10': '0.10 0.20 0.00 1.00',
            'toint3 of (1.7, 2.2, 3.9), over 10': '0.10 0.20 0.30 1.00',
            'toint4 of (1.7, 2.2, 3.9, 5.5), over 10': '0.10 0.20 0.30 0.50',
            'lr of ints 1 < 2': true,
            # negative ints compute wrong values (macOS arm64): -7 reads back as 5 or more, -1 isn't below 1, neg of 3
            # and 7 / -2 give 0, -7 % 3 is 0, toint1 of a negative gives 0, and 2 - 5 gives 5 or more. Python's
            # values, its division truncated as int() does, are 0 (clamped), 1, 0.2, 0.2, 0.7, 0.4 and 0.2. These lines
            # hold macOS arm64's values and run on every platform: a failure elsewhere is the sign that Designer
            # differs there (the user, 2026-11-22)
            'tofloat of int -7, then (x + 5) / 10': '1.00',
            'lr of ints -1 < 1': false,
            'neg of int 3, then (x + 5) / 10': '0.50',
            'div of ints 7 / -2, then (x + 5) / 10': '0.50',
            'mod of ints -7 % 3, then (x + 5) / 10': '0.50',
            'toint1 -1.7, then (x + 5) / 10': '0.50',
            'sub of ints 2 - 5, then (x + 5) / 10': '1.00',
        },
    )
    got = said(t, 'rand of 0.1, then x + 0.5')
    in_range = re.fullmatch(r'\d\.\d\d', got) is not None and 0.5 <= float(got) <= 0.6
    check(F, 'what nodes compute: rand of 0.1, from 0 to 0.1', in_range, got)
    # varying from pixel to pixel: more than 8 values among the 16 pixels (REVIEW.md SRV-208)
    got = said(t, 'rand of 1, at each of the 16 pixels')
    varies = re.fullmatch(r'\d+ values', got) is not None and int(got.split()[0]) > 8
    check(F, 'what nodes compute: rand of 1, varying from pixel to pixel', varies, got)


async def check_input_values(ctx: Ctx) -> None:
    """A node's input values, `#name`, which a value connects into and its functions read: newProperty makes one, a
    connector of the type given, `#` added to a name without one, of each type a Value Processor's output gives; a
    Value Processor connects into it by that id, a second one replacing the first; what an image or a value of another
    type does there; a get_* node of `#name` reads it in a parameter's function, a Pixel Processor's and a Value
    Processor's, and what the wrong getter, a missing name, nothing connected (never, or after a disconnect) and a
    source whose type changed read; and whether the drive survives a save and a reload, read from the file. Each blend
    is white over black, so its pixel is its opacity."""
    c = ctx.c
    t = text(await designer_script(c, 'functions/function_nodes', part='values'))

    def grey(v: float) -> str:
        return '%.2f %.2f %.2f 1.00' % (v, v, v)

    expect(
        t,
        'input values',
        {
            "newProperty('#x', a float)": 'id #x | connectable True | listed True | types float',
            "newProperty('y', a float)": 'id #y | connectable True | listed True | types float',
            "newProperty('#v', a float2 Value Processor's output type)": 'id #v | connectable True | listed True '
            '| types float2',
            'newProperty with the type of each output a Value Processor gives': ' | '.join(
                '%s %s' % (t, t) for t in ('bool', *NUMBERS)
            ),
            'a Value Processor into #x': ONE,
            "a Value Processor into 'x'": 'raised APIException SDApiError.ItemNotFound',
            'a second Value Processor into #x': ONE + ' | from the second True',
            "a uniform's image into a float #t": ONE,
            'a float2 Value Processor into a float #m': ONE,
            'opacitymult reading #x, the Value Processor at 0.25': grey(0.25),
            'opacitymult reading #x, the second Value Processor at 0.5': grey(0.5),
            # an image, or a value of another type, connects and computes the opacity's default, 1, not the value
            "opacitymult's default": '1.00',
            'opacitymult reading #t, an image': grey(1),
            'opacitymult reading #m, a float2 (0.2, 0.4)': grey(1),
            'a Pixel Processor reading its #x': grey(0.25),
            # neither (0.25, 0) nor zeros: the wrong getter computes a wrong value
            'a Pixel Processor reading a float #f with get_float2, in a vector4 with (0, 1)': '0.00 1.00 0.00 0.00',
            'a Pixel Processor reading #nope + 0.5, which it lacks': grey(0.5),
            'a Value Processor reading its #x': '0.25',
            # with nothing connected, as for a mismatch, the opacity computes 1, not a value
            'opacitymult reading #u, with nothing ever connected': grey(1),
            # + 0.5: 0.5 if it reads 0, 0 if the function gives no value (REVIEW.md SRV-196)
            'a Pixel Processor reading its #u + 0.5, with nothing ever connected': grey(0.5),
            'a Value Processor reading its #u + 0.5, with nothing ever connected': '0.50',
            'opacitymult reading #d, the Value Processor at 0.25 connected': grey(0.25),
            'opacitymult reading #d, after a disconnect': grey(1),
            'a Pixel Processor reading its #e + 0.5, after a disconnect': grey(0.5),
            'a Value Processor reading its #e + 0.5, after a disconnect': '0.50',
            'a Value Processor feeding #c, its function changed to a float4': '1 connection | #c types float | its '
            'output float4',
            'opacitymult reading #c, its source changed to a float4': grey(1),
            'opacitymult reading #x, the Value Processor at 0.75': grey(0.75),
            'after a save and a reload, #x': 'listed True | types float | 1 connection, from the Value Processor True '
            '| the function kept True',
            'after a save and a reload, the Value Processor at 0.75, as saved': grey(0.75),
            'after a save and a reload, the Value Processor set to 0.5': grey(0.5),
        },
    )


async def check_function_resources(ctx: Ctx) -> None:
    """Function graphs stored in the package, which set_function's `function` builds and an expression calls by name
    (functions/designer_scripts/function_nodes.py, part `resources`): what sNew and setIdentifier make, a taken
    identifier included; the inputs newProperty makes on one; what decides its output's type; what an instance node of
    one shows and computes in a Pixel Processor; what replacing its nodes, inputs and output does to an instance
    calling it; a save and a reload; delete(). Then more kinds of calls (REVIEW.md TST-733): int and bool inputs, bool
    and int outputs, the `$` variables read inside, a float3 input left unconnected, a Value Processor's and a
    parameter's function calling one, an input deleted between two others, the ids newProperty keeps, and the inputs'
    order after the reload."""
    c = ctx.c
    t = text(await designer_script(c, 'functions/function_nodes', part='resources', getters=GETTERS))
    paint = 'definition sbs::function::instance | inputs uv float2, k float | outputs unique_filter_output float4'
    expect(
        t,
        'function resources',
        {
            'a new function graph, given the identifier paint': 'paint | inputs none | outputs none | type SDSBSFunctionGraph',
            'a second one given paint': 'paint_1',
            "one given the compositing graph's identifier": 'mcp_selftest_function_nodes_1',
            "newProperty('uv', a float2)": 'id uv | types float2',
            'its inputs, uv then k': 'uv float2, k float',
            'newProperty of each type': 'b bool | i1 int | i2 int2 | i3 int3 | i4 int4 | f1 float | f2 float2 '
            '| f3 float3 | f4 float4 | s string',
            # a function graph has no output of its own: its output node's type is what an instance gives
            'its output, by its output node': 'const_float2: none, type SDSBSFunctionGraph '
            '| const_bool: none, type SDSBSFunctionGraph | const_int3: none, type SDSBSFunctionGraph',
            'paint given a float4 output node': 'outputs none | type SDSBSFunctionGraph',
            'an instance node of paint in a Pixel Processor': paint + ' | connected uv 0, k 0 | resource paint',
            'the instance, uv and k connected': paint + ' | connected uv 1, k 1 | resource paint',
            'paint(uv (0.2, 0.4), k 0.6) in a Pixel Processor': '0.20 0.40 0.60 1.00',
            'paint(uv (0.2, 0.4)), k left unconnected': '0.20 0.40 0.00 1.00',
            'where(), reading $pos at pixel (0, 0) of 4 px': '0.13 0.13 0.00 1.00',
            'outer(uv (0.2, 0.4)), calling paint(uv, 0.6)': '0.20 0.40 0.60 1.00',
            'paint replaced after a compute, built beside: (uv.y, uv.x, k * 0.5, 1)': '0.40 0.20 0.30 1.00',
            'paint given an input extra': 'its inputs uv float2, k float, extra float | the instance definition '
            'sbs::function::instance | inputs uv float2, k float, extra float | outputs unique_filter_output float4 '
            '| connected uv 1, k 1, extra 0 | resource paint',
            # the instance follows the function's inputs, its connection into k gone with k; an input of the instance
            # then lists no types until a reload
            'paint without its input k': 'its inputs uv float2, extra float | the instance definition '
            'sbs::function::instance | inputs uv float2, extra  | outputs unique_filter_output float4 '
            '| connected uv 1, extra 0 | resource paint',
            'paint without k, which its body still reads': '0.40 0.20 0.00 1.00',
            # uv deleted and made again: its connection is gone
            'paint with uv made a float3': 'its inputs extra float, uv float3 | the instance definition '
            'sbs::function::instance | inputs extra , uv float3 | outputs unique_filter_output float4 '
            '| connected extra 0, uv 0 | resource paint',
            'paint given a float output node': 'the instance definition sbs::function::instance | inputs extra , uv  '
            '| outputs unique_filter_output float | connected extra 0, uv 0 | resource paint',
            'paint giving a float 0.5': '0.50 0.50 0.50 1.00',
            'a function deleted with delete()': 'mcp_selftest_function_nodes SDSBSCompGraph, paint SDSBSFunctionGraph, '
            'paint_1 SDSBSFunctionGraph, mcp_selftest_function_nodes_1 SDSBSFunctionGraph, kinds SDSBSFunctionGraph, '
            'where SDSBSFunctionGraph, outer SDSBSFunctionGraph',
            'after a save and a reload, the instance': 'definition sbs::function::instance | inputs extra float, uv '
            'float3 | outputs unique_filter_output float | connected extra 0, uv 0 | resource paint',
            'after a save and a reload, paint giving a float 0.5': '0.50 0.50 0.50 1.00',
            # more kinds of calls (REVIEW.md TST-733): int and bool inputs, bool and int outputs, the variables read
            # inside, a vector input left unconnected, a Value Processor's and a parameter's function calling one
            'ib(i 3, b true) = b ? i / 4 : 0.1, in a Pixel Processor': '0.75 0.75 0.75 1.00',
            'ib(i 3, b false)': '0.10 0.10 0.10 1.00',
            'big(0.7) = 0.7 > 0.5, a bool, in an ifelse giving 0.8 or 0.2': '0.80 0.80 0.80 1.00',
            'big: its call gives': 'unique_filter_output bool',
            'three() = 3, an int, over 4': '0.75 0.75 0.75 1.00',
            'three: its call gives': 'unique_filter_output int',
            'size16() = float4($size / 16, 0, 1), in a 4 px Pixel Processor': '0.25 0.25 0.00 1.00',
            'log4() = float4($sizelog2 / 4, 0, 1)': '0.50 0.50 0.00 1.00',
            'tiling4() = float($tiling) / 4': '0.75 0.75 0.75 1.00',
            # + 0.25: a result a Pixel Processor can't show is black too (REVIEW.md TST-739)
            'vec(v) = float4(v + 0.25, 1), its float3 v left unconnected': '0.25 0.25 0.25 1.00',
            'half(x 0.6) = x * 0.5, a Value Processor calling it': '0.30',
            "half(x 0.6), a blend's opacitymult calling it, white over black": '0.30 0.30 0.30 1.00',
            'two(y 0.2, x 0.6) = float4(y, x, 0, 1)': '0.20 0.60 0.00 1.00',
            # an input deleted between two others: the call keeps its connection into the next (REVIEW.md HLP-233)
            'abc(a 0.2, b 0.4, c 0.6) = float4(a, b, c, 1)': '0.20 0.40 0.60 1.00',
            'abc without b: the call': 'inputs a float, c float | connected a 1, c 1',
            'abc without b, which its body still reads': '0.20 0.00 0.60 1.00',
            # input ids newProperty is given and the ids it makes (REVIEW.md HLP-235)
            "newProperty's ids for Uv, _k, k_, a1, x_2": 'Uv float, _k float, k_ float, a1 float, x_2 float',
            'after a save and a reload, two': 'inputs y float, x float',
            'after a save and a reload, two(y 0.2, x 0.6)': '0.20 0.60 0.00 1.00',
        },
    )


ZEROS = '0.00 0.00 0.00 0.00'  # what a sample of an input with no image reads


async def check_sampling_an_image(ctx: Ctx) -> None:
    """samplecol and samplelum (functions/designer_scripts/function_nodes.py, part `sampling`) in a 4 px graph,
    sampling a Pixel Processor whose float4($pos, 0.5, 1) makes columns of R 0.13, 0.38, 0.62 and 0.87, and rows of G
    alike. __constant__ is (the input's index, the mode). Read at x -0.1, 0.3, 0.7 and 1.1 of the top row, mode 0 is
    nearest and repeats, 1 bilinear and repeats, 2 nearest and clamps, 3 bilinear and clamps. samplelum gives the mean
    of R, G and B. pos is in $pos's frame, (x, y) from 0 to 1 from the top-left. Index 1 reads input:1; an index with
    nothing connected, or beyond the inputs, reads (0, 0, 0, 0). A function graph a Pixel Processor calls samples the
    caller's inputs, and a Value Processor's function samples its own, through a call too. A new node's __constant__ is
    (0, 0). Index 39 of 40 inputs connected reads input:39. samplecol's modes read along y as along x. With input alone
    connected, index 70, 2147483647 (the largest __constant__ holds: 2147483648 wraps around to -2147483648) and -1
    each read (0, 0, 0, 0), and Designer answers after them (REVIEW.md SRV-201)."""
    t = text(await designer_script(ctx.c, 'functions/function_nodes', part='sampling', getters=GETTERS))
    answers = text(await ctx.c('execute_designer_code', {'code': "print('ANSWERS')"}))
    check(F, 'sampling an image: Designer answers after the large indices', 'ANSWERS' in answers, answers)
    at_xs = ': R at x -0.1, 0.3, 0.7, 1.1'
    expect(
        t,
        'sampling an image',
        {
            'samplecol, mode 0' + at_xs: '0.87 0.38 0.62 0.13',
            'samplecol, mode 1' + at_xs: '0.80 0.30 0.70 0.20',
            'samplecol, mode 2' + at_xs: '0.13 0.38 0.62 0.87',
            'samplecol, mode 3' + at_xs: '0.13 0.30 0.70 0.87',
            'samplelum, mode 0' + at_xs: '0.50 0.33 0.42 0.25',
            'samplelum, mode 1' + at_xs: '0.47 0.31 0.44 0.27',
            'samplelum, mode 2' + at_xs: '0.25 0.33 0.42 0.50',
            'samplelum, mode 3' + at_xs: '0.25 0.31 0.44 0.50',
            # along y too (REVIEW.md TST-742): the column's G, as R along x
            **{
                'samplecol, mode %d: G at y -0.1, 0.3, 0.7, 1.1' % mode: row
                for mode, row in enumerate(
                    ('0.87 0.38 0.62 0.13', '0.80 0.30 0.70 0.20', '0.13 0.38 0.62 0.87', '0.13 0.30 0.70 0.87')
                )
            },
            'samplecol at (0.875, 0.125)': '0.87 0.13 0.50 1.00',
            'samplecol at (0.125, 0.875)': '0.13 0.87 0.50 1.00',
            'samplecol at $pos: pixels (1, 2) and (3, 0)': '0.38 0.62 0.50 1.00 | 0.87 0.13 0.50 1.00',
            'samplelum of the colour (0.9, 0.1, 0.3)': '0.43 0.43 0.43 1.00',
            'samplecol, index 1: input:1, the colour (0.9, 0.1, 0.3)': '0.90 0.10 0.30 1.00',
            'samplecol, index 2: input:2, nothing connected': ZEROS,
            'samplecol, index 5: beyond the inputs': ZEROS,
            'samplecol, index 0: nothing connected': ZEROS,
            'samplecol, index 1: input:1 disconnected, input:2 still connected': ZEROS,
            'samplecol, index 2: input:2, the colour (0.2, 0.7, 0.4), after the disconnected input:1': (
                '0.20 0.70 0.40 1.00'
            ),
            'a function graph sampling index 1 at its uv (0.875, 0.125), called from a Pixel Processor': (
                '0.90 0.10 0.30 1.00'
            ),
            'a Value Processor sampling index 0 at (0.875, 0.125)': '0.87 0.13 0.50 1.00',
            'a Value Processor sampling index 1': '0.90 0.10 0.30 1.00',
            'a Value Processor calling the function graph sampling index 1': '0.90 0.10 0.30 1.00',
            "a new samplecol's and samplelum's __constant__": '0,0 | 0,0',
            'samplecol, index 39 of 40 inputs: input:39, the colour (0.2, 0.7, 0.4)': '0.20 0.70 0.40 1.00',
            # large indices and a negative one, with input connected (REVIEW.md SRV-201): what __constant__ holds,
            # and what each reads
            '__constant__ given (2147483647, 0), then (2147483648, 0), then (-1, 0)': (
                '2147483647,0 | -2147483648,0 | -1,0'
            ),
            'samplecol, index 70: input connected only': ZEROS,
            'samplecol, index 2147483647: input connected only': ZEROS,
            'samplecol, index -1: input connected only': ZEROS,
        },
    )


async def check_a_processors_image_inputs(ctx: Ctx) -> None:
    """A Pixel and a Value Processor's input images (functions/designer_scripts/function_nodes.py, part
    `image_inputs`), each fact for each (REVIEW.md TST-742): newProperty makes none, and the API says its input isn't
    variadic. A new one lists input; each connection makes the next input appear, input:1, input:2..., empty, up to
    input:40 after 40, and one into an input it doesn't list raises ItemNotFound. An input disconnected stays listed
    while a later one is connected; with the later ones disconnected, the list ends with one empty input after the last
    connected. The connections survive a save and a reload."""
    t = text(await designer_script(ctx.c, 'functions/function_nodes', part='image_inputs'))
    invalid = 'raised APIException SDApiError.InvalidType'
    not_found = 'raised APIException SDApiError.ItemNotFound | input 0'
    each = {
        "newProperty, of its input's type": 'input:1 %s | input %s | input1 %s' % (invalid, invalid, invalid),
        'its input, isVariadic': 'False',
        'a new one': 'input 0',
        'input connected': ONE + ' | input 1, input:1 0',
        'input:1 connected': ONE + ' | input 1, input:1 1, input:2 0',
        'a new one, input:1 connected first': not_found,
        'a new one, input:3 connected first': not_found,
        'input, input:1 and input:2 connected': 'input 1, input:1 1, input:2 1, input:3 0',
        'input:1 disconnected': 'input 1, input:1 0, input:2 1, input:3 0',
        'input:2 disconnected too': 'input 1, input:1 0',
        'input disconnected, input:1 kept': 'input 0, input:1 1, input:2 0',
        '40 connected': '41 listed, the last input:40 0',
    }
    expect(
        t,
        "a processor's image inputs",
        {
            **{
                '%s: %s' % (kind, fact): said
                for kind in ('a Pixel Processor', 'a Value Processor')
                for fact, said in each.items()
            },
            'after a save and a reload, the three of a Pixel Processor, then the Value Processor': (
                'input 1, input:1 1, input:2 1, input:3 0 | input 1, input:1 1, input:2 0'
            ),
        },
    )


async def check_opening_a_function_in_the_editor(ctx: Ctx) -> None:
    """What openResourceInEditor opens (functions/designer_scripts/function_nodes.py, part `editor`), open_graph's
    `function` and its refusal of a node's function rely on: a function graph of the package opens, current in the
    editor, the graph panel titled with its identifier; a Pixel Processor's perpixel function and a levels node's
    leveloutlow function open the node's graph instead, from the function graph too. The self-test graph is opened
    first, which closes Designer's Home screen if it shows."""
    c = ctx.c
    await c('open_graph', {**ctx.G})
    t = text(await designer_script(c, 'functions/function_nodes', part='editor'))
    graph = "SDSBSCompGraph mcp_selftest_function_nodes | panel 'mcp_selftest_function_nodes'"
    function = "SDSBSFunctionGraph probe_fn | panel 'probe_fn'"
    expect(
        t,
        'opening a function in the editor',
        {
            'opened the graph': graph,
            'opened its function graph probe_fn': function,
            "opened then a Pixel Processor's perpixel function": graph,
            'opened probe_fn again': function,
            "opened then a levels node's leveloutlow function": graph,
        },
    )


# ROADMAP item 31's normal map, its Z rebuilt from x and y: here $pos's, from -1 to 1. A sampled normal map's is
# check_set_function_rebuilds_a_normal_maps_z_from_its_r_and_g's
Z = 'xy = $pos * 2 - 1; sqrt(max(0, 1 - dot(xy, xy)))'
NORMAL = 'xy = $pos * 2 - 1; float4(xy * 0.5 + 0.5, sqrt(max(0, 1 - dot(xy, xy))), 1)'


async def check_set_function_computes_known_pixels(ctx: Ctx) -> None:
    """The Pixel Processor's perpixel: Z alone is a float, grey with colorswitch on, as Python computes it at three
    pixels. Replaced after that compute by the whole normal, a float4, the pixels read again are the normal's, so a
    function left stale shows."""
    c, G = ctx.c, ctx.G
    t = text(await c('set_function', {'expression': Z, 'node_id': ctx.pp, **G}))
    expected = built(ctx.pp, Z) + '\ncolorswitch is on: the float is grey.'
    check(S, "a Pixel Processor's float: the result says what was built and how it shows", t == expected, t)
    got = await pixels(ctx, ctx.pp)
    want = {(x, y): [normal(x, y)[2]] * 3 + [1.0] for x, y in POINTS}
    check(
        S,
        "a Pixel Processor's float: the pixels are Z, grey",
        all_near(got, want),
        str(got),
    )
    t = text(await c('set_function', {'expression': NORMAL, 'node_id': ctx.pp, **G}))
    expected = built(ctx.pp, NORMAL, before=Z) + '\ncolorswitch is on: the float4 is the colour.'
    check(S, "a Pixel Processor's float4: the result says what was built and how it shows", t == expected, t)
    got = await pixels(ctx, ctx.pp)
    want = {(x, y): normal(x, y) for x, y in POINTS}
    check(
        S,
        "a function replaced after a compute: the pixels are the new one's",
        all_near(got, want),
        str(got),
    )


async def check_set_function_keeps_the_nodes_connections_and_parameters(ctx: Ctx) -> None:
    """Replacing a function keeps the node's connections and other parameters: the Pixel Processor's to its output, its
    $randomseed and its Absolute $outputsize (8 px in the 16 px graph), and the levels node's input and levelinhigh.
    Each replacing call's result says what it built and what it deleted; describe_graph shows the nodes as before, and
    node_stats the Pixel Processor's size."""
    c, G = ctx.c, ctx.G
    nodes = [ctx.pp, ctx.out, ctx.lv]
    old_pp, old_lv, new_pp, new_lv = '0.25', 'tint * 0.25', 'float4($pos, 0, 1)', 'tint * 0.5'
    lows: ToolArgs = {'node_id': ctx.lv, 'parameter': 'leveloutlow', **G}
    await c('set_function', {'expression': old_pp, 'node_id': ctx.pp, **G})
    await c('set_function', {'expression': old_lv, **lows})
    before = await described(ctx, nodes)
    pp_said = text(await c('set_function', {'expression': new_pp, 'node_id': ctx.pp, **G}))
    lv_said = text(await c('set_function', {'expression': new_lv, **lows}))
    # describe_graph shows "<- a function" for any function: each call's result says it replaced one (REVIEW.md TST-756)
    check(
        S,
        'each replacing call built the new function, deleting the nodes of the one it replaced',
        pp_said.startswith(built(ctx.pp, new_pp, before=old_pp))
        and lv_said.startswith(built(ctx.lv, new_lv, 'leveloutlow', {'tint': 'float4'}, before=old_lv)),
        '%s / %s' % (pp_said, lv_said),
    )
    after = await described(ctx, nodes)
    kept = all(
        line in after
        for line in (
            '$randomseed = 7',
            '$outputsize = (3, 3)',
            'perpixel <- a function',
            'inputNodeOutput<-%s.unique_filter_output' % ctx.pp,
            'in: input1<-',
            'levelinhigh = (0.9, 0.9, 0.9, 1.0)',
            'leveloutlow <- a function',
        )
    )
    check(S, "replacing a function keeps the node's connections and other parameters", kept and before == after, after)
    sized = text(await c('node_stats', {'node_id': ctx.pp, **G})).splitlines()[0]
    check(S, 'replacing a function keeps an Absolute $outputsize', sized.endswith(': 8x8 RGBA8'), sized)


async def check_set_function_on_a_value_processor(ctx: Ctx) -> None:
    """A Value Processor drives the blend's opacity, white over black, through the tools (REVIEW.md TST-719): its
    function, from the graph input tint, gives 0.25, a float; a connect into the blend's #v makes that input value, a
    float; opacitymult's function reads #v. node_stats reads the blend at 0.25, then at 0.75 once the processor's
    function changes, and describe_graph shows the connection and the function."""
    c, G = ctx.c, ctx.G
    expression = 'tint.x * 0.625'
    t = text(await c('set_function', {'expression': expression, 'node_id': ctx.vp, 'parameter': 'function', **G}))
    expected = (
        built(ctx.vp, expression, 'function', {'tint': 'float4'}) + "\nThe Value Processor's output is a float now."
    )
    check(S, "a Value Processor's function: the result says its output's type", t == expected, t)
    t = text(await c('apply_edits', {'ops': [{'op': 'connect', 'from': ctx.vp, 'to': ctx.blend, 'input': '#v'}], **G}))
    made = 'connected %s.unique_filter_output -> %s.#v; made #v, an input value of type float' % (ctx.vp, ctx.blend)
    check(S, "a value connection: the connect makes the input value #v, of the output's type", made in t, t)
    t = text(await c('set_function', {'expression': '#v', 'node_id': ctx.blend, 'parameter': 'opacitymult', **G}))
    expected = built(ctx.blend, '#v', 'opacitymult', {'#v': 'float'})
    check(S, 'a value connection: set_function reads #v in a parameter', t == expected, t)
    got = await pixel_at(ctx, ctx.blend)
    check(
        S,
        "a value connection: the Value Processor's 0.25 is the blend's opacity",
        near(got, [0.25] * 3 + [1]),
        str(got),
    )
    await c('set_function', {'expression': '0.75', 'node_id': ctx.vp, **G})
    got = await pixel_at(ctx, ctx.blend)
    check(S, 'a value connection: the opacity follows the Value Processor, 0.75', near(got, [0.75] * 3 + [1]), str(got))
    graph = await described(ctx, [ctx.blend])
    shown = all(
        line in graph for line in ('#v<-%s.unique_filter_output' % ctx.vp, "opacitymult <- a function reading '#v'")
    )
    check(S, 'a value connection: describe_graph shows the connection and the function', shown, graph)


# whether the library package of contrast_luminosity_grayscale reads as modified, and whether its graph has #v
LIBRARY_STATE = dedent("""
    graph = _library_graph('contrast_luminosity.sbs/contrast_luminosity_grayscale')
    inputs = [p.getId() for p in graph.getProperties(SDPropertyCategory.Input)]
    print('modified %s | #v in its graph %s' % (graph.getPackage().isModified(), '#v' in inputs))""")


async def check_a_value_connection_into_a_library_graphs_instance(ctx: Ctx) -> None:
    """A connect from a Value Processor into #v on an instance of a library graph, contrast_luminosity_grayscale, makes
    #v on the node alone: the library graph has none after it, and its package doesn't read as modified (REVIEW.md
    HLP-247). The instance's Luminosity, its function reading #v, lifts its black input to 0.3 once the processor gives
    0.3, from 0 at 0."""
    c, G = ctx.c, ctx.G
    ops: Ops = [
        {'op': 'add', 'definition': 'valueprocessor', 'ref': 'vp'},
        {'op': 'add', 'definition': 'contrast_luminosity.sbs/contrast_luminosity_grayscale', 'ref': 'cl'},
        {'op': 'add', 'definition': 'output', 'ref': 'out'},
        {'op': 'connect', 'from': 'cl', 'to': 'out', 'input': 'inputNodeOutput'},
    ]
    added = refs(text(await c('apply_edits', {'ops': ops, **G})))
    try:
        await c('set_function', {'expression': '0', 'node_id': added['vp'], **G})
        t = text(
            await c(
                'apply_edits', {'ops': [{'op': 'connect', 'from': added['vp'], 'to': added['cl'], 'input': '#v'}], **G}
            )
        )
        await c('set_function', {'expression': '#v', 'node_id': added['cl'], 'parameter': 'Luminosity', **G})
        dark = await pixel_at(ctx, added['cl'])
        await c('set_function', {'expression': '0.3', 'node_id': added['vp'], **G})
        lit = await pixel_at(ctx, added['cl'])
        state = text(await c('execute_designer_code', {'code': ctx.helper_source + LIBRARY_STATE})).strip()
        made = 'made #v, an input value of type float' in t and state == 'modified False | #v in its graph False'
        check(
            F,
            "#v on a library graph's instance: made on the node alone, the library left unchanged",
            made,
            '%s | %s' % (t, state),
        )
        followed = near(dark, [0.0]) and near(lit, [0.3])
        check(
            S,
            "a library graph's instance reads #v: its Luminosity follows the Value Processor",
            followed,
            '%s, then %s' % (dark, lit),
        )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in added.values()], **G})


async def check_set_function_reads_an_input_value_in_a_pixel_processor(ctx: Ctx) -> None:
    """A Pixel Processor's perpixel reads the input value #w a Value Processor connects into it: the processor at 0.5,
    float4(#w, #w * 0.5, 0, 1) computes (0.5, 0.25, 0, 1). The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    ops: Ops = [
        {'op': 'add', 'definition': 'pixelprocessor', 'ref': 'reader'},
        {'op': 'add', 'definition': 'output', 'ref': 'out'},
        {'op': 'connect', 'from': 'reader', 'to': 'out', 'input': 'inputNodeOutput'},
        {'op': 'connect', 'from': ctx.vp, 'to': 'reader', 'input': '#w'},
    ]
    added = refs(text(await c('apply_edits', {'ops': ops, **G})))
    reader = added['reader']
    try:
        await c('set_function', {'expression': '0.5', 'node_id': ctx.vp, **G})
        expression = 'float4(#w, #w * 0.5, 0, 1)'
        t = text(await c('set_function', {'expression': expression, 'node_id': reader, **G}))
        expected = built(reader, expression, inputs={'#w': 'float'}) + '\ncolorswitch is on: the float4 is the colour.'
        check(S, 'a Pixel Processor reading #w: the result says what was built', t == expected, t)
        got = await pixel_at(ctx, reader)
        check(
            S,
            "a Pixel Processor reading #w: the pixels are the Value Processor's",
            near(got, [0.5, 0.25, 0.0, 1.0]),
            str(got),
        )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in added.values()], **G})


# a Value Processor's function given a float4 output node outside the tools, as a person could in Designer's UI
TO_FLOAT4 = dedent("""
    g = find_graph(%r)
    vp = _node(g, %r)
    fn = vp.getPropertyGraph(vp.getPropertyFromId('function', SDPropertyCategory.Input))
    fn.setOutputNode(_new_node(fn, 'sbs::function::const_float4'), True)
    print('OUTPUT', _type(vp.getProperties(SDPropertyCategory.Output)[0]).getId())""")


async def check_value_connection_refusals(ctx: Ctx) -> None:
    """A float2 Value Processor drives the blend's opacity through #p, a float2 the connect makes, read as #p.y: 0.4.
    A connect into an input value refuses, changing nothing, read with describe_graph: a value of another type (a
    float2 Value Processor into the blend's float #m), an image (the Pixel Processor's) and a name set_function couldn't
    read. A connect into an input value of its type takes it as it is. set_function refuses a #name the node lacks,
    naming those it has, which leave out the image's #img, the blend unchanged. It refuses what Designer would read
    wrongly (GUIDE.md, Input values): the processor's float4 for the #p it drives; #p fed another type, the processor
    made a float4 outside the tools; #p with nothing connected, after a disconnect. That the server's refusals build
    nothing, the unit tests show. The float2 Value Processor is deleted after it."""
    c, G = ctx.c, ctx.G
    pair = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'valueprocessor'}], **G})))
    read_p: ToolArgs = {'expression': '#p.y', 'node_id': ctx.blend, 'parameter': 'opacitymult', **G}

    try:
        t = text(await c('set_function', {'expression': 'float2(0.2, 0.4)', 'node_id': pair, **G}))
        check(S, "a Value Processor's float2: the result says so", t.endswith('output is a float2 now.'), t)
        t = text(
            await c('apply_edits', {'ops': [{'op': 'connect', 'from': pair, 'to': ctx.blend, 'input': '#p'}], **G})
        )
        check(
            S,
            'a float2 value connection: the connect makes #p a float2',
            'made #p, an input value of type float2' in t,
            t,
        )
        await c('set_function', read_p)
        got = await pixel_at(ctx, ctx.blend)
        check(S, "a float2 value connection: #p.y reads the processor's 0.4", near(got, [0.4] * 3 + [1]), str(got))
        into_m: Ops = [{'op': 'connect', 'from': ctx.vp, 'to': ctx.blend, 'input': '#m'}]
        await c('apply_edits', {'ops': into_m, **G})
        t = text(await c('apply_edits', {'ops': into_m, **G}))
        again = 'connected %s.unique_filter_output -> %s.#m\n' % (ctx.vp, ctx.blend)
        check(S, 'a connect into an input value of its type takes it as it is', again in t and 'made' not in t, t)
        before = await described(ctx, [ctx.blend])
        refusals = [
            (
                'a float2 into a float input value',
                {'from': pair, 'input': '#m'},
                '%s.#m is an input value of type float, and %s.unique_filter_output gives type float2'
                % (ctx.blend, pair),
            ),
            ('an image into an input value', {'from': ctx.pp, 'input': '#img'}, 'not a value'),
            ('a name set_function could not read', {'from': ctx.vp, 'input': '#1x'}, "input value '#1x'"),
        ]
        for what, fields, says in refusals:
            r = await c('apply_edits', {'ops': [{'op': 'connect', 'to': ctx.blend, **fields}], **G})
            same = await described(ctx, [ctx.blend]) == before
            refused = r.is_error and says in text(r)
            check(
                S,
                'a value connection refuses %s, the graph unchanged' % what,
                refused and same,
                '%s | %s' % (text(r)[-200:], same),
            )
        r = await c('set_function', {'expression': '#img', 'node_id': ctx.blend, 'parameter': 'opacitymult', **G})
        listed = text(r).split('; its input values are ')
        named = r.is_error and listed[0].endswith('the node has no input value `#img`') and '#m' in listed[-1]
        # a function built of the one get would show, as "opacitymult <- a function reading '#img'"
        kept = named and '#img' not in listed[-1] and await described(ctx, [ctx.blend]) == before
        check(S, 'set_function refuses a #name the node lacks, naming those it has, the graph unchanged', kept, text(r))
        r = await c('set_function', {'expression': 'float4(0.2, 0.4, 0, 1)', 'node_id': pair, **G})
        says = "%s's output drives %s.#p, an input value of type float2, and the expression gives a float4"
        check(
            S,
            "refuses a Value Processor's result unlike an input value it drives",
            says % (pair, ctx.blend) in text(r),
            text(r),
        )
        changed = text(await c('execute_designer_code', {'code': ctx.helper_source + TO_FLOAT4 % (TEST_GRAPH, pair)}))
        r = await c('set_function', read_p)
        says = '%s.#p is an input value of type float2, and %s.unique_filter_output, connected into it, gives float4'
        fed = 'OUTPUT float4' in changed and r.is_error and says % (ctx.blend, pair) in text(r)
        check(S, 'refuses a #name fed another type, naming both', fed, '%s | %s' % (changed[-80:], text(r)[-200:]))
        await c('apply_edits', {'ops': [{'op': 'disconnect', 'node': ctx.blend, 'input': '#p'}], **G})
        r = await c('set_function', read_p)
        says = '%s.#p has nothing connected: connect a value into it first' % ctx.blend
        check(
            S, "a parameter's function refuses a #name with nothing connected", r.is_error and says in text(r), text(r)
        )
        # the disconnect the drive refusal names lifts it (REVIEW.md SRV-195)
        t = text(await c('set_function', {'expression': 'float4(0.2, 0.4, 0, 1)', 'node_id': pair, **G}))
        check(S, 'the disconnect a drive refusal names lifts it', t.endswith('output is a float4 now.'), t)
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': pair}], **G})


async def check_set_function_on_a_parameter(ctx: Ctx) -> None:
    """A levels node's leveloutlow, a float4, from the graph input tint, a colour read as a float4: tint * 0.5 lifts
    the levels of a black input to (0.2, 0.3, 0.4) in R, G and B, and describe_graph shows the parameter driven by a
    function."""
    c, G = ctx.c, ctx.G
    t = text(await c('set_function', {'expression': 'tint * 0.5', 'node_id': ctx.lv, 'parameter': 'leveloutlow', **G}))
    expected = built(ctx.lv, 'tint * 0.5', 'leveloutlow', {'tint': 'float4'})
    check(S, "a parameter's function: the result says what was built", t == expected, t)
    got = await pixel_at(ctx, ctx.lv)
    check(S, "a parameter's function: the levels show it", near(got[:3] if got else None, [0.2, 0.3, 0.4]), str(got))
    graph = await described(ctx, [ctx.lv])
    check(S, "a parameter's function: describe_graph shows it", 'leveloutlow <- a function' in graph, graph)


async def check_set_function_with_colorswitch_off(ctx: Ctx) -> None:
    """A Pixel Processor with colorswitch off computes grayscale: a float is the value, and a float4 (0.2, 0.4, 0.6,
    0.8) the mean of R, G and B, 0.4. Each result line says so. The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    ops: Ops = [
        {'op': 'add', 'definition': 'pixelprocessor', 'ref': 'grey', 'params': {'colorswitch': False}},
        {'op': 'add', 'definition': 'output', 'ref': 'out'},
        {'op': 'connect', 'from': 'grey', 'to': 'out', 'input': 'inputNodeOutput'},
    ]
    added = refs(text(await c('apply_edits', {'ops': ops, **G})))
    grey = added['grey']
    try:
        for expression, value, shown in (
            ('0.5', 0.5, 'colorswitch is off: the float is the grayscale value.'),
            (
                'float4(0.2, 0.4, 0.6, 0.8)',
                0.4,
                'colorswitch is off: the float4 is averaged to grey (the mean of R, G and B, alpha left out).',
            ),
        ):
            t = text(await c('set_function', {'expression': expression, 'node_id': grey, **G}))
            check(S, 'colorswitch off, %s: the result says how it shows' % expression, t.endswith('\n' + shown), t)
            got = await pixel_at(ctx, grey)
            check(S, 'colorswitch off, %s: the pixel is %.1f' % (expression, value), near(got, [value]), str(got))
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in added.values()], **G})


SIZE_REFUSED = 'log2 of the size in pixels (0 is 1 px, 11 is 2048 px, 13 is 8192 px, the largest), not (15, 15)'


async def check_set_function_on_a_dollar_parameter(ctx: Ctx) -> None:
    """A function on a uniform's $outputsize or $format takes effect, the parameter made Absolute as apply_edits' set
    does: int2(2, 2) makes it 4 px in the 16 px graph (inherited, an offset: 64 px), and int(1) 16 bits per channel
    (inherited, ignored). A constant size above 13 is refused with set's message, the size left as it was. The nodes
    are deleted after it."""
    c, G = ctx.c, ctx.G
    ops: Ops = [
        {'op': 'add', 'definition': 'uniform', 'ref': 'u'},
        {'op': 'add', 'definition': 'output', 'ref': 'out'},
        {'op': 'connect', 'from': 'u', 'to': 'out', 'input': 'inputNodeOutput'},
    ]
    added = refs(text(await c('apply_edits', {'ops': ops, **G})))
    u = added['u']
    try:
        t = text(await c('set_function', {'expression': 'int2(2, 2)', 'node_id': u, 'parameter': '$outputsize', **G}))
        check(S, '$outputsize: the result says it is Absolute, a log2 size', 'Absolute now' in t and 'log2' in t, t)
        t = text(await c('set_function', {'expression': 'int(1)', 'node_id': u, 'parameter': '$format', **G}))
        check(S, '$format: the result says it is Absolute', 'Absolute now' in t, t)
        r = await c('set_function', {'expression': 'int2(15, 15)', 'node_id': u, 'parameter': '$outputsize', **G})
        check(S, '$outputsize: a constant size above 13 is refused', r.is_error and SIZE_REFUSED in text(r), text(r))
        # one compute for the three: a size built from the refused 15 would show 8192 px
        got = text(await c('node_stats', {'node_id': u, **G})).splitlines()[0]
        check(
            S,
            '$outputsize and $format: the functions give 4 px and 16 bits, the size kept',
            got.endswith(': 4x4 RGBA16'),
            got,
        )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in added.values()], **G})


PAINT = 'float4(uv, k, 1)'
PAINT_INPUTS = {'uv': 'float2', 'k': 'float'}


async def check_set_function_builds_a_function_graph_a_pixel_processor_calls(ctx: Ctx) -> None:
    """set_function's `function` makes the function graph paint(uv, k) = (uv, k, 1) in the graph's package, and a Pixel
    Processor's perpixel calls paint($pos, 0.6): its pixels are ($pos, 0.6, 1). paint replaced, its inputs kept, while
    the processor calls it, the pixels are the new function's, and the result names nothing calling it. Its input k
    left out, the result names the processor, which calls it; the call keeps its connection into uv, the first input,
    kept. The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    added = await sampler(ctx, [], size_log2=3)
    pp = added['pp']
    try:
        t = text(await c('set_function', {'expression': PAINT, 'function': 'paint', 'inputs': PAINT_INPUTS, **G}))
        where, built_and_output = function_built('paint', PAINT_INPUTS, PAINT)
        made = t.startswith(where + ', a new function graph of ') and t.endswith(built_and_output) and '\n' not in t
        check(S, 'a function graph made: the result gives its identifier, inputs and output', made, t)
        package = {'paint': Resource(PAINT_INPUTS, 'float4', ())}
        call = 'paint($pos, 0.6)'
        t = text(await c('set_function', {'expression': call, 'node_id': pp, **G}))
        expected = built(pp, call, functions=package) + '\ncolorswitch is on: the float4 is the colour.'
        check(S, 'a call of a function graph: the result says what was built', t == expected, t)
        got = await pixels(ctx, pp)
        check(
            S,
            "a call of a function graph: the pixels are its function's",
            all_near(got, {(x, y): [*at(x, y), 0.6, 1.0] for x, y in POINTS}),
            str(got),
        )
        swapped = 'float4(uv.y, uv.x, k * 0.5, 1)'
        t = text(await c('set_function', {'expression': swapped, 'function': 'paint', **G}))
        expected = ''.join(function_built('paint', PAINT_INPUTS, swapped, before=(PAINT, PAINT_INPUTS)))
        check(S, 'a function graph replaced: the result says what it replaced, and names no caller', t == expected, t)
        got = await pixels(ctx, pp)
        check(
            S,
            "a function graph replaced while a Pixel Processor calls it: the pixels are the new function's",
            all_near(got, {(x, y): [at(x, y)[1], at(x, y)[0], 0.3, 1.0] for x, y in POINTS}),
            str(got),
        )
        t = text(
            await c(
                'set_function',
                {'expression': 'float4(uv, 0.5, 1)', 'function': 'paint', 'inputs': {'uv': 'float2'}, **G},
            )
        )
        names = "paint's inputs or output changed, and %s/%s.perpixel calls it" % (TEST_GRAPH, pp)
        check(S, 'a function graph losing an input: the result names what calls it', names in t, t)
        got = await pixels(ctx, pp)
        check(
            S,
            "a function graph losing its second input: a call's connection into the first stays",
            all_near(got, {(x, y): [*at(x, y), 0.5, 1.0] for x, y in POINTS}),
            str(got),
        )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in added.values()], **G})


# the package's function graphs, each with its inputs, its output node's types and how many nodes it has, and how many
# resources the package has: what a refusal must leave as it was
FUNCTION_GRAPHS = dedent("""
    pkg = find_graph(%r).getPackage()
    for f in pkg.getChildrenResources(True):
        if isinstance(f, SDSBSFunctionGraph):
            outs = [[t.getId() for t in o.getPropertyFromId('unique_filter_output', SDPropertyCategory.Output).getTypes()]
                    for o in f.getOutputNodes()]
            ins = [(p.getId(), p.getType().getId()) for p in f.getProperties(SDPropertyCategory.Input)]
            print('FUNCTION_GRAPH', f.getIdentifier(), ins, outs, len(f.getNodes()))
    print('RESOURCES', len(pkg.getChildrenResources(True)))""")


DROPS: list[tuple[str, str, dict[str, str], list[float]]] = [
    ('the middle one dropped', 'float4(a, 0.5, c, 1)', {'a': 'float', 'c': 'float'}, [0.2, 0.5, 0.6, 1.0]),
    ('the first one dropped too', 'float4(0.3, 0.5, c, 1)', {'c': 'float'}, [0.3, 0.5, 0.6, 1.0]),
]


async def check_dropping_a_function_graphs_input_keeps_the_calls_connections_into_the_others(ctx: Ctx) -> None:
    """set_function's `function` dropping a function graph's middle input, then its first, keeps a call's connections
    into the others (REVIEW.md TST-738; GUIDE.md, Function graphs of the package): drop(a, b, c) = (a, b, c, 1), called
    from a Pixel Processor as drop(0.2, 0.4, 0.6), gives (0.2, 0.5, 0.6, 1) once b is dropped for a 0.5, then
    (0.3, 0.5, 0.6, 1) once a is dropped too. A connection lost would read 0. The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    added = await sampler(ctx, [], size_log2=3)
    pp = added['pp']
    three = {'a': 'float', 'b': 'float', 'c': 'float'}
    try:
        await c('set_function', {'expression': 'float4(a, b, c, 1)', 'function': 'drop', 'inputs': three, **G})
        await c('set_function', {'expression': 'drop(0.2, 0.4, 0.6)', 'node_id': pp, **G})
        got = await pixel_at(ctx, pp)
        check(S, "a function graph's three inputs, each connected by a call", near(got, [0.2, 0.4, 0.6, 1.0]), str(got))
        for what, expression, inputs, want in DROPS:
            await c('set_function', {'expression': expression, 'function': 'drop', 'inputs': inputs, **G})
            got = await pixel_at(ctx, pp)
            check(
                S,
                "a function graph's input, %s: the call's connections into the others stay" % what,
                near(got, want),
                str(got),
            )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in added.values()], **G})


async def check_function_graph_refusals_leave_the_package_unchanged(ctx: Ctx) -> None:
    """Each refusal of a function graph, or of a call of one, says what is wrong and leaves the package as it was: its
    function graphs read in Designer (FUNCTION_GRAPHS), and the pixels of a Pixel Processor calling wrap($pos.x), with
    wrap(v) = shade(v) + 0.25 and shade(v) = v * 0.5. Refused: a function graph named like the grammar's function or
    cast; one calling itself, directly or through another; an identifier the package's compositing graph has; an input
    of a type no input takes; a call with too few arguments, or one of another type, for which the pixels are read
    again. The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    added = await sampler(ctx, [], size_log2=3)
    pp = added['pp']
    state = {'code': ctx.helper_source + FUNCTION_GRAPHS % TEST_GRAPH}
    try:
        await c('set_function', {'expression': 'v * 0.5', 'function': 'shade', 'inputs': {'v': 'float'}, **G})
        await c('set_function', {'expression': 'shade(v) + 0.25', 'function': 'wrap', 'inputs': {'v': 'float'}, **G})
        await c('set_function', {'expression': 'wrap($pos.x)', 'node_id': pp, **G})
        before = text(await c('execute_designer_code', state))
        # a read that failed would give one error each time, equal to itself (REVIEW.md TST-736)
        read = all('FUNCTION_GRAPH %s ' % name in before for name in ('shade', 'wrap')) and 'RESOURCES' in before
        check(S, "the package's function graphs read, before the refusals", read, before[-200:])
        computed = await pixels(ctx, pp)
        want = {(x, y): [at(x, y)[0] * 0.5 + 0.25] * 3 + [1.0] for x, y in POINTS}
        check(S, 'function graphs calling each other: the pixels are theirs', all_near(computed, want), str(computed))
        refusals: list[tuple[str, ToolArgs, str]] = [
            ("a function graph named like the grammar's function", {'function': 'clamp'}, '`clamp` is a function of'),
            ("a function graph named like the grammar's cast", {'function': 'float2'}, '`float2` is a cast of'),
            (
                'a function graph calling itself',
                {'function': 'shade', 'expression': 'shade(v)'},
                'calls shade itself',
            ),
            (
                'a function graph calling itself through another',
                {'function': 'shade', 'expression': 'wrap(v)'},
                'calls wrap, which calls shade',
            ),
            (
                "an identifier the package's compositing graph has",
                {'function': TEST_GRAPH},
                'the package holds a graph named %r already' % TEST_GRAPH,
            ),
            (
                'an input of a type no input takes',
                {'function': 'shade', 'inputs': {'v': 'string'}},
                "input `v`: string is no type a function graph's input takes",
            ),
            (
                'a call with too few arguments',
                {'node_id': pp, 'expression': 'wrap()'},
                'wrap takes 1 argument (v float)',
            ),
            (
                'a call of another type',
                {'node_id': pp, 'expression': 'wrap($pos)'},
                '`$pos` is a float2, where `wrap($pos)` takes a float',
            ),
        ]
        for what, args, says in refusals:
            r = await c('set_function', {'expression': '0.5', **args, **G})
            same = read and text(await c('execute_designer_code', state)) == before
            # a call refused could only have built the processor's function, which its pixels show
            kept = 'node_id' not in args or all_near(await pixels(ctx, pp), computed)
            refused = r.is_error and says in text(r)
            check(
                S,
                'refuses %s, the package unchanged' % what,
                refused and same and kept,
                '%s | %s %s' % (text(r)[-160:], same, kept),
            )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in added.values()], **G})


R0, R1, R2, R3 = (b / 255 for b in RAMP)  # ramp.png's columns' R, as Designer reads its bytes
# in a 4 px Pixel Processor, x -0.1, 0.3, 0.7 and 1.1 at its four columns, and y the top row's centre
SPREAD = 'float2($pos.x * 1.6 - 0.3, 0.125)'
ROW = [[k, 0] for k in range(4)]
# ramp's R where SPREAD samples it, by the arguments filter and wrap: one column, or two weighed; beyond an edge, the
# column the wrap gives
MODES: list[tuple[str, list[float]]] = [
    ('', [R3, R1, R2, R0]),  # nearest and repeat, as a new Sample node starts
    (", filter='nearest', wrap='repeat'", [R3, R1, R2, R0]),
    (", filter='bilinear'", [R3 + (R0 - R3) * 0.1, R0 + (R1 - R0) * 0.7, R2 + (R3 - R2) * 0.3, R3 + (R0 - R3) * 0.9]),
    (", wrap='clamp'", [R0, R1, R2, R3]),
    (", filter='bilinear', wrap='clamp'", [R0, R0 + (R1 - R0) * 0.7, R2 + (R3 - R2) * 0.3, R3]),
]
LUM = MODES[-1][0]
GREYS = [(r + R0 + 128 / 255) / 3 for r in MODES[-1][1]]  # the mean of R, G (the top row's) and B (128)


def _red(keywords: str) -> tuple[str, str, list[float]]:
    """A channel sampling ramp's R with the arguments `keywords`: what its check says, its expression, and its values."""
    want = dict(MODES)[keywords]
    return ('sample%s: R' % (keywords or ', by default'), 'sample(0, %s%s).x' % (SPREAD, keywords), want)


# each set_function's four channels, R, G, B and A, one sample each: one compute reads four (padding has no label)
PACKS: list[list[tuple[str, str, list[float]]]] = [
    [_red(keywords) for keywords, _ in (MODES[0], *MODES[2:])],
    [
        _red(MODES[1][0]),
        ('sample_lum%s: the mean of R, G and B' % LUM, 'sample_lum(0, %s%s)' % (SPREAD, LUM), GREYS),
        ('', '0', [0.0] * 4),
        ('', '1', [1.0] * 4),
    ],
]


async def check_set_function_samples_with_each_filter_and_wrap(ctx: Ctx) -> None:
    """A 4 px Pixel Processor samples ramp.png (preparations.py) at x -0.1, 0.3, 0.7 and 1.1 of its top row, one at each
    of its columns (SPREAD), four samples at a time, one in each channel (PACKS). With each filter and wrap, and with
    neither, R is the ramp's column the filter picks, or two columns weighed; beyond an edge, the one the wrap gives
    (MODES). sample_lum's grey, bilinear and clamped, is the mean of R, G and B there. Each set_function's result says
    it built them (REVIEW.md TST-744). The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    added = await sampler(ctx, [ctx.img], size_log2=2)
    try:
        before = ''
        for pack in PACKS:
            expression = 'float4(%s)' % ', '.join(sampled for _, sampled, _ in pack)
            t = text(await c('set_function', {'expression': expression, 'node_id': added['pp'], **G}))
            replaced = built(added['pp'], expression, before=before, images=True)
            expected = replaced + '\ncolorswitch is on: the float4 is the colour.'
            labels = ', '.join(label for label, _, _ in pack if label)
            check(S, 'set_function builds the samples %s' % labels, t == expected, t)
            before = expression
            got = await pixels(ctx, added['pp'], ROW)
            for channel, (label, _, want) in enumerate(pack):
                read = {p: v[channel : channel + 1] for p, v in got.items()}
                wanted = {(k, 0): [w] for k, w in enumerate(want)}
                if label:
                    check(S, '%s, at x -0.1, 0.3, 0.7 and 1.1' % label, all_near(read, wanted), str(read))
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in added.values()], **G})


# ROADMAP item 31: a normal map's Z rebuilt from its R and G, as Designer's normal node encodes it: z * 0.5 + 0.5
REBUILT = 'n = sample(0, $pos); xy = n.xy * 2 - 1; float4(n.xy, sqrt(max(0, 1 - dot(xy, xy))) * 0.5 + 0.5, 1)'
SLOPES = [[0, 0], [2, 2], [8, 8], [6, 10], [12, 4]]  # pixels of the 16 px normal map


async def check_set_function_rebuilds_a_normal_maps_z_from_its_r_and_g(ctx: Ctx) -> None:
    """ROADMAP item 31's case: a Pixel Processor samples the normal map (Designer's normal node on bump.png,
    preparations.py) and rebuilds its Z from its R and G. At five pixels, node_stats reads the rebuilt map's R and G as
    the normal map's, and its B within two 8-bit steps of the normal map's, which slopes there: a B below 0.9 at one of
    them at least. The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    added = await sampler(ctx, [ctx.nm])
    try:
        t = text(await c('set_function', {'expression': REBUILT, 'node_id': added['pp'], **G}))
        expected = built(added['pp'], REBUILT, images=True) + '\ncolorswitch is on: the float4 is the colour.'
        check(S, 'a normal map sampled: the result says what was built', t == expected, t)
        normal_map, rebuilt = await pixels(ctx, ctx.nm, SLOPES), await pixels(ctx, added['pp'], SLOPES)
        slopes = any(v[2] < 0.9 for v in normal_map.values())
        same = all_near(rebuilt, {p: [*v[:2], rebuilt.get(p, v)[2], 1.0] for p, v in normal_map.items()})
        close = all(abs(rebuilt[p][2] - v[2]) <= 2 / 255 + 1e-3 for p, v in normal_map.items() if p in rebuilt)
        check(
            S,
            "a normal map's Z rebuilt from its R and G, sampled: the normal map's own",
            slopes and same and close and len(normal_map) == len(SLOPES),
            '%s | %s' % (normal_map, rebuilt),
        )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in added.values()], **G})


TWO = 'a = sample(0, float2(0.875, 0.125)); b = sample(1, $pos); float4(a.x, b.y, b.z, sample_lum(1, $pos))'


async def check_set_function_samples_two_inputs(ctx: Ctx) -> None:
    """A Pixel Processor's second input image, input:1, connected through apply_edits' connect once input is: ramp.png
    in input, the normal map in input:1. Its pixel (0, 0) is ramp's R at pixel (3, 0), then the normal map's G and B and
    their mean with R there, read with node_stats (TWO). describe_graph shows input:1's connection. A connect into
    input:3, which the node lists only once input:2 is connected, is refused naming input:2, the graph unchanged. A
    sample of input:2, with nothing connected, is built, and the result says so. A function graph sampling its caller's
    input:1, called from it, reads the normal map too; called from a Pixel Processor without inputs, it is built, the
    result saying what to connect. Made to sample input:2, its result names both callers, and the input each lacks
    (REVIEW.md SRV-199). The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    added = await sampler(ctx, [ctx.img])
    bare: dict[str, str] = {}
    try:  # the second sampler made in it, so that a refusal of the first deletes it (REVIEW.md TST-746)
        bare = await sampler(ctx, [])
        two = added['pp']
        into: Ops = [{'op': 'connect', 'from': ctx.nm, 'to': two, 'input': 'input:1'}]
        t = text(await c('apply_edits', {'ops': into, **G}))
        check(S, 'a connect into input:1 once input is connected', '-> %s.input:1' % two in t, t)
        t = text(await c('set_function', {'expression': TWO, 'node_id': two, **G}))
        check(S, 'two inputs sampled: the result says what was built', t.startswith(built(two, TWO, images=True)), t)
        n = (await pixels(ctx, ctx.nm)).get((0, 0))
        got = await pixel_at(ctx, two)
        want = [R3, n[1], n[2], sum(n[:3]) / 3] if n else []
        check(S, 'two inputs sampled: index 0 reads input, index 1 input:1', near(got, want), '%s | %s' % (got, n))
        graph = await described(ctx, [two])
        check(
            S, "describe_graph shows input:1's connection", 'input:1<-%s.unique_filter_output' % ctx.nm in graph, graph
        )
        before = await described(ctx)
        r = await c('apply_edits', {'ops': [{'op': 'connect', 'from': ctx.img, 'to': two, 'input': 'input:3'}], **G})
        says = 'connect an image into input:2 first'
        same = await described(ctx) == before
        check(
            S,
            'a connect into input:3 is refused, naming input:2, the graph unchanged',
            r.is_error and says in text(r) and same,
            '%s | %s' % (text(r)[-200:], same),
        )
        t = text(await c('set_function', {'expression': 'sample(2, $pos)', 'node_id': two, **G}))
        says = '\n' + nothing(two, 'input:2')
        check(
            S,
            'a sample of the next input, input:2, is built, and the result says it has nothing',
            t.endswith(says),
            t.splitlines()[-1],  # the note compared, after the build line (REVIEW.md TST-747)
        )
        inputs = {'uv': 'float2'}
        await c('set_function', {'expression': 'sample(1, uv)', 'function': 'second', 'inputs': inputs, **G})
        await c('set_function', {'expression': 'second($pos)', 'node_id': two, **G})
        got = await pixel_at(ctx, two)
        check(S, "a function graph samples its caller's input:1", near(got, n or []), '%s | %s' % (got, n))
        t = text(await c('set_function', {'expression': 'second($pos)', 'node_id': bare['pp'], **G}))
        says = '\n' + nothing(bare['pp'], 'input:1', 'input')
        check(
            S,
            'a call sampling an input the caller lacks is built, and the result says so',
            t.endswith(says),
            t.splitlines()[-1],
        )
        t = text(await c('set_function', {'expression': 'sample(2, uv)', 'function': 'second', **G}))
        for caller, before in ((two, ''), (bare['pp'], 'input to input:1')):
            where = '%s/%s' % (TEST_GRAPH, caller)
            says = 'second is called from %s.perpixel, and %s' % (where, nothing(where, 'input:2', before))
            check(
                S,
                'a function graph made to sample input:2 names its caller %s, which lacks it' % caller,
                says in t,
                next((line for line in t.splitlines() if 'from %s.' % where in line), t[-150:]),  # its caller's line
            )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in [*added.values(), *bare.values()]], **G})


async def check_set_function_samples_in_a_value_processor(ctx: Ctx) -> None:
    """A Value Processor's function samples its own input images, ramp.png in input and the normal map in input:1,
    both connected in one apply_edits call (REVIEW.md TST-743). sample(0, float2(0.875, 0.125)).x gives the ramp's R at
    pixel (3, 0), and sample(1, ...) at pixel (0, 0)'s centre the normal map's R there, which a Pixel Processor reads
    through #s, connected by apply_edits' connect. The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    ops: Ops = [
        {'op': 'add', 'definition': 'valueprocessor', 'ref': 'vs'},
        {'op': 'connect', 'from': ctx.img, 'to': 'vs', 'input': 'input'},
        {'op': 'connect', 'from': ctx.nm, 'to': 'vs', 'input': 'input:1'},
        {'op': 'add', 'definition': 'pixelprocessor', 'ref': 'reads'},
        {'op': 'add', 'definition': 'output', 'ref': 'out'},
        {'op': 'connect', 'from': 'reads', 'to': 'out', 'input': 'inputNodeOutput'},
        {'op': 'connect', 'from': 'vs', 'to': 'reads', 'input': '#s'},
    ]
    added = refs(text(await c('apply_edits', {'ops': ops, **G})))
    try:
        expression = 'sample(0, float2(0.875, 0.125)).x'
        t = text(await c('set_function', {'expression': expression, 'node_id': added['vs'], **G}))
        expected = (
            built(added['vs'], expression, 'function', images=True) + "\nThe Value Processor's output is a float now."
        )
        check(S, 'a Value Processor sampling its input: the result says what was built', t == expected, t)
        await c('set_function', {'expression': '#s', 'node_id': added['reads'], **G})
        got = await pixel_at(ctx, added['reads'])
        check(
            S,
            "a Value Processor sampling its input: the ramp's R at pixel (3, 0)",
            near(got, [R3] * 3 + [1.0]),
            str(got),
        )
        # pixel (0, 0)'s centre in the 16 px normal map
        expression = 'sample(1, float2(0.03125, 0.03125)).x'
        t = text(await c('set_function', {'expression': expression, 'node_id': added['vs'], **G}))
        check(
            S,
            'a Value Processor sampling its input:1: built',
            t.startswith(built(added['vs'], expression, 'function', images=True)),
            t,
        )
        n = (await pixels(ctx, ctx.nm)).get((0, 0))
        got = await pixel_at(ctx, added['reads'])
        check(
            S,
            "a Value Processor sampling its input:1: the normal map's R at pixel (0, 0)",
            near(got, [n[0]] * 3 + [1.0] if n else []),
            '%s | %s' % (got, n),
        )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in added.values()], **G})


UNCONNECTED = 'sample(0, $pos) + sample(2, $pos)'
GAP = 'sample(1, $pos) + sample(2, $pos) + sample(5, $pos)'
SHOWN = 'colorswitch is on: the float4 is the colour.'


async def check_set_function_samples_an_input_with_nothing_connected(ctx: Ctx) -> None:
    """A sample of an input image with nothing connected is built, and the result says it reads (0, 0, 0, 0) until an
    image is connected (GUIDE.md, Sampling an image; REVIEW.md TST-743). A Pixel Processor without inputs samples
    input and input:2: the result names what to connect, in order. A Pixel Processor with ramp.png in input and
    input:2 and the normal map in input:1, connected in one apply_edits call, input:1 then disconnected, samples
    input:1, input:2 and input:5: the result names input:1 and input:5, and its pixel is ramp's (0, 0) alone. The nodes
    are deleted after it."""
    c, G = ctx.c, ctx.G
    added = await sampler(ctx, [ctx.img, ctx.nm, ctx.img])
    bare: dict[str, str] = {}
    try:  # the second sampler made in it (REVIEW.md TST-746)
        bare = await sampler(ctx, [])
        gap, lacks = added['pp'], bare['pp']
        t = text(await c('set_function', {'expression': UNCONNECTED, 'node_id': lacks, **G}))
        notes = [nothing(lacks, 'input'), nothing(lacks, 'input:2', 'input to input:1')]
        expected = '\n'.join([built(lacks, UNCONNECTED, images=True), SHOWN, *notes])
        check(
            S,
            'a sample of inputs a node lacks is built, and the result says what to connect',
            t == expected,
            differing(t, expected),  # a note, after the build line, most likely (REVIEW.md TST-747)
        )
        await c('apply_edits', {'ops': [{'op': 'disconnect', 'node': gap, 'input': 'input:1'}], **G})
        t = text(await c('set_function', {'expression': GAP, 'node_id': gap, **G}))
        notes = [nothing(gap, 'input:1'), nothing(gap, 'input:5', 'input:3 to input:4')]
        expected = '\n'.join([built(gap, GAP, images=True), SHOWN, *notes])
        check(
            S,
            'a sample of input:1, disconnected, and of input:5: built, and the result says so',
            t == expected,
            differing(t, expected),
        )
        got = await pixel_at(ctx, gap)
        check(
            S,
            'a sample of input:1, disconnected, and of input:5 reads (0, 0, 0, 0): input:2 alone shows',
            near(got, [R0, R0, 128 / 255, 1.0]),
            str(got),
        )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in [*added.values(), *bare.values()]], **G})


# each refusal: (what is wrong, the call's arguments but the graph and the expression, what its error says, whether it
# is the server's, after the read: then a wrong build could only show in the Pixel Processor's pixels)
REFUSALS: list[tuple[str, dict[str, str], str, bool]] = [
    ('an unknown name', {'expression': 'sqrt(nope)'}, 'column 6: unknown name `nope`', True),
    (
        'a float2 for a Pixel Processor',
        {'expression': '$pos'},
        'gives a float2, which a Pixel Processor computes as black',
        True,
    ),
    ('a float3 for a Pixel Processor', {'expression': 'float3($pos, 1)'}, 'write float4(c, 1) for a colour c', True),
    (
        'a sample at a float, not a float2',
        {'expression': 'sample(0, $pos.x)'},
        '`$pos.x` is a float, where `sample(0, $pos.x)` takes a float2',
        True,
    ),
    (
        'an index that is not a number',
        {'expression': 'sample(tint.x, $pos)'},
        "`tint.x` is a float, where `sample(tint.x, $pos)` takes an input image's index",
        True,
    ),
    (
        'a filter that is not one of its names',
        {'expression': 'sample(0, $pos, filter=tint)'},
        "filter is 'nearest' or 'bilinear'",
        True,
    ),
    ('a missing node', {'node_id': '999999'}, "node '999999' not found", False),
    ('a missing parameter', {'parameter': 'nope'}, "'nope' is not a parameter of node", False),
    ('a connector for a parameter', {'parameter': 'input'}, "'input' is an input connector of node", False),
]


async def check_set_function_refusals_leave_the_graph_unchanged(ctx: Ctx) -> None:
    """Each refusal says what is wrong, and leaves the graph as it was, read after each one. A refusal of the read, in
    Designer, is read with describe_graph: the nodes and parameters, and the Value Processor's function's nodes. One of
    the server's, after the read, could only have built a function, which only the pixels of the node it was asked of
    show. A wrong type for a parameter, `$pos` in a parameter's and in a Value Processor's function, where it isn't the
    pixel's (check_system_variables), a node without a function of its own and a parameter of a type no function gives
    (a curve's) are refused too. The curve node is deleted after it."""
    c, G = ctx.c, ctx.G
    curve = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'curve'}], **G})))
    await c('set_function', {'expression': 'float4($pos, 0, 1)', 'node_id': ctx.pp, **G})
    await c('set_function', {'expression': 'tint * 0.5', 'node_id': ctx.lv, 'parameter': 'leveloutlow', **G})

    async def state() -> str:
        """The graph as described, and the Value Processor's function, whose nodes describe_graph lists only for its
        node (REVIEW.md TST-760)."""
        return await described(ctx) + text(await c('describe_graph', {'node_id': ctx.vp, **G}))

    graph = await state()
    computed = {node: await pixels(ctx, node) for node in (ctx.pp, ctx.lv)}
    refusals: list[tuple[str, ToolArgs, str, str | None]] = [
        *(
            (what, {'expression': '0.5', 'node_id': ctx.pp, **args}, says, ctx.pp if after_read else None)
            for what, args, says, after_read in REFUSALS
        ),
        (
            'a float for a float4 parameter',
            {'expression': '0.5', 'node_id': ctx.lv, 'parameter': 'leveloutlow'},
            'takes a float4, and the expression gives a float',
            ctx.lv,
        ),
        (
            "a sample in a parameter's function",
            {'expression': 'sample(0, $pos)', 'node_id': ctx.lv, 'parameter': 'leveloutlow'},
            "only a Pixel or Value Processor's function has input images",
            ctx.lv,
        ),
        (
            "$pos in a parameter's function",
            {'expression': 'float4($pos, 0, 1)', 'node_id': ctx.lv, 'parameter': 'leveloutlow'},
            "`$pos` isn't the pixel's position in a parameter's function",
            ctx.lv,
        ),
        (
            "$pos in a Value Processor's function",
            {'expression': '$pos.x', 'node_id': ctx.vp},
            "`$pos` isn't the pixel's position in a Value Processor's function",
            None,
        ),
        ('a node with no function of its own', {'expression': '0.5', 'node_id': ctx.lv}, 'name the parameter', None),
        (
            'a parameter no function gives',
            {'expression': '0.5', 'node_id': curve, 'parameter': 'curveluminance'},
            'cannot take a function from this tool',
            None,
        ),
    ]
    try:
        for what, args, says, node in refusals:
            r = await c('set_function', {**args, **G})
            same = await state() == graph if node is None else all_near(await pixels(ctx, node), computed[node])
            refused = r.is_error and says in text(r)
            check(S, 'refuses %s, the graph unchanged' % what, refused and same, '%s | %s' % (text(r)[-150:], same))
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': curve}], **G})


# describe_node's helper on each of `definitions`, after a line naming it, in one code job (REVIEW.md TST-751)
DESCRIBED_EACH = dedent("""
    for definition in %r:
        print('=== ' + definition)
        describe_node(definition)""")


async def check_describe_node_and_search_nodes_know_the_function_nodes(ctx: Ctx) -> None:
    """search_nodes finds a function node by its description, Lower's, and by its label, Sample color's, naming the
    definition describe_node takes; a limit past what the library holds keeps it in reach (REVIEW.md TST-751).
    describe_node gives a function node's inputs and output, with their types, as the compiler's table has them
    (parsing.described_differs): add's, listing every number type, and lr's, named as a function's listing gives it
    (SRV-204). So do its helper's lines for every definition of the table, samplecol's int2 __constant__ among them, in
    one code job. It refuses an id the module lacks, naming search_nodes (TST-750). A function node's kind that names
    another node too, pow a library graph and passthrough an atomic one, gives that node, then names the function node
    (SRV-205). Both tools show lr's description with A<B, not the entity Designer's text holds, and no description
    describe_node gives holds an entity (HLP-246)."""
    c = ctx.c
    lower = ''
    for query, definition in (('lower than', 'sbs::function::lr'), ('sample color', 'sbs::function::samplecol')):
        t = text(await c('search_nodes', {'query': query, 'limit': 1000}))
        found = 'function %s' % definition.removeprefix('sbs::function::')
        line = next((line for line in t.splitlines() if line.startswith(found + ' ')), '')
        check(
            'search_nodes',
            'finds the function node %s by %r' % (definition, query),
            "definition='%s'" % definition in line,
            line or t.splitlines()[0],
        )
        lower = line if definition == 'sbs::function::lr' else lower
    check('search_nodes', "lr's description shows A<B, not its entity", lower.endswith(': A<B'), lower)
    table = compiler_table()
    for name, definition in (('add', 'sbs::function::add'), ('lr', 'lr')):
        t = text(await c('describe_node', {'definition': definition}))
        differs = described_differs(t, table[name])
        check(
            'describe_node',
            "a function node's inputs and output, with their types: %s" % definition,
            t.startswith('function node sbs::function::%s ' % name) and not differs,
            differs or t.splitlines()[0],
        )
    ids = ['sbs::function::' + name for name in sorted(table)]
    t = text(await c('execute_designer_code', {'code': ctx.helper_source + DESCRIBED_EACH % ids}))
    parts = re.split(r'^=== (\S+)$', t, flags=re.M)[1:]  # a definition, then what was said of it
    blocks = dict(zip(parts[::2], parts[1::2], strict=True))
    named = {definition: definition.removeprefix('sbs::function::') for definition in ids}
    differ = [
        '%s: %s' % (name, differs)
        for definition, name in named.items()
        if (differs := described_differs(blocks.get(definition, ''), table[name]))
    ]
    check(
        'describe_node',
        "every function node's inputs and output, with their types, as the compiler's table has them, all %d"
        % len(ids),
        not differ,
        '; '.join(differ) or '%d described' % len(blocks),
    )
    entities = sorted({e for block in blocks.values() for e in re.findall(r'&#?\w+;', block)})
    head = blocks.get('sbs::function::lr', '').strip().partition('\n')[0]
    check(
        'describe_node',
        "every function node's description shows the characters its entities stand for, lr's A<B",
        not entities and head.endswith(': A<B'),
        ', '.join(entities) or head,
    )
    # a name both a function node's kind and another node's: that node, then a line naming the function node (SRV-205)
    for name, kind in (('pow', 'library node pow'), ('passthrough', 'atomic node sbs::compositing::passthrough')):
        t = text(await c('describe_node', {'definition': name}))
        said = "%s is a function node's kind too: describe_node('sbs::function::%s') describes that one" % (name, name)
        check(
            'describe_node',
            "a function node's kind another node has: that node, and the function node named: %s" % name,
            t.startswith(kind) and t.rstrip().endswith(said),
            '%s ... %s' % (t.splitlines()[0], t.strip().splitlines()[-1]),
        )
    r = await c('describe_node', {'definition': 'sbs::function::no_such'})
    says = "'sbs::function::no_such' is no function node; search_nodes lists them"
    check(
        'describe_node',
        'refuses an id no function node has, naming search_nodes',
        r.is_error and says in text(r),
        text(r),
    )


# after TO_FLOAT4: a get node reading '#q', which the node lacks, added to a Pixel Processor's function outside the tools
A_LACKING_NAME = dedent("""
    from sd.api.sdvaluestring import SDValueString
    pp = _node(g, %r)
    perpixel = pp.getPropertyGraph(pp.getPropertyFromId('perpixel', SDPropertyCategory.Input))
    _new_node(perpixel, 'sbs::function::get_float1').setInputPropertyValueFromId('__constant__', SDValueString.sNew('#q'))""")
READ_W = 'float4(#w, #w * 0.5, 0, 1)'


async def check_describe_graph_shows_a_processors_function_and_what_feeds_its_input_values(ctx: Ctx) -> None:
    """describe_graph with node_id shows a Pixel Processor's own function, as set_function built READ_W: its nodes,
    each with its constant and its output's type, their connections and its output node (results.function_differs).
    It says what feeds #w, the input value it reads: a Value Processor's float. A stale drive shows: the Value
    Processor's output made a float4 outside the tools, #w is fed another type, which Designer reads wrongly; once
    disconnected, #w has nothing connected. A get node reading #q, which the node lacks, added outside the tools, is
    said to read no input value. The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    ops: Ops = [
        {'op': 'add', 'definition': 'valueprocessor', 'ref': 'feeder'},
        {'op': 'add', 'definition': 'pixelprocessor', 'ref': 'reader'},
    ]
    added = refs(text(await c('apply_edits', {'ops': ops, **G})))
    feeder, reader = added['feeder'], added['reader']
    shown: ToolArgs = {'node_id': reader, **G}
    try:
        await c('set_function', {'expression': '0.5', 'node_id': feeder, **G})
        await c('apply_edits', {'ops': [{'op': 'connect', 'from': feeder, 'to': reader, 'input': '#w'}], **G})
        await c('set_function', {'expression': READ_W, 'node_id': reader, **G})
        t = text(await c('describe_graph', shown))
        differs = function_differs(t, compile_expression(READ_W, {'#w': 'float'}, images=True))
        header = t.startswith("%s.perpixel, a Pixel Processor's function, in graph %s: " % (reader, TEST_GRAPH))
        check(
            'describe_graph',
            "a Pixel Processor's function: its nodes, constants, connections and output node",
            header and not differs,
            differs or t.splitlines()[0],
        )
        fed = 'reads #w: an input value of type float, fed by %s.unique_filter_output, of type float' % feeder
        check('describe_graph', 'an input value the function reads: what feeds it', fed + '\n' in t, t)
        changed = text(
            await c(
                'execute_designer_code',
                {'code': ctx.helper_source + TO_FLOAT4 % (TEST_GRAPH, feeder) + A_LACKING_NAME % reader},
            )
        )
        t = text(await c('describe_graph', shown))
        stale = fed + '4, which Designer reads wrongly'
        lacking = 'reads #q: the node has no input value of that name'
        check(
            'describe_graph',
            'an input value fed another type: says Designer reads it wrongly',
            'OUTPUT float4' in changed and stale + '\n' in t,
            '%s | %s' % (changed[-60:], t),
        )
        check('describe_graph', 'a #name the node lacks: says so', lacking in t, t)
        await c('apply_edits', {'ops': [{'op': 'disconnect', 'node': reader, 'input': '#w'}], **G})
        t = text(await c('describe_graph', shown))
        none = 'reads #w: an input value of type float, with nothing connected'
        check('describe_graph', 'an input value disconnected: says it has nothing connected', none in t, t)
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in added.values()], **G})


# a Pixel Processor's perpixel given an empty function graph outside the tools, as newPropertyGraph makes one
EMPTY_FUNCTION = dedent("""
    pp = _node(find_graph(%r), %r)
    pp.newPropertyGraph(pp.getPropertyFromId('perpixel', SDPropertyCategory.Input), 'SDSBSFunctionGraph')""")


async def check_describe_graph_shows_a_value_processors_function_and_says_when_there_is_none(ctx: Ctx) -> None:
    """describe_graph with node_id shows a Value Processor's own function, 0.5: its node and its output node (REVIEW.md
    TST-750). A new Pixel Processor has no function (GUIDE.md, A processor's function), which it says; given an empty
    one outside the tools, it says that. The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    ops: Ops = [
        {'op': 'add', 'definition': 'valueprocessor', 'ref': 'value'},
        {'op': 'add', 'definition': 'pixelprocessor', 'ref': 'fresh'},
    ]
    added = refs(text(await c('apply_edits', {'ops': ops, **G})))
    value, fresh = added['value'], added['fresh']
    try:
        await c('set_function', {'expression': '0.5', 'node_id': value, **G})
        t = text(await c('describe_graph', {'node_id': value, **G}))
        differs = function_differs(t, compile_expression('0.5', {}, images=True))
        header = t.startswith("%s.function, a Value Processor's function, in graph %s: " % (value, TEST_GRAPH))
        check(
            'describe_graph',
            "a Value Processor's function: its node and output node",
            header and not differs,
            differs or t,
        )
        t = text(await c('describe_graph', {'node_id': fresh, **G}))
        none = t.strip() == '%s.perpixel has no function' % fresh
        check('describe_graph', 'a new Pixel Processor: says it has no function', none, t)
        await c('execute_designer_code', {'code': ctx.helper_source + EMPTY_FUNCTION % (TEST_GRAPH, fresh)})
        t = text(await c('describe_graph', {'node_id': fresh, **G}))
        empty = t.strip() == '%s.perpixel has an empty function' % fresh
        check('describe_graph', 'an empty function: says so', empty, t)
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in added.values()], **G})


async def check_describe_graph_shows_a_parameters_function(ctx: Ctx) -> None:
    """describe_graph with node_id and parameter shows the levels node's leveloutlow function, tint * 0.5: its nodes,
    constants, connections and output node, and no input value read. Its levelinlow has no function, which it says."""
    c, G = ctx.c, ctx.G
    await c('set_function', {'expression': 'tint * 0.5', 'node_id': ctx.lv, 'parameter': 'leveloutlow', **G})
    t = text(await c('describe_graph', {'node_id': ctx.lv, 'parameter': 'leveloutlow', **G}))
    differs = function_differs(t, compile_expression('tint * 0.5', {'tint': 'float4'}))
    header = t.startswith("%s.leveloutlow, a parameter's function, in graph %s: " % (ctx.lv, TEST_GRAPH))
    check(
        'describe_graph',
        "a parameter's function: its nodes, constants, connections and output node",
        header and not differs and 'reads ' not in t,
        differs or t,
    )
    t = text(await c('describe_graph', {'node_id': ctx.lv, 'parameter': 'levelinlow', **G}))
    check(
        'describe_graph',
        'a parameter with no function: says so',
        t.strip() == '%s.levelinlow has no function' % ctx.lv,
        t,
    )


async def check_describe_graph_lists_a_parameter_set_function_refuses(ctx: Ctx) -> None:
    """describe_graph doesn't refuse a curve's curveluminance, a parameter no get_* node reads, as set_function does: it
    says the parameter has no function (REVIEW.md HLP-244). The curve node is deleted after it."""
    c, G = ctx.c, ctx.G
    curve = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'curve'}], **G})))
    try:
        t = text(await c('describe_graph', {'node_id': curve, 'parameter': 'curveluminance', **G}))
        check(
            'describe_graph',
            'a parameter set_function refuses, with no function: says it has none',
            t.strip() == '%s.curveluminance has no function' % curve,
            t,
        )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': curve}], **G})


DESCRIBED = 'float4(uv, k, 1)'
DESCRIBED_INPUTS = {'uv': 'float2', 'k': 'float'}


async def check_describe_graph_shows_a_function_graph_of_the_package(ctx: Ctx) -> None:
    """describe_graph with function shows the function graph shown(uv, k) = float4(uv, k, 1), as set_function made it:
    its inputs, its nodes, constants, connections and output node; node_ids picks some of its nodes, naming one it
    lacks. describe_graph of the graph names it among its package's function graphs, with its inputs and its output's
    type, but focused on node_ids (REVIEW.md HLP-242). An identifier the package lacks is refused, naming the ones it
    has."""
    c, G = ctx.c, ctx.G
    await c('set_function', {'expression': DESCRIBED, 'function': 'shown', 'inputs': DESCRIBED_INPUTS, **G})
    t = text(await c('describe_graph', {'function': 'shown', **G}))
    differs = function_differs(t, compile_expression(DESCRIBED, DESCRIBED_INPUTS, defining='shown', images=True))
    lines = t.splitlines()
    header = (
        len(lines) > 1 and lines[0].startswith('function graph shown of ') and lines[1] == 'inputs: uv float2, k float'
    )
    check(
        'describe_graph',
        'a function graph: its inputs, nodes, constants, connections and output node',
        header and not differs,
        differs or t,
    )
    first = next(iter(positions(t)), '')
    t = text(await c('describe_graph', {'function': 'shown', 'node_ids': [first, 'no_such_node'], **G}))
    picked = t.startswith('function graph shown of ') and list(positions(t)) == [first]
    check('describe_graph', "node_ids picks a function graph's nodes", picked and 'not found: no_such_node' in t, t)
    t = text(await c('describe_graph', G))
    check(
        'describe_graph',
        "the graph's description names its package's function graphs",
        'shown(uv float2, k float) -> float4' in t,
        t,
    )
    t = text(await c('describe_graph', {'node_ids': [ctx.pp], **G}))
    check(
        'describe_graph',
        'a description focused on node_ids leaves the function graphs out',
        'function graphs of the package' not in t and list(positions(t)) == [ctx.pp],  # its node, listed (TST-753)
        t,
    )
    r = await c('describe_graph', {'function': 'no_such_function', **G})
    check(
        'describe_graph',
        'an identifier the package lacks is refused, naming its function graphs',
        r.is_error and "no function graph 'no_such_function'" in text(r) and 'shown' in text(r),
        text(r),
    )


async def check_open_graph_opens_a_function_graph(ctx: Ctx) -> None:
    """open_graph with function opens the function graph opened(k) = k * 0.5 in the editor, fitted whole: the editor
    then has it current, and screenshot_designer('graph') shows another picture than the graph's (REVIEW.md TST-752).
    node_id centres one of its nodes. A node's function is refused, naming describe_graph: Designer's editor opens the
    node's graph instead (check_opening_a_function_in_the_editor). The graph is open in the editor after it."""
    c, G = ctx.c, ctx.G
    await c('set_function', {'expression': 'k * 0.5', 'function': 'opened', 'inputs': {'k': 'float'}, **G})
    try:
        await c('open_graph', {**G})
        graph_shot = await c('screenshot_designer', {'panel': 'graph', 'max_size': 400})
        t = text(await c('open_graph', {'function': 'opened', **G}))
        function_shot = await c('screenshot_designer', {'panel': 'graph', 'max_size': 400})
        check(
            'screenshot_designer',
            "graph, after open_graph's function: another picture than the graph's",
            is_image(graph_shot) and is_image(function_shot) and picture(graph_shot) != picture(function_shot),
            '%s | %s' % (text(graph_shot)[-80:], text(function_shot)[-80:]),
        )
        current = text(await c('execute_designer_code', {'code': GRAPH_IN_EDITOR}))
        check(
            'open_graph',
            'opens a function graph of the package, fitted whole',
            t.startswith('opened function graph opened')
            and 'fitted the whole graph (3 node(s)' in t
            and 'CURRENT=opened' in current,
            '%s | %s' % (t, current),
        )
        node = next(iter(positions(text(await c('describe_graph', {'function': 'opened', **G})))), '')
        t = text(await c('open_graph', {'function': 'opened', 'node_id': node, **G}))
        centred = t.startswith('opened function graph opened') and 'focused node %s ' % node in t
        check('open_graph', "node_id centres a function graph's node", centred, t)
        r = await c('open_graph', {'node_id': ctx.pp, 'parameter': 'perpixel', **G})
        says = "describe_graph(graph=%r, node_id=%r, parameter='perpixel')" % (TEST_GRAPH, ctx.pp)
        check(
            'open_graph',
            "refuses a node's function, naming describe_graph",
            r.is_error and says in text(r),
            text(r),
        )
    finally:
        await c('open_graph', {**G})
