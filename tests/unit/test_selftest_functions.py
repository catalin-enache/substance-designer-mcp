"""The functions category's helpers (tests/test_all_tools/functions/results.py), and what its sampling checks do with
the answers they get (checks.py), without Designer."""

import asyncio
from types import SimpleNamespace

import pytest
from selftest_fakes import FakeCall, fresh, tool_result

from function_compiler import ExpressionError
from project_constants import ToolArgs


def test_a_pixel_compare_with_nothing_wanted_fails() -> None:
    # REVIEW.md TST-722: a baseline node_stats that failed reads as no pixels, and every compare with it passed
    results = fresh('functions.results')
    assert not results.all_near({(0, 0): [0.5]}, {})
    assert not results.all_near({}, {(0, 0): [0.5]})
    assert results.all_near({(0, 0): [0.5, 1.0]}, {(0, 0): [0.502, 1.0]})


# a note as long as set_function's, which a build line before it would push past check()'s 150 characters
NOTE = 'a note the check does not expect, ' + 'as long as a real one, ' * 3 + 'and no longer'
# a set_function result whose build line is longer than check()'s 150 characters, its note wrong
WRONG = '7.perpixel: built 9 function nodes, its output a float4' + ' ' * 120 + '\n' + NOTE


def _designer(edits: list[list[ToolArgs]] | None = None, refuse_first: bool = False) -> FakeCall:
    """The answers of the sampling checks: apply_edits adds each node under its ref (the first call refused if
    `refuse_first`); set_function gives the build line and colour line a node's expression gets, else WRONG's, then
    NOTE; the ops of each apply_edits call kept in `edits`."""
    results = fresh('functions.results')
    ids = iter(range(100, 200))
    kept: list[list[ToolArgs]] = [] if edits is None else edits

    async def c(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        args = args or {}
        if name == 'apply_edits':
            ops = args['ops']
            assert isinstance(ops, list)
            kept.append(ops)
            if refuse_first and len(kept) == 1:
                return tool_result('op 0 (add) failed', True)
            return tool_result(''.join("  ref '%s' = %d\n" % (op['ref'], next(ids)) for op in ops if 'ref' in op))
        if name == 'set_function':
            try:
                head = results.built(str(args['node_id']), str(args['expression']), images=True)
            except (KeyError, ExpressionError):  # a function graph's, or a call of one the fake doesn't know
                return tool_result(WRONG)
            return tool_result('%s\ncolorswitch is on: the float4 is the colour.\n%s' % (head, NOTE))
        return tool_result('ok')

    return c


# each check, and how many of its checks compare the notes after the build line
CHECKS = {'check_set_function_samples_two_inputs': 4, 'check_set_function_samples_an_input_with_nothing_connected': 2}


@pytest.mark.parametrize('name', list(CHECKS))
def test_a_sampling_check_deletes_its_second_sampler_when_the_first_is_refused(name: str) -> None:
    # REVIEW.md TST-746: the first sampler's ids read before the try left the second's nodes in the graph
    checks = fresh('functions.checks')
    edits: list[list[ToolArgs]] = []
    ctx = SimpleNamespace(c=_designer(edits, refuse_first=True), G={'graph': 'g'}, img='1', nm='2')
    with pytest.raises(KeyError):
        asyncio.run(getattr(checks, name)(ctx))
    deleted = [str(op['node']) for ops in edits for op in ops if op.get('op') == 'delete']
    assert sorted(deleted) == ['100', '101'], edits  # the second sampler's Pixel Processor and output


@pytest.mark.parametrize(('name', 'compared'), CHECKS.items())
def test_a_sampling_checks_failure_shows_the_notes_it_compares(
    name: str, compared: int, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-747: check() prints a detail's first 150 characters, and these checks compare the result's end
    checks = fresh('functions.checks')
    asyncio.run(getattr(checks, name)(SimpleNamespace(c=_designer(), G={'graph': 'g'}, img='1', nm='2')))
    lines = capsys.readouterr().out.splitlines()
    assert sum(line.startswith('FAIL') and line.endswith(NOTE) for line in lines) == compared, lines
