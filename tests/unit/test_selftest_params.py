"""The params category's checks of a Gradient Map's keys (tests/test_all_tools/params/checks.py), on a fake Designer:
what they leave behind when a check fails, which a passing self-test doesn't show."""

import asyncio
from types import ModuleType, SimpleNamespace

import pytest
from selftest_fakes import fresh, tool_result

from project_constants import ToolArgs


@pytest.fixture
def params() -> ModuleType:
    return fresh('params.checks')


@pytest.mark.parametrize('taken', [True, False], ids=['taken', 'refused'])
def test_an_expose_taken_has_its_input_removed(params: ModuleType, taken: bool) -> None:
    # REVIEW.md TST-766: an expose a regression took left its input driving gradientrgba for the checks after it
    calls: list[str] = []

    async def c(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        calls.append(name)
        if name == 'apply_edits':
            return tool_result(
                'exposed 5.gradientrgba as graph input' if taken else 'cannot be exposed', error=not taken
            )
        return tool_result(
            'gradientrgba (int) = 0  drives: 5.gradientrgba' if taken and name == 'list_graph_inputs' else ''
        )

    ctx = SimpleNamespace(c=c, G={'graph': 'mcp_selftest'}, gradient='5')
    asyncio.run(params.check_expose_refuses_gradient_keys(ctx))
    assert ('remove_graph_input' in calls) is taken, calls
