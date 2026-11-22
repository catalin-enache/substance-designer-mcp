"""An expression compiled into the function nodes Designer builds (ROADMAP item 9): pure Python, run on the server.

compile_expression(expression, inputs, functions, defining, images, kind) returns a Function: the result's type, the nodes
to build, each fed only by earlier ones, and the input images it samples. Every name, and the type of every connection, is checked against DEFINITIONS
first, as Designer connects a wrong type silently and computes a wrong value (GUIDE.md, Building a function graph).
A mistake raises ExpressionError, naming its place in the expression and what was expected there.

The grammar is Python's expressions, parsed with `ast`, each `$` and each `#` of a name read as `_` so that the
columns stay the text's:
- statements `name = value`, on lines of their own or after `;`, then the result. The indent they all hold is left
  out. A name is bound once, and every use reads its one node. A name bound to a number is a number at each use;
- comments: a `#` followed by a letter starts an input value's name, and any other `#` starts a comment, to the end
  of its line. A refusal names such a name where a comment written without its space may have been meant: one
  starting a statement of several (LEADING), or one before a syntax error on its line (_value_before);
- numbers, which take the type their context needs, int or float, in each component; alone, a float. `true`, `false`;
- graph inputs by their id, the node's input values by their `#name`, and Designer's variables (VARIABLES), each read
  by one get_* node. An FX-Map's variables (FX_MAP) are refused, and so is `$pos` in a Value Processor's or a
  parameter's function (NOT_THE_PIXELS);
- float() to int4(): a cast of one value of that size, or a vector of components that add up to it;
- swizzles, `.x` to `.wzyx` and `.r` to `.abgr`;
- `+ - * / %`, unary `-`, comparisons, `and`, `or`, `not` and `a if condition else b`. A float or a number times a
  float vector multiplies it (mulscalar). In `+ - /`, a float with a float vector is made a vector. Any other mix is
  refused, naming the cast or the swizzle to write;
- Designer's functions, and atan2(y, x), clamp, length and normalize, built from Designer's nodes (ARITY);
- the package's function graphs, called by their identifier with their inputs in order, each built as an instance
  node (Resource). A function graph's own expression reads its inputs by id, and can't call itself, directly or
  through others;
- sample(index, pos) and sample_lum(index, pos), with filter= and wrap= by name (SAMPLE_MODES): a samplecol or
  samplelum node reading a Pixel or Value Processor's input image `index` at pos. Only those processors' functions
  have input images, and a function graph samples its caller's (GUIDE.md, Sampling an image). So a processor's
  function and a function graph's (`images`) sample any index an int holds, and a parameter's function none, its
  calls included. Which input sampled has nothing connected is set_function's to say: the function reads (0, 0, 0, 0)
  there until an image is connected, and Designer lists each input once the one before it is connected (GUIDE.md, A
  processor's input images).

Designer computes negative ints wrongly (GUIDE.md, What nodes compute: measured on macOS arm64), so a negative int
number and unary minus on an int are refused, naming the float form. An int that goes negative as the function runs,
such as `i - j`, isn't seen.
"""

import ast
import dataclasses
import keyword
import math
import re
import textwrap
from collections.abc import Mapping, Sequence
from typing import Literal, NamedTuple, TypedDict


class Definition(NamedTuple):
    """A `sbs::function::` definition: its inputs' ids, each with the types it takes, and its output's types."""

    inputs: dict[str, tuple[str, ...]]
    output: tuple[str, ...]


# the types Designer lists for inputs and outputs, in its order
NUMBERS = ('int', 'int2', 'int3', 'int4', 'float', 'float2', 'float3', 'float4')
INTS, FLOATS = NUMBERS[:4], NUMBERS[4:]
READABLE = ('bool', *NUMBERS, 'string')  # the types a get_* node reads
ANY = (*READABLE, 'void')
SCALAR, BOOL = ('float',), ('bool',)

# Designer's 85 definitions, as `getDefinitions()` gives them: the functions category compares them
# (check_the_function_definitions). Each has one output, `unique_filter_output`, and every input but `__constant__`
# connects
DEFINITIONS: dict[str, Definition] = {
    **{d: Definition({'a': NUMBERS, 'b': NUMBERS}, NUMBERS) for d in ('add', 'sub', 'mul', 'min', 'max')},
    **{d: Definition({'a': ('int', *FLOATS), 'b': ('int', *FLOATS)}, ('int', *FLOATS)) for d in ('div', 'mod')},
    **{d: Definition({'a': ('int', *FLOATS)}, ('int', *FLOATS)) for d in ('abs', 'neg')},
    **{
        d: Definition({'a': FLOATS}, FLOATS)
        for d in ('ceil', 'cos', 'exp', 'floor', 'log', 'log2', 'pow2', 'sin', 'sqrt', 'tan')
    },
    'pow': Definition({'a': FLOATS, 'b': FLOATS}, FLOATS),
    'lerp': Definition({'a': FLOATS, 'b': FLOATS, 'x': SCALAR}, FLOATS),
    'dot': Definition({'a': FLOATS[1:], 'b': FLOATS[1:]}, SCALAR),
    'mulscalar': Definition({'a': FLOATS[1:], 'scalar': SCALAR}, FLOATS[1:]),
    **{
        d: Definition({'a': ('int', 'float'), 'b': ('int', 'float')}, BOOL)
        for d in ('eq', 'noteq', 'gt', 'gteq', 'lr', 'lreq')
    },
    **{d: Definition({'a': BOOL, 'b': BOOL}, BOOL) for d in ('and', 'or')},
    'not': Definition({'a': BOOL}, BOOL),
    'atan2': Definition({'a': ('float2',)}, SCALAR),
    'cartesian': Definition({'rho': SCALAR, 'theta': SCALAR}, ('float2',)),
    'rand': Definition({'a': SCALAR}, SCALAR),
    'ifelse': Definition({'condition': BOOL, 'ifpath': ANY, 'elsepath': ANY}, ANY),
    'passthrough': Definition({'input': ANY}, ANY),
    'sequence': Definition({'seqin': ANY, 'seqlast': ANY}, ANY),
    'while': Definition({'init': ANY, 'cond': BOOL, 'loop': ANY, '__constant__': ('int',)}, ANY),
    'set': Definition({'value': READABLE, '__constant__': ('string',)}, READABLE),
    'isdefined': Definition({'__constant__': ('string',)}, BOOL),
    # __constant__: the input image's index, and the mode (SAMPLE_MODES)
    'samplecol': Definition({'pos': ('float2',), '__constant__': ('int2',)}, ('float4',)),
    'samplelum': Definition({'pos': ('float2',), '__constant__': ('int2',)}, SCALAR),
    # by size n: vectors of components, swizzles of a vector by index, casts, constants and reads of a variable
    **{
        '%svector%d' % (i, n): Definition(
            {'componentsin': kind[: n - 1], 'componentslast': kind[: n - 1]}, (kind[n - 1],)
        )
        for i, kind in (('', FLOATS), ('i', INTS))
        for n in (2, 3, 4)
    },
    **{
        '%sswizzle%d' % (i, n): Definition({'vector': kind, '__constant__': (INTS[n - 1],)}, (kind[n - 1],))
        for i, kind in (('', FLOATS), ('i', INTS))
        for n in (1, 2, 3, 4)
    },
    **{
        'tofloat%s' % ('' if n == 1 else n): Definition({'value': (INTS[n - 1],)}, (FLOATS[n - 1],))
        for n in (1, 2, 3, 4)
    },
    **{'toint%d' % n: Definition({'value': (FLOATS[n - 1],)}, (INTS[n - 1],)) for n in (1, 2, 3, 4)},
    **{
        'const_%s%d' % (name, n): Definition({'__constant__': (kind[n - 1],)}, (kind[n - 1],))
        for name, kind in (('float', FLOATS), ('int', INTS))
        for n in (1, 2, 3, 4)
    },
    **{'const_%s' % t: Definition({'__constant__': (t,)}, (t,)) for t in ('bool', 'string')},
    **{
        'get_%s%d' % (name, n): Definition({'__constant__': ('string',)}, (kind[n - 1],))
        for name, kind in (('float', FLOATS), ('integer', INTS))
        for n in (1, 2, 3, 4)
    },
    **{'get_%s' % t: Definition({'__constant__': ('string',)}, (t,)) for t in ('bool', 'string')},
}

# Designer's variables a function reads, by their type (Adobe's system-variables page; the functions category measures
# all but $time). FX_MAP's are an FX-Map's: Adobe's page lists them there, and Designer's own packages read them only
# in FX-Maps
VARIABLES = {'$pos': 'float2', '$size': 'float2', '$sizelog2': 'float2', '$tiling': 'int', '$time': 'float'}
FX_MAP = ('$depth', '$number')
# a node's function: a Pixel Processor's perpixel, a Value Processor's function, or a parameter's
type Kind = Literal['perpixel', 'function', 'parameter']
# where `$pos` isn't the pixel's position, by a node's function's kind, and what it reads there (GUIDE.md, Variables;
# the functions category's check_system_variables)
NOT_THE_PIXELS: dict[Kind, str] = {
    'function': "a Value Processor's function, where it reads (0, 0)",
    'parameter': "a parameter's function, where it reads another value",
}

# sample() and sample_lum(), and the definition each builds; the mode their __constant__ adds up, by each argument and
# word (the functions category, check_sampling_an_image). Neither given, 0: nearest and repeat, as a new node starts
SAMPLES = {'sample': 'samplecol', 'sample_lum': 'samplelum'}
SAMPLE_MODES = {'filter': {'nearest': 0, 'bilinear': 1}, 'wrap': {'repeat': 0, 'clamp': 2}}

type Constant = bool | int | float | str | tuple[int, ...] | tuple[float, ...]


class Node(TypedDict):
    """A node to build: its definition (without `sbs::function::`), its output's type, its `__constant__` (None when
    the definition has none) and, for each of its other inputs, the index of the node feeding it. An instance node of
    the package's function graph has the definition `instance`, and that graph's identifier as its constant."""

    definition: str
    type: str
    constant: Constant | None
    inputs: dict[str, int]


class Function(TypedDict):
    """The nodes of a compiled expression, each fed only by earlier ones, which of them is the output, and the indices
    of the input images it samples, through the function graphs it calls too."""

    type: str
    nodes: list[Node]
    output: int
    samples: list[int]


class Resource(NamedTuple):
    """A function graph of the package, as an expression calls it: its inputs' ids and types, in the order a call gives
    them; its output's type, None when it has no output node of one type; the package's function graphs it calls; the
    indices of its caller's input images its own nodes sample."""

    inputs: dict[str, str]
    output: str | None
    calls: tuple[str, ...]
    samples: tuple[int, ...] = ()


class ExpressionError(ValueError):
    """An expression refused: the message names the place, and what was expected there."""


def compile_expression(
    expression: str,
    inputs: Mapping[str, str],
    functions: Mapping[str, Resource] | None = None,
    defining: str | None = None,
    images: bool = False,
    kind: Kind | None = None,
) -> Function:
    """The nodes `expression` compiles to, reading the graph inputs and the node's input values `inputs` ({id: type},
    such as 'float2' or 'int'; an input value's id is its `#name`) and calling the package's function graphs
    `functions`, by identifier, every name and type checked. `defining` is the function graph whose expression this
    is: then `inputs` are its own, and a call reaching it again is refused. `images` says the function has input images
    to sample: a Pixel or Value Processor's, or a function graph's, which samples its caller's. A parameter's function
    has none. `kind` is a node's function's: `$pos` is refused in a Value Processor's and a parameter's (NOT_THE_PIXELS),
    and None, for a function graph's, which can't know its callers, refuses it nowhere. A call into a function graph
    reading `$pos` isn't checked, as a Resource carries no flag for it. Raises ExpressionError on the first mistake,
    naming its place."""
    return _Compiler(expression, inputs, functions or {}, defining, images, kind).compiled()


def image_input(index: int) -> str:
    """A Pixel or Value Processor's input image `index`, as Designer names its connector: input, input:1, input:2..."""
    return 'input:%d' % index if index else 'input'


NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')  # a name an expression writes: a function graph's, an input's
VALUE_NAME = re.compile(r'#[A-Za-z][A-Za-z0-9_]*')  # an input value's name, `#` and a letter first


def name_refusal(name: str, called: bool) -> str | None:
    """Why an expression can't write `name` as the identifier of a function graph it calls (`called`) or of an input it
    reads; None when it can. A function graph named like one of the grammar's functions or casts would never be called:
    the call builds the grammar's."""
    if not NAME.fullmatch(name):
        return (
            '`%s` is not a name an expression can write: write letters, digits and _, not starting with a digit' % name
        )
    if keyword.iskeyword(name):
        return "`%s` is one of Python's keywords, which an expression can't write as a name" % name
    if name in BOOLS:
        return '`%s` is a constant of the grammar' % name
    if called and name in FUNCTIONS:
        what = 'a cast' if name in NUMBERS else 'a function'
        return '`%s` is %s of the grammar, which a call by that name would build' % (name, what)
    return None


def getter_of(type_: str) -> str:
    """The get_* definition that reads a graph input or a variable of type `type_`, such as get_float2 for 'float2'."""
    return _named('get_', type_)


# the grammar's functions, by their number of arguments: Designer's own, taking their definition's inputs in order;
# those built from Designer's nodes; float() and int(). float2() to int4() take components that add up (_vector)
ARITY = {
    **{
        d: len(DEFINITIONS[d].inputs)
        for d in (
            *('abs', 'cartesian', 'ceil', 'cos', 'dot', 'exp', 'floor', 'lerp', 'log', 'log2', 'max', 'min', 'pow'),
            *('rand', 'sin', 'sqrt', 'tan'),
        )
    },
    'atan2': 2,
    'clamp': 3,
    **dict.fromkeys(SAMPLES, 2),  # then filter= and wrap= by name
    'length': 1,
    'normalize': 1,
    'float': 1,
    'int': 1,
}
FUNCTIONS = sorted({*ARITY, *NUMBERS})
BOOLS = {'true': True, 'false': False}
ARITHMETIC: dict[type[ast.operator], str] = {
    ast.Add: 'add',
    ast.Sub: 'sub',
    ast.Mult: 'mul',
    ast.Div: 'div',
    ast.Mod: 'mod',
}
HINTS: dict[type[ast.operator], str] = {ast.Pow: ': write pow(%s, %s)', ast.FloorDiv: ': write floor(%s / %s)'}
COMPARISONS: dict[type[ast.cmpop], tuple[str, str]] = {
    ast.Eq: ('eq', '=='),
    ast.NotEq: ('noteq', '!='),
    ast.Lt: ('lr', '<'),
    ast.LtE: ('lreq', '<='),
    ast.Gt: ('gt', '>'),
    ast.GtE: ('gteq', '>='),
}
WRONGLY = ', which Designer computes wrongly'  # negative ints (GUIDE.md, What nodes compute)
COMMENT = 'a comment starts with `# `'
# what a misplaced `$` or `#` is told
SIGILS = {
    '$': "`$` starts a variable's name, such as $pos",
    '#': "`#` and a letter start an input value's name, such as #x, which can't follow a name, a number or a `.`; "
    + COMMENT,
}
# a misplaced `#` in a function graph's expression, which reads no input values (REVIEW.md SRV-197)
NO_VALUES = "`#` and a letter start an input value's name, and a function graph has none; " + COMMENT
# a statement of several that starts with a `#` and a letter naming no input value: a comment written without its
# space, or a mistake (REVIEW.md SRV-210, SRV-215)
LEADING = "`%s` starts its statement and reads as an input value's name, %s: " + COMMENT
# an input value read in a function graph's expression (one bound is refused first: LEADING)
NONE_HERE = '`%s` is an input value, and a function graph has none: it reads its inputs by id'
STATEMENT = (
    ' is not part of the grammar: a statement binds one name (`name = value`), and the last one gives the result'
)
ONLY_PROCESSORS = "only a Pixel or Value Processor's function has input images"  # a sample anywhere else
INDEX = "an input image's index"
INT_MAX = 2**31 - 1  # the largest index __constant__ holds (GUIDE.md, Sampling an image; REVIEW.md SRV-201)
WHOLE = ': write a whole number, 0 for input, 1 for input:1...'


@dataclasses.dataclass(frozen=True)
class _Built:
    """A node built: its type, its index, and the expression it stands for, for messages."""

    type: str
    node: int
    at: ast.expr


@dataclasses.dataclass(frozen=True)
class _Literal:
    """A number not built yet: it takes the type its context needs."""

    value: int | float
    at: ast.expr


type _Value = _Built | _Literal


def _kind(t: str) -> str:
    """'int' or 'float' for a number type, else the type itself ('bool', 'string')."""
    return t.rstrip('234') if t in NUMBERS else t


def _size(t: str) -> int:
    return int(t[-1]) if t[-1] in '234' else 1


def _sized(kind: str, n: int) -> str:
    return kind if n == 1 else '%s%d' % (kind, n)


def with_article(t: str) -> str:
    """A type as a message names it: 'a float', 'an int2'."""
    return ('an ' if t.startswith('int') else 'a ') + t


def joined_with(items: Sequence[str], word: str) -> str:
    """'a', 'a and b', 'a, b and c' (or `word`)."""
    return items[0] if len(items) == 1 else '%s %s %s' % (', '.join(items[:-1]), word, items[-1])


def _listed(types: tuple[str, ...]) -> str:
    """'a float', 'an int or float', 'a float, float2, float3 or float4'."""
    return with_article(joined_with(types, 'or'))


def _scalar_and_vector(a: _Value, b: _Value) -> tuple[_Value, _Built] | None:
    """A float or a number, and a float vector, in that order, when `a` and `b` are one of each."""
    for scalar, vector in ((a, b), (b, a)):
        if (
            isinstance(vector, _Built)
            and vector.type in FLOATS[1:]
            and (isinstance(scalar, _Literal) or scalar.type == 'float')
        ):
            return scalar, vector
    return None


def _named(prefix: str, type_: str) -> str:
    """The definition starting with `prefix` whose output is `type_`: ('const_', 'float2') gives const_float2."""
    return next(d for d, definition in DEFINITIONS.items() if d.startswith(prefix) and definition.output == (type_,))


def _nearest(types: tuple[str, ...], have: str) -> str | None:
    """The number type of `types` closest to `have`, by size, then kind: what a hint converts `have` to. It is no
    larger than `have`: a float made a vector would compute another value in dot, length and normalize."""
    if have not in NUMBERS:
        return None
    fits = [t for t in types if t in NUMBERS and _size(t) <= _size(have)]
    return min(fits, key=lambda t: (_size(have) - _size(t), _kind(t) != _kind(have)), default=None)


def converted(text: str, have: str, need: str) -> str:
    """`text`, of type `have`, written as a `need`: a swizzle, then a cast, then a vector of a float. '' unless both are
    numbers, and for a vector to a larger one, which takes components only the writer knows."""
    if have not in NUMBERS or need not in NUMBERS or 1 < _size(have) < _size(need):
        return ''
    kind, n = _kind(need), _size(need)
    if _size(have) > n:
        text = '%s.%s' % (text if re.fullmatch(r'[\w$.]+', text) else '(%s)' % text, 'xyzw'[:n])
        have = _sized(_kind(have), n)
    if _kind(have) != kind:
        have = _sized(kind, _size(have))
        text = '%s(%s)' % (have, text)
    if _size(have) < n:
        text = '%s(%s)' % (need, ', '.join([text] * n))
    return text


def _code(line: str) -> str:
    """The part of an expression's line before its comment, which a `#` not followed by a letter starts."""
    comment = re.search(r'#(?![A-Za-z])', line)
    return line[: comment.start()] if comment else line


class _Compiler:
    """One expression's compilation: the nodes built so far, and the names they are known by."""

    def __init__(
        self,
        text: str,
        inputs: Mapping[str, str],
        functions: Mapping[str, Resource],
        defining: str | None,
        images: bool,
        kind: Kind | None,
    ) -> None:
        # the indent every line holds is left out before parsing, and added back to the columns of the messages
        self.text = textwrap.dedent(text)
        self.lines = self.text.split('\n')
        pairs = zip(text.split('\n'), self.lines, strict=True)
        self.indent = next((len(given) - len(read) for given, read in pairs if read.strip()), 0)
        self.multiline = '\n' in text.strip()
        self.inputs = inputs
        self.functions = functions
        self.defining = defining
        self.images = images
        self.kind = kind
        self.sampled: set[int] = set()  # the input images sampled, by index, through calls too
        self.nodes: list[Node] = []
        self.gets: dict[str, _Built] = {}  # one get node per graph input or variable read
        self.bound: dict[str, tuple[_Value, ast.Name]] = {}  # each name's value, and where it is bound
        self.used: set[str] = set()

    def compiled(self) -> Function:
        statements = self._statements()
        if not statements:
            raise ExpressionError('the expression is empty')
        if len(statements) > 1:
            self._refuse_a_leading_value(statements)
        *bindings, last = statements
        for statement in bindings:
            if isinstance(statement, ast.Expr):
                raise self._error(
                    statement,
                    '`%s` gives a value before the last statement: bind it to a name (`name = value`)'
                    % self._text(statement),
                )
            if not (
                isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(target := statement.targets[0], ast.Name)
            ):
                raise self._error(statement, '`%s`%s' % (self._text(statement), STATEMENT))
            self._bind(target, statement.value)
        if isinstance(last, ast.Assign):
            raise self._error(last, '`%s` binds a name: the last statement gives the result' % self._text(last))
        if not isinstance(last, ast.Expr):
            raise self._error(last, '`%s`%s' % (self._text(last), STATEMENT))
        value = self._value(last.value)
        result = self._typed(value, 'float') if isinstance(value, _Literal) else value  # a number alone is a float
        for name, (_, target) in self.bound.items():
            if name not in self.used:
                raise self._error(target, '`%s` is bound but never used' % name)
        return {'type': result.type, 'nodes': self.nodes, 'output': result.node, 'samples': sorted(self.sampled)}

    def _statements(self) -> list[ast.stmt]:
        """The statements, parsed with each `$` and each `#` of a name read as `_`, so that columns stay those of the
        text. A `$` must start a variable's name, and a `#` followed by a letter starts an input value's name. Any
        other `#` starts a comment, left as it is."""
        read = []
        for number, line in enumerate(self.lines, 1):
            code = _code(line)
            for m in re.finditer(r'[$#]', code):  # each `#` here is followed by a letter
                if re.search(r'[\w$.]$', code[: m.start()]) or not re.match(r'[A-Za-z]', code[m.end() :]):
                    said = NO_VALUES if m.group() == '#' and self.defining is not None else SIGILS[m.group()]
                    raise ExpressionError('%s: %s' % (self._place(number, m.end()), said))
            read.append(re.sub(r'[$#]', '_', code) + line[len(code) :])
        try:
            return ast.parse('\n'.join(read)).body
        except SyntaxError as e:
            where = self._place(e.lineno or 1, e.offset or 1)
            raise ExpressionError('%s: %s%s' % (where, e.msg, self._value_before(e, where))) from None

    def _value_before(self, e: SyntaxError, where: str) -> str:
        """What the syntax error `e`, at `where`, adds for the first `#` and a letter on its line before its end, such
        as `#twice` in `f * 2  #twice`, with its place unless it is `where`: a comment written without its space,
        which parses as a name (REVIEW.md SRV-210). '' without one. The node's own input values, read on purpose, are
        passed over, as _refuse_a_leading_value passes them, and so is the line's comment (SRV-213)."""
        number = e.lineno or 1
        line = self.lines[number - 1] if number <= len(self.lines) else ''
        end = len(line) if (e.end_lineno or number) > number else (e.end_offset or e.offset or 1) - 1
        names = VALUE_NAME.finditer(_code(line))
        found = next((m for m in names if m.start() < end and m.group() not in self.inputs), None)
        if found is None:
            return ''
        at = self._place(number, found.start() + 1)
        return "; `%s`%s reads as an input value's name: %s" % (
            found.group(),
            '' if at == where else ', at %s,' % at,
            COMMENT,
        )

    def _refuse_a_leading_value(self, statements: list[ast.stmt]) -> None:
        """Refuses a statement of `statements` that starts with a `#` and a letter naming no input value of the node,
        such as `#done` or `#half-res` (LEADING). Before the others compile, so that no refusal of another line comes
        first (REVIEW.md SRV-210, SRV-215). A binding, `#x = 1`, is one too: _bind refuses only the node's own."""
        for s in statements:
            leading = VALUE_NAME.match(self._text(s))
            if leading and leading.group() not in self.inputs:
                lacking = 'and a function graph has none' if self.defining is not None else 'which the node lacks'
                raise self._error(s, LEADING % (leading.group(), lacking))

    def _bind(self, target: ast.Name, value: ast.expr) -> None:
        name = target.id
        if self._is_variable(target):
            raise self._error(target, "`%s` is Designer's variable: it can't be bound" % self._text(target))
        if self._is_value(target):  # the node's own: one it lacks is refused first (_refuse_a_leading_value)
            raise self._error(target, "`%s` is an input value of the node: it can't be bound" % self._text(target))
        if name in self.bound:
            where = self._where(self.bound[name][1])
            raise self._error(target, '`%s` is bound already, at %s: a name is bound once' % (name, where))
        if name in BOOLS:
            raise self._error(target, '`%s` is a constant: bind another name' % name)
        if name in self.inputs:
            what = 'an input' if self.defining else 'a graph input'
            raise self._error(target, '`%s` is %s: bind another name' % (name, what))
        self.bound[name] = (self._value(value), target)

    def _value(self, node: ast.expr) -> _Value:
        """What `node` gives: a node built, or a number that takes its type where it is used."""
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return self._node('const_bool', {}, node, node.value)
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return _Literal(node.value, node)
        if isinstance(node, ast.Name):
            return self._name(node)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return self._negated(node)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return self._apply('not', {'a': self._value(node.operand)}, node)
        if isinstance(node, ast.BinOp) and type(node.op) in ARITHMETIC:
            return self._arithmetic(ARITHMETIC[type(node.op)], self._value(node.left), self._value(node.right), node)
        if isinstance(node, ast.Compare) and all(type(op) in COMPARISONS for op in node.ops):
            return self._compared(node)
        if isinstance(node, ast.BoolOp):
            definition = 'and' if isinstance(node.op, ast.And) else 'or'
            values = [self._value(v) for v in node.values]
            whole = values[0]
            for v in values[1:]:
                whole = self._apply(definition, {'a': whole, 'b': v}, node)
            return whole
        if isinstance(node, ast.IfExp):
            path, condition, other = self._value(node.body), self._value(node.test), self._value(node.orelse)
            return self._apply('ifelse', {'condition': condition, 'ifpath': path, 'elsepath': other}, node)
        if isinstance(node, ast.Call):
            return self._call(node)
        if isinstance(node, ast.Attribute):
            return self._swizzle(node)
        hint = ''
        if isinstance(node, ast.BinOp) and type(node.op) in HINTS:
            hint = HINTS[type(node.op)] % (self._text(node.left), self._text(node.right))
        raise self._error(node, '`%s` is not part of the grammar%s' % (self._text(node), hint))

    def _name(self, node: ast.Name) -> _Value:
        """A variable, an input value of the node, true or false, a name bound before, or a graph input."""
        if self._is_variable(node):
            name = self._text(node)
            if name in FX_MAP:
                raise self._error(
                    node, "`%s` is an FX-Map's variable, which no function this tool builds can read" % name
                )
            if name not in VARIABLES:
                raise self._error(
                    node, 'unknown variable `%s`; the variables are %s' % (name, ', '.join(sorted(VARIABLES)))
                )
            if name == '$pos' and self.kind in NOT_THE_PIXELS:
                raise self._error(
                    node,
                    "`$pos` isn't the pixel's position in %s: use it in a Pixel Processor's function"
                    % NOT_THE_PIXELS[self.kind],
                )
            return self._get(name, VARIABLES[name], node)
        if self._is_value(node):
            name = self._text(node)
            if self.defining is not None:
                raise self._error(node, NONE_HERE % name)
            if name not in self.inputs:
                values = sorted(i for i in self.inputs if i.startswith('#'))
                listed = (
                    '; its input values are %s' % ', '.join(values)
                    if values
                    else ", nor any other: connect a value into it first (apply_edits' connect to input %r)" % name
                )
                raise self._error(node, 'the node has no input value `%s`%s' % (name, listed))
            return self._input(node, name)
        if node.id in BOOLS:
            return self._node('const_bool', {}, node, BOOLS[node.id])
        if node.id in self.bound:
            self.used.add(node.id)
            return dataclasses.replace(self.bound[node.id][0], at=node)
        if node.id in self.inputs:
            return self._input(node, node.id)
        graph_inputs = sorted(i for i in self.inputs if not i.startswith('#'))
        whose = (
            ('its inputs are', 'it has no inputs')
            if self.defining
            else ('the graph inputs are', 'the graph has no inputs')
        )
        listed = '; %s %s' % (whose[0], ', '.join(graph_inputs)) if graph_inputs else '; ' + whose[1]
        raise self._error(node, 'unknown name `%s`%s' % (node.id, listed))

    def _input(self, node: ast.Name, name: str) -> _Built:
        """The graph input or input value (`#name`) `name` of `inputs`, read with the get_* node of its type."""
        type_ = self.inputs[name]
        if type_ not in READABLE:
            what = 'input value' if name.startswith('#') else 'input' if self.defining else 'graph input'
            raise self._error(node, "%s `%s` has type %s, which a function can't read" % (what, name, type_))
        return self._get(name, type_, node)

    def _get(self, name: str, type_: str, at: ast.expr) -> _Built:
        if name not in self.gets:
            self.gets[name] = self._node(getter_of(type_), {}, at, name)
        return dataclasses.replace(self.gets[name], at=at)

    def _negated(self, node: ast.UnaryOp) -> _Value:
        """`-x`: a number negated, or a neg node of a float to float4. An int is refused, as Designer computes negative
        ints wrongly."""
        v = self._value(node.operand)
        if isinstance(v, _Literal):
            return _Literal(-v.value, node)
        if _kind(v.type) == 'int':
            message = '`%s` makes negative ints%s: write -%s' % (self._text(node), WRONGLY, self._as_float(v))
            raise self._error(node, message)
        self._accepts(v, FLOATS, node)
        return self._apply('neg', {'a': v}, node)

    def _arithmetic(self, definition: str, a: _Value, b: _Value, at: ast.expr) -> _Built:
        """`a` and `b` added, subtracted, multiplied, divided or taken modulo. A float or a number times a float vector
        multiplies it (mulscalar). In + - /, a float with a float vector is made a vector of its own, and a number
        takes the vector's type."""
        pair = _scalar_and_vector(a, b)
        if pair:
            scalar, vector = pair
            if definition == 'mul':
                return self._apply('mulscalar', {'a': vector, 'scalar': scalar}, at)
            if isinstance(scalar, _Built) and definition != 'mod':
                wide = self._broadcast(scalar, _size(vector.type))
                a, b = (wide, b) if scalar is a else (a, wide)
        return self._apply(definition, {'a': a, 'b': b}, at)

    def _compared(self, node: ast.Compare) -> _Built:
        operands = [node.left, *node.comparators]
        if len(node.ops) > 1:
            pairs = [
                '(%s %s %s)' % (self._text(operands[k]), COMPARISONS[type(op)][1], self._text(operands[k + 1]))
                for k, op in enumerate(node.ops)
            ]
            raise self._error(node, '`%s` chains comparisons: write %s' % (self._text(node), ' and '.join(pairs)))
        a, b = self._value(node.left), self._value(node.comparators[0])
        return self._apply(COMPARISONS[type(node.ops[0])][0], {'a': a, 'b': b}, node)

    def _call(self, node: ast.Call) -> _Value:
        if not isinstance(node.func, ast.Name) or self._is_variable(node.func) or self._is_value(node.func):
            raise self._error(node, '`%s` is not part of the grammar' % self._text(node))
        name = node.func.id
        if node.keywords and name not in SAMPLES:
            raise self._error(node, '`%s` names an argument: arguments are given by position' % self._text(node))
        for argument in node.args:
            if isinstance(argument, ast.Starred):
                raise self._error(argument, '`%s` is not part of the grammar' % self._text(argument))
        if name not in FUNCTIONS and (name in self.functions or name == self.defining):
            return self._called(name, node)
        if name not in FUNCTIONS:
            callable_ = sorted(f for f in self.functions if f != self.defining)  # not the one being defined
            package = '; the package has %s' % ', '.join(callable_) if callable_ else ''
            raise self._error(
                node, 'unknown function `%s`; the functions are %s%s' % (name, ', '.join(FUNCTIONS), package)
            )
        count = ARITY.get(name)
        if count is not None and len(node.args) != count:
            raise self._arity(name, node, count)
        if name in SAMPLES:
            return self._sample(name, node)
        args = [self._value(a) for a in node.args]
        if name in NUMBERS:
            return self._vector(name, args, node)
        if name == 'atan2':  # atan2(y, x): Designer's atan2 reads y from its float2's second component
            for v in args:
                if isinstance(v, _Built):
                    self._accepts(v, SCALAR, node)
            y, x = args
            return self._apply('atan2', {'a': self._vector('float2', [x, y], node)}, node)
        if name == 'clamp':
            x, low, high = args
            return self._apply('min', {'a': self._apply('max', {'a': x, 'b': low}, node), 'b': high}, node)
        if name == 'length':
            return self._length(args[0], node)
        if name == 'normalize':
            return self._arithmetic('div', args[0], self._length(args[0], node), node)
        return self._apply(name, dict(zip(DEFINITIONS[name].inputs, args, strict=True)), node)

    def _called(self, name: str, node: ast.Call) -> _Built:
        """A call of the package's function graph `name`: an instance node, fed on each input by the argument in its
        place, of that input's type. Refused when it reaches the function graph being defined, when the graph has no
        output of one type, or when the arguments don't match its inputs."""
        through = self._through(name)
        if through:
            chain = 'calls %s itself' % name if len(through) == 1 else 'calls ' + ', which calls '.join(through)
            others = '' if len(through) == 1 else ', through others either'
            raise self._error(node, "`%s` %s: a function can't call itself%s" % (self._text(node), chain, others))
        resource = self.functions[name]
        if resource.output is None:
            raise self._error(
                node,
                '`%s` calls %s, which has no output node of one type: give it its function with set_function first'
                % (self._text(node), name),
            )
        if len(node.args) != len(resource.inputs):
            raise self._arity(name, node, len(resource.inputs), ', '.join('%s %s' % i for i in resource.inputs.items()))
        samples = self._samples_of(name)
        if samples and not self.images:
            raise self._error(
                node,
                '`%s` calls %s, which samples input image %d, and %s'
                % (self._text(node), name, max(samples), ONLY_PROCESSORS),
            )
        self.sampled |= samples
        built: dict[str, _Built] = {}
        for (input_id, type_), argument in zip(resource.inputs.items(), node.args, strict=True):
            v = self._value(argument)
            if isinstance(v, _Literal):
                v = self._typed(v, type_)
            else:
                self._accepts(v, (type_,), node)
            built[input_id] = v
        return self._added('instance', resource.output, built, node, name)

    def _arity(self, name: str, node: ast.Call, count: int, inputs: str = '') -> ExpressionError:
        """`node`, a call of `name`, given another number of arguments than its `count`; `inputs` are a function
        graph's, which the message lists."""
        takes = 'no arguments' if not count else '%d argument%s' % (count, '' if count == 1 else 's')
        listed = ', then filter= and wrap= by name' if name in SAMPLES else ' (%s)' % inputs if inputs else ''
        return self._error(
            node, '%s takes %s%s, and `%s` gives %d' % (name, takes, listed, self._text(node), len(node.args))
        )

    def _through(self, name: str) -> list[str] | None:
        """The function graphs from `name` to the one being defined, each calling the next: [name] when it is that one;
        None when `name` doesn't reach it. A loop of calls that doesn't reach it ends the search."""
        seen: set[str] = set()

        def path(f: str) -> list[str] | None:
            if f == self.defining:
                return [f]
            if f in seen or f not in self.functions:
                return None
            seen.add(f)
            for callee in self.functions[f].calls:
                rest = path(callee)
                if rest:
                    return [f, *rest]
            return None

        return path(name) if self.defining is not None else None

    def _samples_of(self, name: str) -> set[int]:
        """The input images the function graph `name` samples, through those it calls too, by index."""
        found: set[int] = set()
        seen: set[str] = set()
        waiting = [name]
        while waiting:
            f = waiting.pop()
            if f in seen or f not in self.functions:
                continue
            seen.add(f)
            found.update(self.functions[f].samples)
            waiting.extend(self.functions[f].calls)
        return found

    def _sample(self, name: str, node: ast.Call) -> _Built:
        """sample(index, pos) or sample_lum(index, pos), with filter= and wrap= by name: a samplecol or samplelum node,
        its __constant__ the input image's index and the mode. Refused in a parameter's function, which has no input
        images."""
        if not self.images:
            raise self._error(
                node,
                '`%s` samples an input image, and %s, or a function graph it calls'
                % (self._text(node), ONLY_PROCESSORS),
            )
        chosen: dict[str, int] = {}  # each argument's part of the mode
        for k in node.keywords:
            arg = k.arg or ''
            words = SAMPLE_MODES.get(arg)
            if words is None:
                raise self._error(
                    node,
                    '`%s` names the argument %s: %s takes filter= and wrap= by name'
                    % (self._text(node), k.arg or self._text(k), name),
                )
            value = k.value.value if isinstance(k.value, ast.Constant) else None
            if not isinstance(value, str) or value not in words:
                said = ' or '.join(repr(w) for w in words)
                raise self._error(k, '`%s`: %s is %s, written as such' % (self._text(k), k.arg, said))
            if arg in chosen:  # Python's parser takes one given twice (REVIEW.md SRV-200)
                raise self._error(
                    k, '`%s` gives %s a second time: give filter= and wrap= once each' % (self._text(k), arg)
                )
            chosen[arg] = words[value]
        index, pos = (self._value(a) for a in node.args)
        if isinstance(index, _Built):
            raise self._error(
                index.at,
                '`%s` is %s, where `%s` takes %s%s'
                % (self._text(index.at), with_article(index.type), self._text(node), INDEX, WHOLE),
            )
        if not isinstance(index.value, int) or index.value < 0:
            raise self._error(index.at, '`%s` must be %s here%s' % (self._text(index.at), INDEX, WHOLE))
        if index.value > INT_MAX:
            raise self._error(
                index.at,
                '`%s` is above %d, the largest index Designer holds: a larger one wraps around to a negative index'
                % (self._text(index.at), INT_MAX),
            )
        self.sampled.add(index.value)
        return self._apply(SAMPLES[name], {'pos': pos}, node, (index.value, sum(chosen.values())))

    def _length(self, v: _Value, at: ast.expr) -> _Built:
        return self._apply('sqrt', {'a': self._apply('dot', {'a': v, 'b': v}, at)}, at)

    def _vector(self, name: str, args: list[_Value], at: ast.expr) -> _Built:
        """float() to int4(): a cast of one value of that size, else a vector of components that add up to it."""
        kind, n = _kind(name), _size(name)
        if n == 1:
            [v] = args
            if isinstance(v, _Literal):
                return self._typed(v, name)
            self._accepts(v, ('int', 'float'), at)
            return self._cast(v, name, at)
        if len(args) == 1 and isinstance(v := args[0], _Built) and v.type in NUMBERS and _size(v.type) == n:
            return self._cast(v, name, at)
        for v in args:
            if isinstance(v, _Built) and _kind(v.type) != kind:
                fix = self._hint(v, _sized(kind, _size(v.type)))
                text = self._text(v.at)
                raise self._error(
                    v.at,
                    '`%s` is %s, where `%s` takes %s components%s'
                    % (text, with_article(v.type), self._text(at), kind, fix),
                )
        total = sum(_size(v.type) if isinstance(v, _Built) else 1 for v in args)
        if total != n:
            raise self._error(
                at, '%s takes components that add up to %d, and `%s` gives %d' % (name, n, self._text(at), total)
            )
        if all(isinstance(v, _Literal) for v in args):
            values = tuple(self._number(v, kind) for v in args if isinstance(v, _Literal))
            return self._node(_named('const_', name), {}, at, values)
        return self._joined([self._typed(v, kind) if isinstance(v, _Literal) else v for v in args], at)

    def _cast(self, v: _Built, name: str, at: ast.expr) -> _Built:
        """`v` as a `name` of its size: itself, or a tofloat* or toint* node."""
        return v if v.type == name else self._node(_named('to', name), {'value': v}, at)

    def _swizzle(self, node: ast.Attribute) -> _Built:
        letters = node.attr
        sets = [s for s in ('xyzw', 'rgba') if set(letters) <= set(s)]
        if not sets or len(letters) > 4:
            raise self._error(
                node, '`%s` is not a swizzle: write up to four of x, y, z, w, or of r, g, b, a' % self._text(node)
            )
        indices = tuple(sets[0].index(c) for c in letters)
        v = self._value(node.value)
        if isinstance(v, _Literal) or v.type not in NUMBERS or _size(v.type) == 1:
            what = 'a number' if isinstance(v, _Literal) else with_article(v.type)
            raise self._error(
                node,
                "`%s`: `%s` is %s; a swizzle reads a vector's components" % (self._text(node), self._text(v.at), what),
            )
        if max(indices) >= _size(v.type):
            beyond = letters[indices.index(max(indices))]
            raise self._error(
                node,
                '`%s`: `%s` is %s, which has no %s'
                % (self._text(node), self._text(v.at), with_article(v.type), beyond),
            )
        kind = _kind(v.type)
        definition = _named('iswizzle' if kind == 'int' else 'swizzle', _sized(kind, len(indices)))
        return self._node(definition, {'vector': v}, node, indices[0] if len(indices) == 1 else indices)

    def _apply(
        self, definition: str, args: dict[str, _Value], at: ast.expr, constant: Constant | None = None
    ) -> _Built:
        """A node of `definition` fed by `args` ({input id: value}), holding `constant` if given. Its inputs listing
        several types take one type, as Designer settles them from the first connection (the functions category): the
        type of its values, or a float when all of them are numbers. Each number then takes the type its input needs."""
        d = DEFINITIONS[definition]
        for i, v in args.items():
            if isinstance(v, _Built):
                self._accepts(v, d.inputs[i], at)
        group = [i for i in args if len(d.inputs[i]) > 1]
        typed = [v for i in group if isinstance(v := args[i], _Built)]
        for v in typed[1:]:
            if v.type != typed[0].type:
                raise self._mix(at, typed[0], v)
        shared = typed[0].type if typed else 'float'
        built: dict[str, _Built] = {}
        for i, v in args.items():
            if isinstance(v, _Literal):
                need = shared if i in group else d.inputs[i][0]
                if need not in d.inputs[i]:
                    raise self._error(
                        v.at,
                        '`%s` is a number, where `%s` takes %s'
                        % (self._text(v.at), self._text(at), _listed(d.inputs[i])),
                    )
                v = self._typed(v, need, typed[0] if typed and i in group else None)
            built[i] = v
        return self._node(definition, built, at, constant)

    def _accepts(self, v: _Built, types: tuple[str, ...], at: ast.expr) -> None:
        """Refuses `v` unless its type is one of `types`, the hint a cast or a swizzle (_nearest)."""
        if v.type not in types:
            fix = self._hint(v, _nearest(types, v.type))
            raise self._error(
                v.at,
                '`%s` is %s, where `%s` takes %s%s'
                % (self._text(v.at), with_article(v.type), self._text(at), _listed(types), fix),
            )

    def _mix(self, at: ast.expr, a: _Built, b: _Built) -> ExpressionError:
        """`a` and `b` of two types where one is needed. The hint, whatever their order, converts both to one type: a
        float if either is, the vector's size if the other is a scalar, else the smaller size."""
        hint = ''
        if a.type in NUMBERS and b.type in NUMBERS:
            sizes = (_size(a.type), _size(b.type))
            kind = 'float' if 'float' in (_kind(a.type), _kind(b.type)) else 'int'
            target = _sized(kind, max(sizes) if 1 in sizes else min(sizes))
            fixes = [converted(self._text(v.at), v.type, target) for v in (a, b) if v.type != target]
            hint = ': write ' + ' and '.join(fixes)
        return self._error(
            at,
            '`%s` mixes %s (`%s`) and %s (`%s`)%s'
            % (self._text(at), with_article(a.type), self._text(a.at), with_article(b.type), self._text(b.at), hint),
        )

    def _hint(self, v: _Built, need: str | None) -> str:
        fix = converted(self._text(v.at), v.type, need) if need else ''
        return ': write ' + fix if fix else ''

    def _typed(self, v: _Literal, need: str, like: _Built | None = None) -> _Built:
        """A constant node of `need` holding the number `v`, in each component."""
        value = self._number(v, _kind(need), like)
        return self._node(_named('const_', need), {}, v.at, value if _size(need) == 1 else (value,) * _size(need))

    def _number(self, v: _Literal, kind: str, like: _Built | None = None) -> int | float:
        """`v` as a number of `kind`; `like` is the value it takes its type from, for the message."""
        if kind == 'float':
            return float(v.value)
        if kind == 'int' and isinstance(v.value, int):
            if v.value >= 0:
                return v.value
            fix = 'write ' + self._as_float(like) if like else 'compute it in floats'
            raise self._error(v.at, '`%s` is a negative int%s: %s' % (self._text(v.at), WRONGLY, fix))
        hint = ''
        if kind == 'bool':
            hint = ': write true or false'
        elif kind == 'int' and like:
            hint = ', as `%s` is: write %s' % (self._text(like.at), self._as_float(like))
        elif kind == 'int':
            # a negative whole number is refused in turn, and an infinite one has none
            whole = math.isfinite(v.value) and v.value >= 0
            hint = ': write it without a decimal point, such as `%d`' % v.value if whole else ': compute it in floats'
        raise self._error(v.at, '`%s` must be %s here%s' % (self._text(v.at), with_article(kind), hint))

    def _as_float(self, v: _Built) -> str:
        """The cast that makes the int `v` a float of its size, such as float2(i2)."""
        return converted(self._text(v.at), v.type, _sized('float', _size(v.type)))

    def _broadcast(self, scalar: _Built, n: int) -> _Built:
        """A float2 to float4 of `scalar` in each component, sharing one vector2."""
        pair = self._joined([scalar, scalar], scalar.at)
        return pair if n == 2 else self._joined([pair, scalar] if n == 3 else [pair, pair], scalar.at)

    def _joined(self, parts: list[_Built], at: ast.expr) -> _Built:
        """A vector of `parts`, joined from the left: vector3(vector2(a, b), c)."""
        prefix = 'ivector' if _kind(parts[0].type) == 'int' else 'vector'
        whole = parts[0]
        for part in parts[1:]:
            size = _size(whole.type) + _size(part.type)
            inputs = {'componentsin': whole, 'componentslast': part}
            whole = self._node(_named(prefix, _sized(_kind(whole.type), size)), inputs, at)
        return whole

    def _node(
        self, definition: str, inputs: Mapping[str, _Built], at: ast.expr, constant: Constant | None = None
    ) -> _Built:
        """A node added: its type is its output's, or else that of its inputs listing several types."""
        d = DEFINITIONS[definition]
        type_ = d.output[0] if len(d.output) == 1 else next(v.type for i, v in inputs.items() if len(d.inputs[i]) > 1)
        return self._added(definition, type_, inputs, at, constant)

    def _added(
        self, definition: str, type_: str, inputs: Mapping[str, _Built], at: ast.expr, constant: Constant | None
    ) -> _Built:
        """A node of `definition` and of type `type_` added, fed by `inputs`."""
        self.nodes.append(
            {
                'definition': definition,
                'type': type_,
                'constant': constant,
                'inputs': {i: v.node for i, v in inputs.items()},
            }
        )
        return _Built(type_, len(self.nodes) - 1, at)

    def _is_variable(self, node: ast.Name) -> bool:
        """Whether the user wrote `node` with a `$`, read as `_` by the parser."""
        return self._text(node).startswith('$')

    def _is_value(self, node: ast.Name) -> bool:
        """Whether the user wrote `node` with a `#`, read as `_` by the parser: an input value of the node."""
        return self._text(node).startswith('#')

    def _text(self, node: ast.stmt | ast.expr | ast.keyword) -> str:
        return ast.get_source_segment(self.text, node) or ''

    def _where(self, node: ast.stmt | ast.expr | ast.keyword) -> str:
        line = self.lines[node.lineno - 1]
        return self._place(node.lineno, len(line.encode()[: node.col_offset].decode(errors='replace')) + 1)

    def _place(self, line: int, column: int) -> str:
        """Where line `line`, column `column` of the text read is in the text given, its indent back."""
        column += self.indent
        return 'line %d, column %d' % (line, column) if self.multiline else 'column %d' % column

    def _error(self, node: ast.stmt | ast.expr | ast.keyword, message: str) -> ExpressionError:
        return ExpressionError('%s: %s' % (self._where(node), message))
