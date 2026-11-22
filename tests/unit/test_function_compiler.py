"""function_compiler: an expression compiled into the function nodes Designer builds (ROADMAP item 9), the grammar's
constructs and its refusals. Designer connects a wrong type silently and computes a wrong value (GUIDE.md, Building a
function graph), so every compiled function is checked whole against the definitions' table (`compiled`). The
tests compiling calls of function graphs that call each other, in a loop and in a diamond, are the exception: they read
only the calls' tree (`tree`)."""

import pytest

from function_compiler import (
    DEFINITIONS,
    Constant,
    ExpressionError,
    Function,
    Kind,
    Resource,
    compile_expression,
    name_refusal,
)

# the graph inputs the expressions read, by id
INPUTS = {
    'f': 'float',
    'g': 'float',
    'v2': 'float2',
    'v3': 'float3',
    'c': 'float4',
    'i': 'int',
    'i2': 'int2',
    'i3': 'int3',
    'b': 'bool',
    's': 'string',
}
VECTORS = ('vector2', 'vector3', 'vector4', 'ivector2', 'ivector3', 'ivector4')  # components that add up


def tree(f: Function, index: int | None = None) -> str:
    """Node `index` (default: the output) and what feeds it: `definition[constant](its inputs, in the definition's
    order)`; an instance node of a function graph `instance[its identifier](its inputs, in the graph's order)`."""
    n = f['nodes'][f['output'] if index is None else index]
    constant = n['constant']
    shown = ', '.join(str(x) for x in constant) if isinstance(constant, tuple) else constant
    head = n['definition'] + ('' if constant is None else '[%s]' % shown)
    if n['definition'] == 'instance':
        return head + '(%s)' % ', '.join(tree(f, source) for source in n['inputs'].values())
    ids = [i for i in DEFINITIONS[n['definition']].inputs if i in n['inputs']]
    return head + ('(%s)' % ', '.join(tree(f, n['inputs'][i]) for i in ids) if ids else '')


def compiled(
    expression: str,
    inputs: dict[str, str] = INPUTS,
    functions: dict[str, Resource] | None = None,
    images: bool = False,
    defining: str | None = None,
    kind: Kind | None = None,
) -> Function:
    """compile_expression's result, checked whole: each node of a definition of the table, fed on each of its inputs
    but `__constant__` by an earlier node, of a type the input lists; a definition's inputs listing several types (a
    vector's components aside) of one type, which its output takes when it lists several; a vector's two components
    adding up to its size; a constant exactly where the definition has a `__constant__`, of its type; every node
    feeding the output. An instance node calls one of the function graphs `functions`: fed on each of its inputs, in
    their order, by an earlier node of that input's type, it gives its output's type. `images`, `defining` and `kind`
    are compile_expression's."""
    f = compile_expression(expression, inputs, functions, defining, images, kind)
    nodes = f['nodes']
    for k, n in enumerate(nodes):
        if n['definition'] == 'instance':
            resource = (functions or {})[str(n['constant'])]
            assert list(n['inputs']) == list(resource.inputs), n
            assert all(source < k and nodes[source]['type'] == resource.inputs[i] for i, source in n['inputs'].items())
            assert n['type'] == resource.output, n
            continue
        d = DEFINITIONS[n['definition']]
        assert set(n['inputs']) == set(d.inputs) - {'__constant__'}, n
        assert (n['constant'] is not None) == ('__constant__' in d.inputs), n
        if n['constant'] is not None:
            assert shape(n['constant']) == d.inputs['__constant__'][0], n
        assert all(source < k and nodes[source]['type'] in d.inputs[i] for i, source in n['inputs'].items()), n
        assert n['type'] in d.output, n
        shared = {nodes[n['inputs'][i]]['type'] for i in n['inputs'] if len(d.inputs[i]) > 1}
        if n['definition'] in VECTORS:
            assert sum(size(nodes[source]['type']) for source in n['inputs'].values()) == size(n['type']), n
        else:
            assert len(shared) <= 1, n
            assert len(d.output) == 1 or shared == {n['type']}, n
    fed = {f['output']}
    for k in reversed(range(len(nodes))):
        if k in fed:
            fed |= set(nodes[k]['inputs'].values())
    assert fed == set(range(len(nodes))), 'nodes feeding nothing: %s' % sorted(set(range(len(nodes))) - fed)
    assert f['type'] == nodes[f['output']]['type']
    return f


def shape(constant: Constant) -> str:
    """The type a constant holds: string, bool, int or float, or int2 to float4 for a tuple of them."""
    if isinstance(constant, tuple):
        kinds = {type(x) for x in constant}
        return '%s%d' % ('int' if kinds == {int} else 'float' if kinds == {float} else 'mixed', len(constant))
    return {str: 'string', bool: 'bool', int: 'int', float: 'float'}[type(constant)]


def size(type_: str) -> int:
    return int(type_[-1]) if type_[-1].isdigit() else 1


def refused(
    expression: str,
    inputs: dict[str, str] = INPUTS,
    functions: dict[str, Resource] | None = None,
    defining: str | None = None,
    images: bool = False,
    kind: Kind | None = None,
) -> str:
    with pytest.raises(ExpressionError) as e:
        compile_expression(expression, inputs, functions, defining, images, kind)
    return str(e.value)


XY = 'sub(mulscalar(get_float2[$pos], const_float1[2.0]), const_float2[1.0, 1.0])'


def test_a_name_bound_once_is_one_node_shared_by_every_use() -> None:
    f = compiled('xy = $pos * 2 - 1; sqrt(max(0, 1 - dot(xy, xy)))')
    assert tree(f) == 'sqrt(max(const_float1[0.0], sub(const_float1[1.0], dot(%s, %s))))' % (XY, XY)
    assert f['type'] == 'float'
    assert len(f['nodes']) == 11
    dot = next(n for n in f['nodes'] if n['definition'] == 'dot')
    assert dot['inputs']['a'] == dot['inputs']['b']


def test_statements_on_lines_or_after_semicolons_compile_alike() -> None:
    one_line = compiled('xy = $pos * 2 - 1; sqrt(max(0, 1 - dot(xy, xy)))')
    assert compiled('xy = $pos * 2 - 1  # centred\nsqrt(max(0, 1 - dot(xy, xy)))\n') == one_line


def test_a_graph_input_or_a_variable_read_twice_is_one_get_node() -> None:
    f = compiled('f + f')
    assert tree(f) == 'add(get_float1[f], get_float1[f])'
    assert len(f['nodes']) == 2
    assert len(compiled('$pos.x + $pos.y')['nodes']) == 4


@pytest.mark.parametrize(
    ('expression', 'built', 'type_'),
    [
        # literals: alone a float; true and false
        ('0.5', 'const_float1[0.5]', 'float'),
        ('1', 'const_float1[1.0]', 'float'),
        ('-2', 'const_float1[-2.0]', 'float'),
        ('true', 'const_bool[True]', 'bool'),
        ('false', 'const_bool[False]', 'bool'),
        ('True', 'const_bool[True]', 'bool'),
        # a literal takes the type its context needs
        ('$pos + 2', 'add(get_float2[$pos], const_float2[2.0, 2.0])', 'float2'),
        ('v2 / 2', 'div(get_float2[v2], const_float2[2.0, 2.0])', 'float2'),
        ('i + 1', 'add(get_integer1[i], const_int1[1])', 'int'),
        ('2 - i2', 'sub(const_int2[2, 2], get_integer2[i2])', 'int2'),
        ('k = 2; $pos + k', 'add(get_float2[$pos], const_float2[2.0, 2.0])', 'float2'),
        ('k = 2; $tiling * k', 'mul(get_integer1[$tiling], const_int1[2])', 'int'),
        ('k = 2; float(i + k) * k', 'mul(tofloat(add(get_integer1[i], const_int1[2])), const_float1[2.0])', 'float'),
        # vectors, from components that add up
        ('float2(f, g)', 'vector2(get_float1[f], get_float1[g])', 'float2'),
        ('float2(0.2, 1)', 'const_float2[0.2, 1.0]', 'float2'),
        ('float4(v3, 1)', 'vector4(get_float3[v3], const_float1[1.0])', 'float4'),
        ('float3(1, v2)', 'vector3(const_float1[1.0], get_float2[v2])', 'float3'),
        ('float4(v2, v2)', 'vector4(get_float2[v2], get_float2[v2])', 'float4'),
        (
            'float4(f, g, f, g)',
            'vector4(vector3(vector2(get_float1[f], get_float1[g]), get_float1[f]), get_float1[g])',
            'float4',
        ),
        ('int2(i, 3)', 'ivector2(get_integer1[i], const_int1[3])', 'int2'),
        ('int3(1, 2, 3)', 'const_int3[1, 2, 3]', 'int3'),
        ('int4(i3, i)', 'ivector4(get_integer3[i3], get_integer1[i])', 'int4'),
        # casts, and a value already of the type
        ('float(i)', 'tofloat(get_integer1[i])', 'float'),
        ('int(f)', 'toint1(get_float1[f])', 'int'),
        ('float2(i2)', 'tofloat2(get_integer2[i2])', 'float2'),
        ('int3(v3)', 'toint3(get_float3[v3])', 'int3'),
        ('float(f)', 'get_float1[f]', 'float'),
        ('float2(v2)', 'get_float2[v2]', 'float2'),
        ('int2(i2)', 'get_integer2[i2]', 'int2'),
        ('float(3)', 'const_float1[3.0]', 'float'),
        ('int(3)', 'const_int1[3]', 'int'),
        # swizzles
        ('$pos.x', 'swizzle1[0](get_float2[$pos])', 'float'),
        ('$pos.yx', 'swizzle2[1, 0](get_float2[$pos])', 'float2'),
        ('c.rgb', 'swizzle3[0, 1, 2](get_float4[c])', 'float3'),
        ('c.wzyx', 'swizzle4[3, 2, 1, 0](get_float4[c])', 'float4'),
        ('v3.zz', 'swizzle2[2, 2](get_float3[v3])', 'float2'),
        ('i2.y', 'iswizzle1[1](get_integer2[i2])', 'int'),
        ('i3.yx', 'iswizzle2[1, 0](get_integer3[i3])', 'int2'),
        ('i3.zxy', 'iswizzle3[2, 0, 1](get_integer3[i3])', 'int3'),
        ('i3.zyxx', 'iswizzle4[2, 1, 0, 0](get_integer3[i3])', 'int4'),
        # operators
        ('f + g', 'add(get_float1[f], get_float1[g])', 'float'),
        ('f - g', 'sub(get_float1[f], get_float1[g])', 'float'),
        ('f * g', 'mul(get_float1[f], get_float1[g])', 'float'),
        ('f / g', 'div(get_float1[f], get_float1[g])', 'float'),
        ('f % g', 'mod(get_float1[f], get_float1[g])', 'float'),
        ('v2 * v2', 'mul(get_float2[v2], get_float2[v2])', 'float2'),
        ('v2 % v2', 'mod(get_float2[v2], get_float2[v2])', 'float2'),
        ('-f', 'neg(get_float1[f])', 'float'),
        ('-v2', 'neg(get_float2[v2])', 'float2'),
        ('i - 1', 'sub(get_integer1[i], const_int1[1])', 'int'),
        # a float with a float vector: broadcast in + - /, mulscalar in *
        ('v2 + f', 'add(get_float2[v2], vector2(get_float1[f], get_float1[f]))', 'float2'),
        ('f - v3', 'sub(vector3(vector2(get_float1[f], get_float1[f]), get_float1[f]), get_float3[v3])', 'float3'),
        (
            'c / f',
            'div(get_float4[c], vector4(vector2(get_float1[f], get_float1[f]), vector2(get_float1[f], get_float1[f])))',
            'float4',
        ),
        ('v2 * f', 'mulscalar(get_float2[v2], get_float1[f])', 'float2'),
        ('f * c', 'mulscalar(get_float4[c], get_float1[f])', 'float4'),
        ('$pos * 2', 'mulscalar(get_float2[$pos], const_float1[2.0])', 'float2'),
        ('2 * v3', 'mulscalar(get_float3[v3], const_float1[2.0])', 'float3'),
        ('k = 2; $pos * k', 'mulscalar(get_float2[$pos], const_float1[2.0])', 'float2'),
        ('2 * i2', 'mul(const_int2[2, 2], get_integer2[i2])', 'int2'),
        # comparisons
        ('f == g', 'eq(get_float1[f], get_float1[g])', 'bool'),
        ('f != g', 'noteq(get_float1[f], get_float1[g])', 'bool'),
        ('f < g', 'lr(get_float1[f], get_float1[g])', 'bool'),
        ('f <= g', 'lreq(get_float1[f], get_float1[g])', 'bool'),
        ('f > g', 'gt(get_float1[f], get_float1[g])', 'bool'),
        ('f >= g', 'gteq(get_float1[f], get_float1[g])', 'bool'),
        ('i > 2', 'gt(get_integer1[i], const_int1[2])', 'bool'),
        ('$pos.x < 0.5', 'lr(swizzle1[0](get_float2[$pos]), const_float1[0.5])', 'bool'),
        # and, or, not
        ('b and f > 0', 'and(get_bool[b], gt(get_float1[f], const_float1[0.0]))', 'bool'),
        ('b or b', 'or(get_bool[b], get_bool[b])', 'bool'),
        ('b and b and b', 'and(and(get_bool[b], get_bool[b]), get_bool[b])', 'bool'),
        ('not b', 'not(get_bool[b])', 'bool'),
        # a if condition else b
        ('f if b else 0', 'ifelse(get_bool[b], get_float1[f], const_float1[0.0])', 'float'),
        (
            'v2 if f > 0 else 1',
            'ifelse(gt(get_float1[f], const_float1[0.0]), get_float2[v2], const_float2[1.0, 1.0])',
            'float2',
        ),
        ('1 if b else 0', 'ifelse(get_bool[b], const_float1[1.0], const_float1[0.0])', 'float'),
        ('s if b else s', 'ifelse(get_bool[b], get_string[s], get_string[s])', 'string'),
        # the atomic functions
        ('sqrt(f)', 'sqrt(get_float1[f])', 'float'),
        ('sqrt(v2)', 'sqrt(get_float2[v2])', 'float2'),
        ('pow(v2, 2)', 'pow(get_float2[v2], const_float2[2.0, 2.0])', 'float2'),
        ('abs(i)', 'abs(get_integer1[i])', 'int'),
        # a negative number where a float is needed
        ('$pos * -1', 'mulscalar(get_float2[$pos], const_float1[-1.0])', 'float2'),
        ('float2(-1, 2)', 'const_float2[-1.0, 2.0]', 'float2'),
        ('1 if b else -1', 'ifelse(get_bool[b], const_float1[1.0], const_float1[-1.0])', 'float'),
        ('abs(-3)', 'abs(const_float1[-3.0])', 'float'),
        ('floor(f)', 'floor(get_float1[f])', 'float'),
        ('ceil(f)', 'ceil(get_float1[f])', 'float'),
        ('sin(f)', 'sin(get_float1[f])', 'float'),
        ('cos(f)', 'cos(get_float1[f])', 'float'),
        ('tan(f)', 'tan(get_float1[f])', 'float'),
        ('exp(f)', 'exp(get_float1[f])', 'float'),
        ('log(f)', 'log(get_float1[f])', 'float'),
        ('log2(f)', 'log2(get_float1[f])', 'float'),
        ('min(f, 1)', 'min(get_float1[f], const_float1[1.0])', 'float'),
        ('max(i2, i2)', 'max(get_integer2[i2], get_integer2[i2])', 'int2'),
        ('lerp(v2, v2, 0.5)', 'lerp(get_float2[v2], get_float2[v2], const_float1[0.5])', 'float2'),
        ('dot(v3, v3)', 'dot(get_float3[v3], get_float3[v3])', 'float'),
        ('rand(f)', 'rand(get_float1[f])', 'float'),
        ('cartesian(f, g)', 'cartesian(get_float1[f], get_float1[g])', 'float2'),
        # atan2(y, x): Designer's atan2 reads y from its float2's second component (the functions category)
        ('atan2(f, g)', 'atan2(vector2(get_float1[g], get_float1[f]))', 'float'),
        ('atan2(1, 0)', 'atan2(const_float2[0.0, 1.0])', 'float'),
        # built from atomic nodes
        ('clamp(f, 0, 1)', 'min(max(get_float1[f], const_float1[0.0]), const_float1[1.0])', 'float'),
        ('clamp(v2, 0, 1)', 'min(max(get_float2[v2], const_float2[0.0, 0.0]), const_float2[1.0, 1.0])', 'float2'),
        ('length(v2)', 'sqrt(dot(get_float2[v2], get_float2[v2]))', 'float'),
    ],
)
def test_each_construct_compiles_to_its_nodes(expression: str, built: str, type_: str) -> None:
    f = compiled(expression)
    assert (tree(f), f['type']) == (built, type_)


def test_a_float_made_a_vector4_shares_one_vector2() -> None:
    f = compiled('c / f')
    assert len(f['nodes']) == 5
    vector4 = next(n for n in f['nodes'] if n['definition'] == 'vector4')
    assert vector4['inputs']['componentsin'] == vector4['inputs']['componentslast']


@pytest.mark.parametrize('expression', ['  f + g', '\n    x = f\n    x + g\n', '\tf + g  '])
def test_text_indented_whole_compiles_as_if_it_were_not(expression: str) -> None:
    assert tree(compiled(expression)) == 'add(get_float1[f], get_float1[g])'


def test_length_and_normalize_read_their_vector_once() -> None:
    length = compiled('length(v2)')
    assert len(length['nodes']) == 3
    norm = compiled('normalize(v3)')
    size = 'sqrt(dot(get_float3[v3], get_float3[v3]))'
    assert tree(norm) == 'div(get_float3[v3], vector3(vector2(%s, %s), %s))' % (size, size, size)
    assert (norm['type'], len(norm['nodes'])) == ('float3', 6)


@pytest.mark.parametrize(
    ('variable', 'getter', 'type_'),
    [
        # Adobe's system-variables page; all but $time measured too (the functions category, check_system_variables)
        ('$pos', 'get_float2', 'float2'),
        ('$size', 'get_float2', 'float2'),
        ('$sizelog2', 'get_float2', 'float2'),
        ('$tiling', 'get_integer1', 'int'),
        ('$time', 'get_float1', 'float'),
    ],
)
def test_a_variable_is_read_with_the_get_node_of_its_type(variable: str, getter: str, type_: str) -> None:
    f = compiled(variable)
    assert (tree(f), f['type']) == ('%s[%s]' % (getter, variable), type_)


@pytest.mark.parametrize(
    ('kind', 'where'),
    [
        ('function', "a Value Processor's function, where it reads (0, 0)"),
        ('parameter', "a parameter's function, where it reads another value"),
    ],
)
def test_pos_is_refused_where_it_isnt_the_pixels(kind: Kind, where: str) -> None:
    # the functions category's facts: there it isn't the pixel's position (GUIDE.md, Variables)
    assert refused('float4($pos, 0, 1)', {}, kind=kind) == (
        "column 8: `$pos` isn't the pixel's position in %s: use it in a Pixel Processor's function" % where
    )
    assert tree(compiled('$size.x / $sizelog2.y', {}, kind=kind)) == (
        'div(swizzle1[0](get_float2[$size]), swizzle1[1](get_float2[$sizelog2]))'
    )


@pytest.mark.parametrize('kind', ['function', 'parameter'])
def test_a_call_to_a_function_graph_reading_pos_compiles_wherever_it_is(kind: Kind) -> None:
    # Resource carries no flag for `$pos`: a call from where it isn't the pixel's is taken, unchecked (REVIEW.md SRV-219)
    where = {'where': Resource({}, 'float2', ())}
    assert tree(compiled('where()', {}, where, kind=kind)) == 'instance[where]()'


# a Pixel Processor's, and a function graph's (no kind), which can't know its callers
@pytest.mark.parametrize('kind', ['perpixel', None])
def test_pos_is_read_in_a_pixel_processors_function_and_a_function_graphs(kind: Kind | None) -> None:
    assert tree(compiled('$pos.x', {}, kind=kind)) == 'swizzle1[0](get_float2[$pos])'


def test_a_variable_and_a_graph_input_named_like_it_are_told_apart() -> None:
    # each `$` is read as `_` before parsing
    assert tree(compiled('$pos + _pos', {'_pos': 'float2'})) == 'add(get_float2[$pos], get_float2[_pos])'


@pytest.mark.parametrize(
    ('type_', 'getter'),
    [
        ('float', 'get_float1'),
        ('float2', 'get_float2'),
        ('float3', 'get_float3'),
        ('float4', 'get_float4'),
        ('int', 'get_integer1'),
        ('int2', 'get_integer2'),
        ('int3', 'get_integer3'),
        ('int4', 'get_integer4'),
        ('bool', 'get_bool'),
        ('string', 'get_string'),
    ],
)
def test_a_graph_input_is_read_with_the_get_node_of_its_type(type_: str, getter: str) -> None:
    f = compiled('x', {'x': type_})
    assert (tree(f), f['type']) == ('%s[x]' % getter, type_)


@pytest.mark.parametrize(
    ('type_', 'getter'), [('float', 'get_float1'), ('float2', 'get_float2'), ('int', 'get_integer1')]
)
def test_an_input_value_is_read_by_its_name_with_the_get_node_of_its_type(type_: str, getter: str) -> None:
    # the node's input values come in `inputs` beside the graph's, under their `#name`
    f = compiled('#v', {'#v': type_, 'v': 'bool'})
    assert (tree(f), f['type']) == ('%s[#v]' % getter, type_)


def test_an_input_value_a_graph_input_and_a_variable_named_alike_are_told_apart() -> None:
    # each `#` and `$` of a name is read as `_` before parsing
    inputs = {'#pos': 'float2', 'pos': 'float2', '_pos': 'float2'}
    assert (
        tree(compiled('#pos + pos + $pos + _pos', inputs))
        == 'add(add(add(get_float2[#pos], get_float2[pos]), get_float2[$pos]), get_float2[_pos])'
    )


def test_an_input_value_read_twice_is_one_get_node_and_takes_swizzles() -> None:
    f = compiled('#v.x + #v.y', {'#v': 'float2'})
    assert tree(f) == 'add(swizzle1[0](get_float2[#v]), swizzle1[1](get_float2[#v]))'
    assert len(f['nodes']) == 4


@pytest.mark.parametrize(
    'expression',
    [
        '#v * 2  # twice the value',
        '#v * 2#',
        '# #w would be a value\n#v * 2',
        'x = #v  # costs $1\nx * 2',
    ],
    ids=['after the result', 'an empty one', 'on a line of its own', 'with a $ in it'],
)
def test_a_hash_not_followed_by_a_letter_starts_a_comment(expression: str) -> None:
    # a comment's own #name or $ is not read: #w is no input value here
    assert tree(compiled(expression, {'#v': 'float'})) == 'mul(get_float1[#v], const_float1[2.0])'


def test_an_input_of_a_type_no_function_reads_is_refused_only_when_read() -> None:
    assert tree(compiled('f', {'f': 'float', 'x': 'ColorRGBA'})) == 'get_float1[f]'
    assert (
        refused('x', {'x': 'ColorRGBA'}) == "column 1: graph input `x` has type ColorRGBA, which a function can't read"
    )


UNKNOWN = '; the graph inputs are b, c, f, g, i, i2, i3, s, v2, v3'
FUNCTIONS = (
    'abs, atan2, cartesian, ceil, clamp, cos, dot, exp, float, float2, float3, float4, floor, int, int2, int3, int4, '
    'length, lerp, log, log2, max, min, normalize, pow, rand, sample, sample_lum, sin, sqrt, tan'
)
GRAMMAR = ' is not part of the grammar'
STATEMENT = (
    ' is not part of the grammar: a statement binds one name (`name = value`), and the last one gives the result'
)
NUMBER_TYPES = 'an int, int2, int3, int4, float, float2, float3 or float4'


@pytest.mark.parametrize(
    ('expression', 'message'),
    [
        # statements
        ('f + )', "column 5: unmatched ')'"),
        ('', 'the expression is empty'),
        ('# a comment', 'the expression is empty'),
        ('x = f', 'column 1: `x = f` binds a name: the last statement gives the result'),
        ('x += 1; x', 'column 1: `x += 1`' + STATEMENT),
        ('a = b = f; a', 'column 1: `a = b = f`' + STATEMENT),
        ('f; g', 'column 1: `f` gives a value before the last statement: bind it to a name (`name = value`)'),
        ('x = f; x = g; x', 'column 8: `x` is bound already, at column 1: a name is bound once'),
        ('f = 1; f', 'column 1: `f` is a graph input: bind another name'),
        ('true = 1; true', 'column 1: `true` is a constant: bind another name'),
        ('x = f; g', 'column 1: `x` is bound but never used'),
        ('x = f\nfoo', 'line 2, column 1: unknown name `foo`' + UNKNOWN),
        # names, variables and functions
        ('foo', 'column 1: unknown name `foo`' + UNKNOWN),
        ('$pos + foo', 'column 8: unknown name `foo`' + UNKNOWN),
        ('\u00e9 = f; \u00e9 + foo', 'column 12: unknown name `foo`' + UNKNOWN),
        ('  f + foo', 'column 7: unknown name `foo`' + UNKNOWN),
        ('\n    x = f\n    x + foo\n', 'line 3, column 9: unknown name `foo`' + UNKNOWN),
        ('  f + )', "column 7: unmatched ')'"),
        ('  $ pos', "column 3: `$` starts a variable's name, such as $pos"),
        ('y = x + 1; x = f; y', 'column 5: unknown name `x`' + UNKNOWN),
        ('$foo', 'column 1: unknown variable `$foo`; the variables are $pos, $size, $sizelog2, $tiling, $time'),
        # an FX-Map's: Adobe's system-variables page, and every read of them in Designer's own packages
        ('$depth', "column 1: `$depth` is an FX-Map's variable, which no function this tool builds can read"),
        ('$number * 2', "column 1: `$number` is an FX-Map's variable, which no function this tool builds can read"),
        ('$ pos', "column 1: `$` starts a variable's name, such as $pos"),
        ('f$pos', "column 2: `$` starts a variable's name, such as $pos"),
        ('$pos = f; $pos', "column 1: `$pos` is Designer's variable: it can't be bound"),
        ('foo(f)', 'column 1: unknown function `foo`; the functions are ' + FUNCTIONS),
        ('f.sin()', 'column 1: `f.sin()`' + GRAMMAR),
        ('$pos(f)', 'column 1: `$pos(f)`' + GRAMMAR),
        ('sqrt(f, g)', 'column 1: sqrt takes 1 argument, and `sqrt(f, g)` gives 2'),
        ('min(f)', 'column 1: min takes 2 arguments, and `min(f)` gives 1'),
        ('float(f, g)', 'column 1: float takes 1 argument, and `float(f, g)` gives 2'),
        ('atan2(f)', 'column 1: atan2 takes 2 arguments, and `atan2(f)` gives 1'),
        ('sqrt(a=f)', 'column 1: `sqrt(a=f)` names an argument: arguments are given by position'),
        ('sqrt(*f)', 'column 6: `*f`' + GRAMMAR),
        # swizzles
        ('v2.q', 'column 1: `v2.q` is not a swizzle: write up to four of x, y, z, w, or of r, g, b, a'),
        ('c.xg', 'column 1: `c.xg` is not a swizzle: write up to four of x, y, z, w, or of r, g, b, a'),
        ('c.xyzwx', 'column 1: `c.xyzwx` is not a swizzle: write up to four of x, y, z, w, or of r, g, b, a'),
        ('$pos.z', 'column 1: `$pos.z`: `$pos` is a float2, which has no z'),
        ('f.x', "column 1: `f.x`: `f` is a float; a swizzle reads a vector's components"),
        ('b.x', "column 1: `b.x`: `b` is a bool; a swizzle reads a vector's components"),
        ('(1).x', "column 1: `(1).x`: `1` is a number; a swizzle reads a vector's components"),
        # types an input doesn't take
        ('sqrt(i)', 'column 6: `i` is an int, where `sqrt(i)` takes a float, float2, float3 or float4: write float(i)'),
        ('b + 1', 'column 1: `b` is a bool, where `b + 1` takes ' + NUMBER_TYPES),
        ('not f', 'column 5: `f` is a float, where `not f` takes a bool'),
        ('-b', 'column 2: `b` is a bool, where `-b` takes a float, float2, float3 or float4'),
        # Designer computes negative ints wrongly (measured on macOS arm64: the functions category,
        # check_what_nodes_compute)
        ('-i', 'column 1: `-i` makes negative ints, which Designer computes wrongly: write -float(i)'),
        ('-i2', 'column 1: `-i2` makes negative ints, which Designer computes wrongly: write -float2(i2)'),
        ('i + -1', 'column 5: `-1` is a negative int, which Designer computes wrongly: write float(i)'),
        ('int2(-1, 2)', 'column 6: `-1` is a negative int, which Designer computes wrongly: compute it in floats'),
        ('int(-3)', 'column 5: `-3` is a negative int, which Designer computes wrongly: compute it in floats'),
        (
            'k = -2; $tiling * k',
            'column 19: `k` is a negative int, which Designer computes wrongly: write float($tiling)',
        ),
        (
            'i2 % i2',
            'column 1: `i2` is an int2, where `i2 % i2` takes an int, float, float2, float3 or float4: write float2(i2)',
        ),
        ('f if f else 0', 'column 6: `f` is a float, where `f if f else 0` takes a bool'),
        ('v2 > f', 'column 1: `v2` is a float2, where `v2 > f` takes an int or float: write v2.x'),
        ('length(f)', 'column 8: `f` is a float, where `length(f)` takes a float2, float3 or float4'),
        ('normalize(f)', 'column 11: `f` is a float, where `normalize(f)` takes a float2, float3 or float4'),
        ('dot(f, g)', 'column 5: `f` is a float, where `dot(f, g)` takes a float2, float3 or float4'),
        ('lerp(v2, v2, v2)', 'column 14: `v2` is a float2, where `lerp(v2, v2, v2)` takes a float: write v2.x'),
        ('atan2(v2, f)', 'column 7: `v2` is a float2, where `atan2(v2, f)` takes a float: write v2.x'),
        ('dot(1, 2)', 'column 5: `1` is a number, where `dot(1, 2)` takes a float2, float3 or float4'),
        ('float(v2)', 'column 7: `v2` is a float2, where `float(v2)` takes an int or float: write v2.x'),
        ('int(b)', 'column 5: `b` is a bool, where `int(b)` takes an int or float'),
        # mixes: the cast or the swizzle to write
        ('f + i', 'column 1: `f + i` mixes a float (`f`) and an int (`i`): write float(i)'),
        ('i + f', 'column 1: `i + f` mixes an int (`i`) and a float (`f`): write float(i)'),
        ('v2 + v3', 'column 1: `v2 + v3` mixes a float2 (`v2`) and a float3 (`v3`): write v3.xy'),
        ('v2 % f', 'column 1: `v2 % f` mixes a float2 (`v2`) and a float (`f`): write float2(f, f)'),
        ('i2 + i', 'column 1: `i2 + i` mixes an int2 (`i2`) and an int (`i`): write int2(i, i)'),
        ('i2 * i', 'column 1: `i2 * i` mixes an int2 (`i2`) and an int (`i`): write int2(i, i)'),
        ('min(v2, f)', 'column 1: `min(v2, f)` mixes a float2 (`v2`) and a float (`f`): write float2(f, f)'),
        ('min(f, v2)', 'column 1: `min(f, v2)` mixes a float (`f`) and a float2 (`v2`): write float2(f, f)'),
        ('v3 + v2', 'column 1: `v3 + v2` mixes a float3 (`v3`) and a float2 (`v2`): write v3.xy'),
        ('i2 + v3', 'column 1: `i2 + v3` mixes an int2 (`i2`) and a float3 (`v3`): write float2(i2) and v3.xy'),
        ('v2 + (v3 * 2)', 'column 1: `v2 + (v3 * 2)` mixes a float2 (`v2`) and a float3 (`v3 * 2`): write (v3 * 2).xy'),
        ('s if b else f', 'column 1: `s if b else f` mixes a string (`s`) and a float (`f`)'),
        # literals that can't take the type their context needs
        ('$tiling * 0.5', 'column 11: `0.5` must be an int here, as `$tiling` is: write float($tiling)'),
        ('i + 1.0', 'column 5: `1.0` must be an int here, as `i` is: write float(i)'),
        ('k = 0.5; $tiling + k', 'column 20: `k` must be an int here, as `$tiling` is: write float($tiling)'),
        ('int2(1.5, 2)', 'column 6: `1.5` must be an int here: write it without a decimal point, such as `1`'),
        ('int(2.5)', 'column 5: `2.5` must be an int here: write it without a decimal point, such as `2`'),
        ('int(2.0)', 'column 5: `2.0` must be an int here: write it without a decimal point, such as `2`'),
        ('int2(1.0, 2.0)', 'column 6: `1.0` must be an int here: write it without a decimal point, such as `1`'),
        # no whole number to suggest: a negative one is refused in turn, and 1e999 is infinite
        ('int(-2.5)', 'column 5: `-2.5` must be an int here: compute it in floats'),
        ('int(1e999)', 'column 5: `1e999` must be an int here: compute it in floats'),
        ('b and 1', 'column 7: `1` must be a bool here: write true or false'),
        ('1 if 1 else 0', 'column 6: `1` must be a bool here: write true or false'),
        # vectors
        ('float3(v2)', 'column 1: float3 takes components that add up to 3, and `float3(v2)` gives 2'),
        ('float2(1)', 'column 1: float2 takes components that add up to 2, and `float2(1)` gives 1'),
        ('float4(c, f)', 'column 1: float4 takes components that add up to 4, and `float4(c, f)` gives 5'),
        ('float2()', 'column 1: float2 takes components that add up to 2, and `float2()` gives 0'),
        ('float2(i, f)', 'column 8: `i` is an int, where `float2(i, f)` takes float components: write float(i)'),
        ('int2(f, i)', 'column 6: `f` is a float, where `int2(f, i)` takes int components: write int(f)'),
        ('float2(b, f)', 'column 8: `b` is a bool, where `float2(b, f)` takes float components'),
        # comparisons and the rest of Python
        ('f < g < 1', 'column 1: `f < g < 1` chains comparisons: write (f < g) and (g < 1)'),
        ('f ** 2', 'column 1: `f ** 2`' + GRAMMAR + ': write pow(f, 2)'),
        ('f // 2', 'column 1: `f // 2`' + GRAMMAR + ': write floor(f / 2)'),
        ('[f]', 'column 1: `[f]`' + GRAMMAR),
        ('f[0]', 'column 1: `f[0]`' + GRAMMAR),
        ("'a'", "column 1: `'a'`" + GRAMMAR),
        ('None', 'column 1: `None`' + GRAMMAR),
        ('1j', 'column 1: `1j`' + GRAMMAR),
        ('lambda: 1', 'column 1: `lambda: 1`' + GRAMMAR),
        ('+f', 'column 1: `+f`' + GRAMMAR),
        ('f & g', 'column 1: `f & g`' + GRAMMAR),
        ('f is g', 'column 1: `f is g`' + GRAMMAR),
        ('if b: f', 'column 1: `if b: f`' + STATEMENT),
    ],
)
def test_each_mistake_is_refused_naming_its_place_and_what_was_expected(expression: str, message: str) -> None:
    assert refused(expression) == message


VALUES = {'f': 'float', '#v': 'float', '#w': 'float2', '#t': 'SDTypeTexture'}  # a graph input and three input values
# what a syntax error adds for a `#` and a letter where a comment may have been meant, at its place when the error is
# elsewhere; and a statement of several that starts with such a name (REVIEW.md SRV-210, SRV-215)
NOT_A_COMMENT = "; `%s`%s reads as an input value's name: a comment starts with `# `"
AT = ', at line %d, column %d,'
LEADING = "`%s` starts its statement and reads as an input value's name, %s: a comment starts with `# `"


@pytest.mark.parametrize(
    ('expression', 'inputs', 'message'),
    [
        ('#nope', VALUES, 'column 1: the node has no input value `#nope`; its input values are #t, #v, #w'),
        (
            '#nope',
            {'f': 'float'},
            "column 1: the node has no input value `#nope`, nor any other: connect a value into it first (apply_edits' "
            "connect to input '#nope')",
        ),
        ('foo', VALUES, 'column 1: unknown name `foo`; the graph inputs are f'),
        ('foo', {'#v': 'float'}, 'column 1: unknown name `foo`; the graph has no inputs'),
        ('#t', VALUES, "column 1: input value `#t` has type SDTypeTexture, which a function can't read"),
        ('#v = 1; #v', VALUES, "column 1: `#v` is an input value of the node: it can't be bound"),
        (
            'f#v',
            VALUES,
            "column 2: `#` and a letter start an input value's name, such as #x, which can't follow a name, a number or "
            'a `.`; a comment starts with `# `',
        ),
        (
            '$pos.#v',
            VALUES,
            "column 6: `#` and a letter start an input value's name, such as #x, which can't follow a name, a number or "
            'a `.`; a comment starts with `# `',
        ),
        ('#f(1)', VALUES, 'column 1: `#f(1)`' + GRAMMAR),
        # a comment starts with `# `: `#note` is read as an input value, and the refusal says so (REVIEW.md SRV-210)
        ('f #note', VALUES, 'column 3: invalid syntax' + NOT_A_COMMENT % ('#note', '')),
        ('f * 2  #twice', VALUES, 'column 8: invalid syntax' + NOT_A_COMMENT % ('#twice', '')),
        ('#scale it\nf * 2', VALUES, 'line 1, column 8: invalid syntax' + NOT_A_COMMENT % ('#scale', AT % (1, 1))),
        # the node's own #v, read on purpose, is passed over: #double is named, and with no other #name, nothing is.
        # Nor is a #name in a comment (REVIEW.md SRV-213)
        ('#v * 2  #double', VALUES, 'column 9: invalid syntax' + NOT_A_COMMENT % ('#double', '')),
        ('#v * (1 2)', VALUES, 'column 7: invalid syntax. Perhaps you forgot a comma?'),
        ('f *  # see #now', VALUES, 'column 6: invalid syntax'),
        # refused before the other lines, which blamed another line: `x` "gives a value before the last statement"
        ('x = f * 2\nx\n#done', VALUES, 'line 3, column 1: ' + LEADING % ('#done', 'which the node lacks')),
        ('#done\nf * 2', VALUES, 'line 1, column 1: ' + LEADING % ('#done', 'which the node lacks')),
        ('x = f * 2\n#done', VALUES, 'line 2, column 1: ' + LEADING % ('#done', 'which the node lacks')),
        # a comment of more words, parsed as more than a name (REVIEW.md SRV-215)
        ('x = f * 2\nx\n#half-res', VALUES, 'line 3, column 1: ' + LEADING % ('#half', 'which the node lacks')),
        ('x = f * 2\nx\n#scale and bias', VALUES, 'line 3, column 1: ' + LEADING % ('#scale', 'which the node lacks')),
        ('x = f * 2\n#TODO: tune\nx', VALUES, 'line 2, column 1: ' + LEADING % ('#TODO', 'which the node lacks')),
        ('x = f * 2\n#scale = 2\nx', VALUES, 'line 2, column 1: ' + LEADING % ('#scale', 'which the node lacks')),
        # the node's own #v alone, or #nope as the whole expression: no comment
        ('x = f\n#v', VALUES, 'line 1, column 1: `x` is bound but never used'),
    ],
)
def test_each_mistake_with_an_input_value_is_refused(expression: str, inputs: dict[str, str], message: str) -> None:
    assert refused(expression, inputs) == message


def test_an_unknown_name_in_a_graph_without_inputs_says_so() -> None:
    assert refused('foo', {}) == 'column 1: unknown name `foo`; the graph has no inputs'


# Calls to the package's function graphs (set_function's `function`)

# what the read gives of the package's function graphs: paint(uv, k), a float4; wrap(uv), calling paint; deep(),
# calling wrap; pi(), with no inputs; flag(on), a bool input; unset(), with no output of one type
PACKAGE = {
    'paint': Resource({'uv': 'float2', 'k': 'float'}, 'float4', ()),
    'wrap': Resource({'uv': 'float2'}, 'float4', ('paint',)),
    'deep': Resource({}, 'float4', ('wrap',)),
    'pi': Resource({}, 'float', ()),
    'flag': Resource({'on': 'bool'}, 'float', ()),
    'unset': Resource({}, None, ()),
}


@pytest.mark.parametrize(
    ('expression', 'built', 'type_'),
    [
        ('paint($pos, f)', 'instance[paint](get_float2[$pos], get_float1[f])', 'float4'),
        # a number takes its input's type, as elsewhere
        ('paint(0.5, 1)', 'instance[paint](const_float2[0.5, 0.5], const_float1[1.0])', 'float4'),
        ('pi()', 'instance[pi]()', 'float'),
        ('flag(b)', 'instance[flag](get_bool[b])', 'float'),
        ('paint(v2, f).zx', 'swizzle2[2, 0](instance[paint](get_float2[v2], get_float1[f]))', 'float2'),
    ],
)
def test_a_call_builds_an_instance_of_the_function_graph(expression: str, built: str, type_: str) -> None:
    f = compiled(expression, functions=PACKAGE)
    assert tree(f) == built
    assert f['type'] == type_


def test_a_call_reads_each_argument_once_and_feeds_other_nodes() -> None:
    f = compiled('x = pi(); x * paint(v2, x).w', functions=PACKAGE)
    assert [n['definition'] for n in f['nodes']].count('instance') == 2
    assert f['type'] == 'float'


def test_a_grammar_function_wins_over_a_function_graph_named_alike() -> None:
    # set_function refuses to make one (name_refusal); a person could have, in Designer
    f = compiled('abs(f)', functions={'abs': Resource({'x': 'float2'}, 'float4', ())})
    assert tree(f) == 'abs(get_float1[f])'


def test_an_input_named_like_a_function_graph_is_read_and_the_call_still_calls(  # REVIEW.md TST-734
) -> None:
    f = compiled('paint(v2, paint)', {**INPUTS, 'paint': 'float'}, PACKAGE)
    assert tree(f) == 'instance[paint](get_float2[v2], get_float1[paint])'


# a diamond: top calls a and b, each calling c (REVIEW.md TST-734)
DIAMOND = {
    'top': Resource({}, 'float', ('a', 'b')),
    'a': Resource({}, 'float', ('c',)),
    'b': Resource({}, 'float', ('c',)),
    'c': Resource({}, 'float', ()),
}


def test_a_diamond_of_calls_not_reaching_the_function_graph_defined_compiles() -> None:
    assert tree(compile_expression('top() + a()', {}, DIAMOND, defining='d')) == 'add(instance[top](), instance[a]())'


def test_a_diamond_of_calls_reaching_the_function_graph_defined_is_refused() -> None:
    assert refused('top()', {}, DIAMOND, 'c') == (
        "column 1: `top()` calls top, which calls a, which calls c: a function can't call itself, through others either"
    )


def test_a_function_graphs_input_no_function_reads_is_called_its_input() -> None:  # REVIEW.md HLP-239
    assert refused('x', {'x': 'SDTypeTexture'}, PACKAGE, 'paint') == (
        "column 1: input `x` has type SDTypeTexture, which a function can't read"
    )


def test_a_statement_led_by_the_nodes_own_input_value_compiles() -> None:  # REVIEW.md SRV-215
    assert tree(compiled('k = #v * 2\n#v - k', VALUES)) == (
        'sub(get_float1[#v], mul(get_float1[#v], const_float1[2.0]))'
    )


def test_a_comment_without_its_space_in_a_function_graphs_expression_is_named() -> None:  # REVIEW.md SRV-210
    leading = LEADING % ('#done', 'and a function graph has none')
    assert refused('x = k * 2\nx\n#done', {'k': 'float'}, PACKAGE, 'paint') == 'line 3, column 1: ' + leading
    assert refused('x = k\n#done', {'k': 'float'}, PACKAGE, 'paint') == 'line 2, column 1: ' + leading


def test_a_function_graph_without_inputs_says_so_of_an_unknown_name() -> None:  # REVIEW.md TST-734
    assert refused('nope', {}, PACKAGE, 'paint') == 'column 1: unknown name `nope`; it has no inputs'


def test_function_graphs_calling_each_other_in_a_loop_compile_a_call_to_one() -> None:
    # a loop a person made: the search for one through the function being built ends
    loop = {'a': Resource({}, 'float', ('b',)), 'b': Resource({}, 'float', ('a',))}
    assert tree(compile_expression('a()', {}, loop, defining='c')) == 'instance[a]()'


@pytest.mark.parametrize(
    ('expression', 'defining', 'message'),
    [
        ('paint($pos)', None, 'column 1: paint takes 2 arguments (uv float2, k float), and `paint($pos)` gives 1'),
        ('pi(1)', None, 'column 1: pi takes no arguments, and `pi(1)` gives 1'),
        ('wrap(v2, f)', None, 'column 1: wrap takes 1 argument (uv float2), and `wrap(v2, f)` gives 2'),
        ('paint(f, f)', None, 'column 7: `f` is a float, where `paint(f, f)` takes a float2'),
        ('paint(v2, i)', None, 'column 11: `i` is an int, where `paint(v2, i)` takes a float: write float(i)'),
        ('flag(1)', None, 'column 6: `1` must be a bool here: write true or false'),
        (
            'unset()',
            None,
            'column 1: `unset()` calls unset, which has no output node of one type: give it its function with '
            'set_function first',
        ),
        (
            'nope(f)',
            None,
            'column 1: unknown function `nope`; the functions are %s; the package has deep, flag, paint, pi, unset, '
            'wrap' % FUNCTIONS,
        ),
        ('paint($pos, f)', 'paint', "column 1: `paint($pos, f)` calls paint itself: a function can't call itself"),
        # a new one, not in the package yet
        ('fresh(f)', 'fresh', "column 1: `fresh(f)` calls fresh itself: a function can't call itself"),
        (
            'wrap($pos)',
            'paint',
            "column 1: `wrap($pos)` calls wrap, which calls paint: a function can't call itself, through others either",
        ),
        (
            'deep()',
            'paint',
            "column 1: `deep()` calls deep, which calls wrap, which calls paint: a function can't call itself, through "
            'others either',
        ),
        ('#x', 'paint', 'column 1: `#x` is an input value, and a function graph has none: it reads its inputs by id'),
        ('f = 1; f', 'paint', 'column 1: `f` is an input: bind another name'),
        ('nope', 'paint', 'column 1: unknown name `nope`; its inputs are b, c, f, g, i, i2, i3, s, v2, v3'),
        # a function graph has no input values: neither bound nor written after a name (REVIEW.md SRV-197)
        # a binding is refused as a comment without its space, as any statement led by such a name (REVIEW.md SRV-215)
        ('#x = 1; 0.5', 'paint', 'column 1: ' + LEADING % ('#x', 'and a function graph has none')),
        (
            'f#x',
            'paint',
            "column 2: `#` and a letter start an input value's name, and a function graph has none; a comment starts "
            'with `# `',
        ),
        # the function graph being defined isn't one the package has to call (REVIEW.md SRV-197)
        (
            'nope(f)',
            'paint',
            'column 1: unknown function `nope`; the functions are %s; the package has deep, flag, pi, unset, wrap'
            % FUNCTIONS,
        ),
    ],
)
def test_each_mistake_in_a_call_is_refused(expression: str, defining: str | None, message: str) -> None:
    assert refused(expression, INPUTS, PACKAGE, defining) == message


@pytest.mark.parametrize(
    ('name', 'called_', 'refusal'),
    [
        ('paint', True, None),
        ('uv_2', False, None),
        ('abs', False, None),  # an input named like a function: a name, never a call
        ('clamp', True, '`clamp` is a function of the grammar, which a call by that name would build'),
        ('sample_lum', True, '`sample_lum` is a function of the grammar, which a call by that name would build'),
        ('float2', True, '`float2` is a cast of the grammar, which a call by that name would build'),
        ('int', True, '`int` is a cast of the grammar, which a call by that name would build'),
        ('true', False, '`true` is a constant of the grammar'),
        ('and', True, "`and` is one of Python's keywords, which an expression can't write as a name"),
        ('None', False, "`None` is one of Python's keywords, which an expression can't write as a name"),
        (
            '2pi',
            True,
            '`2pi` is not a name an expression can write: write letters, digits and _, not starting with a digit',
        ),
        (
            'a-b',
            False,
            '`a-b` is not a name an expression can write: write letters, digits and _, not starting with a digit',
        ),
        ('', True, '`` is not a name an expression can write: write letters, digits and _, not starting with a digit'),
        (
            '#x',
            False,
            '`#x` is not a name an expression can write: write letters, digits and _, not starting with a digit',
        ),
    ],
)
def test_a_name_an_expression_cannot_write_is_refused(name: str, called_: bool, refusal: str | None) -> None:
    assert name_refusal(name, called_) == refusal


# Sampling a processor's input images: sample() builds samplecol, sample_lum() samplelum, their __constant__ (the
# input's index, the mode), the mode 1 for bilinear plus 2 for clamp (the functions category, check_sampling_an_image)


@pytest.mark.parametrize(
    ('expression', 'built', 'type_'),
    [
        # nearest and repeat, as a new Sample node starts
        ('sample(0, $pos)', 'samplecol[0, 0](get_float2[$pos])', 'float4'),
        ('sample_lum(1, v2)', 'samplelum[1, 0](get_float2[v2])', 'float'),
        ("sample(0, $pos, filter='bilinear')", 'samplecol[0, 1](get_float2[$pos])', 'float4'),
        ("sample(0, $pos, wrap='clamp')", 'samplecol[0, 2](get_float2[$pos])', 'float4'),
        ("sample_lum(2, v2, wrap='clamp', filter='bilinear')", 'samplelum[2, 3](get_float2[v2])', 'float'),
        ("sample(1, v2, filter='nearest', wrap='repeat')", 'samplecol[1, 0](get_float2[v2])', 'float4'),
        # a number takes pos's type, as elsewhere; a name bound to a number is a number at each use
        ('sample(0, 0.5)', 'samplecol[0, 0](const_float2[0.5, 0.5])', 'float4'),
        ('k = 2; sample(k, $pos)', 'samplecol[2, 0](get_float2[$pos])', 'float4'),
        ('sample(0, $pos).zx', 'swizzle2[2, 0](samplecol[0, 0](get_float2[$pos]))', 'float2'),
    ],
)
def test_a_sample_builds_its_node_with_the_index_and_the_mode(expression: str, built: str, type_: str) -> None:
    f = compiled(expression, images=True)
    assert (tree(f), f['type']) == (built, type_)


def test_the_function_lists_the_input_images_it_samples() -> None:
    assert compiled('sample(1, $pos) + sample(0, $pos) * sample_lum(1, $pos)', images=True)['samples'] == [0, 1]
    assert compiled('f', images=True)['samples'] == []


def test_a_processors_function_samples_any_index() -> None:
    # a processor lists each input once the one before it is connected, 40 measured (the functions category,
    # check_a_processors_image_inputs): set_function says which sampled input has nothing connected
    assert compiled('sample(70, $pos)', images=True)['samples'] == [70]


def test_a_function_graphs_expression_samples_any_index() -> None:
    # its callers' input images (the functions category: a function graph samples its caller's)
    f = compiled('sample(3, uv)', {'uv': 'float2'}, images=True, defining='blur')
    assert (tree(f), f['samples']) == ('samplecol[3, 0](get_float2[uv])', [3])


# blur(uv) samples input image 1; soft(uv) calls blur; plain() samples none
SAMPLING = {
    'blur': Resource({'uv': 'float2'}, 'float4', (), (1,)),
    'soft': Resource({'uv': 'float2'}, 'float4', ('blur',)),
    'plain': Resource({}, 'float', ()),
}


def test_a_call_samples_what_its_function_graph_samples_through_the_others_it_calls() -> None:
    f = compiled('soft($pos) * plain() + sample(0, $pos)', functions=SAMPLING, images=True)
    assert f['samples'] == [0, 1]
    assert compiled('plain()', functions=SAMPLING)['samples'] == []  # a parameter's function calls one sampling none


@pytest.mark.parametrize(
    ('expression', 'images', 'message'),
    [
        # only a Pixel or Value Processor's function has input images: a parameter's has none
        (
            'sample(0, $pos)',
            False,
            "column 1: `sample(0, $pos)` samples an input image, and only a Pixel or Value Processor's function has "
            'input images, or a function graph it calls',
        ),
        (
            'soft($pos)',
            False,
            "column 1: `soft($pos)` calls soft, which samples input image 1, and only a Pixel or Value Processor's "
            'function has input images',
        ),
        # the index: a whole number from 0
        (
            'sample(f, $pos)',
            True,
            "column 8: `f` is a float, where `sample(f, $pos)` takes an input image's index: write a whole number, 0 "
            'for input, 1 for input:1...',
        ),
        (
            'sample(true, $pos)',
            True,
            "column 8: `true` is a bool, where `sample(true, $pos)` takes an input image's index: write a whole "
            'number, 0 for input, 1 for input:1...',
        ),
        (
            'sample(1.0, $pos)',
            True,
            "column 8: `1.0` must be an input image's index here: write a whole number, 0 for input, 1 for input:1...",
        ),
        # beyond what __constant__ holds (GUIDE.md, Sampling an image; REVIEW.md SRV-201)
        (
            'sample(2147483648, $pos)',
            True,
            'column 8: `2147483648` is above 2147483647, the largest index Designer holds: a larger one wraps around to '
            'a negative index',
        ),
        (
            'sample(-1, $pos)',
            True,
            "column 8: `-1` must be an input image's index here: write a whole number, 0 for input, 1 for input:1...",
        ),
        # pos: a float2, as for every other connection (Designer connects a float silently)
        ('sample(0, f)', True, 'column 11: `f` is a float, where `sample(0, f)` takes a float2'),
        ('sample(0, v3)', True, 'column 11: `v3` is a float3, where `sample(0, v3)` takes a float2: write v3.xy'),
        ('sample(0, i2)', True, 'column 11: `i2` is an int2, where `sample(0, i2)` takes a float2: write float2(i2)'),
        # filter and wrap: by name, each one of its words
        (
            "sample(0, $pos, filter='cubic')",
            True,
            "column 17: `filter='cubic'`: filter is 'nearest' or 'bilinear', written as such",
        ),
        (
            'sample(0, $pos, filter=f)',
            True,
            "column 17: `filter=f`: filter is 'nearest' or 'bilinear', written as such",
        ),
        (
            "sample(0, $pos, wrap='mirror')",
            True,
            "column 17: `wrap='mirror'`: wrap is 'repeat' or 'clamp', written as such",
        ),
        (
            'sample(0, $pos, mode=1)',
            True,
            'column 1: `sample(0, $pos, mode=1)` names the argument mode: sample takes filter= and wrap= by name',
        ),
        (
            "sample(0, $pos, 'nearest')",
            True,
            "column 1: sample takes 2 arguments, then filter= and wrap= by name, and `sample(0, $pos, 'nearest')` "
            'gives 3',
        ),
        (
            'sample_lum(0)',
            True,
            'column 1: sample_lum takes 2 arguments, then filter= and wrap= by name, and `sample_lum(0)` gives 1',
        ),
        ('sqrt(a=f)', True, 'column 1: `sqrt(a=f)` names an argument: arguments are given by position'),
        # an argument given twice would add its mode twice (REVIEW.md SRV-200)
        (
            "sample(0, $pos, filter='bilinear', filter='bilinear')",
            True,
            "column 36: `filter='bilinear'` gives filter a second time: give filter= and wrap= once each",
        ),
        (
            "sample_lum(0, $pos, wrap='clamp', filter='nearest', wrap='repeat')",
            True,
            "column 53: `wrap='repeat'` gives wrap a second time: give filter= and wrap= once each",
        ),
    ],
)
def test_each_mistake_in_a_sample_is_refused(expression: str, images: bool, message: str) -> None:
    assert refused(expression, functions=SAMPLING, images=images) == message
