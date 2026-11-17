"""The unit tests that depend on the system run only where it fits (REVIEW.md TST-508): run under
windows_simulation.py, a test that can't run on Windows skips there rather than failing. Every test file that mentions
the system is run so, but NOT_SIMULATED."""

import os
import re
import subprocess
import sys

import pytest
from windows_simulation import NAMES, POSIX_ONLY

from conftest import ROOT

HERE = os.path.dirname(os.path.abspath(__file__))
LIMIT_S = 300  # a limit for the run, not the time it takes (about 12 s)
# the files that mention the system but aren't run under the simulation: ruff's and mypy's, which check the code's text,
# this one, and the plugin's, whose binding takes SO_EXCLUSIVEADDRUSE, which macOS lacks and Windows has
NOT_SIMULATED = {'test_lint.py', 'test_types.py', 'test_windows_simulation.py', 'test_plugin.py'}
# what fails in the simulation for reasons of its own: a run on Windows hasn't measured these (ROADMAP item 18)
SIMULATION_ONLY = {
    # macOS's socket module lacks SO_EXCLUSIVEADDRUSE, which Windows has and the plugin binds with
    'test_lifecycle_env.py::test_launch_refuses_a_port_another_program_holds',
    'test_lifecycle_env.py::test_a_restart_during_the_wait_refuses_a_port_another_program_holds',
    'test_lifecycle_env.py::test_the_refusal_of_a_held_port_says_why_and_how_to_find_the_holder',
    'test_lifecycle_env.py::test_a_port_that_cant_be_bound_for_another_reason_isnt_blamed_on_a_program',
    # it imports the server in a process of its own, which runs on the real system
    'test_lifecycle_env.py::test_environment_overrides',
}


# a mention of the system, or of a name windows_simulation.py takes away (REVIEW.md TST-509)
MENTIONS = re.compile(
    r'sys\.platform|\b(?:import|from) (?:%s)\b|\b(?:%s)\b'
    % ('|'.join(POSIX_ONLY), '|'.join(name for names in NAMES.values() for name in names))
)


def _system_files() -> list[str]:
    """The unit test files that mention the system or a name the simulation takes away (MENTIONS), but
    NOT_SIMULATED."""
    found = []
    for name in sorted(os.listdir(HERE)):
        if name.startswith('test_') and name.endswith('.py') and name not in NOT_SIMULATED:
            with open(os.path.join(HERE, name), encoding='utf-8') as f:
                if MENTIONS.search(f.read()):
                    found.append(name)
    return found


@pytest.mark.skipif(sys.platform == 'win32', reason='simulates Windows on macOS; on Windows the tests run as they are')
def test_the_tests_that_depend_on_the_system_skip_on_windows() -> None:
    files = _system_files()
    assert {'test_lifecycle_env.py', 'test_install.py', 'test_view3d_helpers.py'} <= set(files), files
    done = subprocess.run(
        [sys.executable, '-m', 'pytest', '-p', 'windows_simulation', '-p', 'no:cacheprovider', '-v', '--tb=no', '-rfE']
        + [os.path.join(HERE, name) for name in files],
        cwd=ROOT,
        env=dict(os.environ, PYTHONPATH=HERE),
        capture_output=True,
        text=True,
        timeout=LIMIT_S,
    )
    # a test that fails or errs, or a file that can't be collected (named alone)
    failed: set[str] = set(re.findall(r'^(?:FAILED|ERROR) tests/unit/(test_\w+\.py(?:::\w+)?)', done.stdout, re.M))
    assert failed == SIMULATION_ONLY, done.stdout[-3000:] + done.stderr[-2000:]
    # a case that sets Windows runs there: a mark on its whole test skipped it (REVIEW.md TST-510)
    skipped = re.findall(r'^tests/unit/(test_\w+\.py::\w+\[[^]]*\bwin32\b[^]]*\]) SKIPPED', done.stdout, re.M)
    assert not skipped, skipped
