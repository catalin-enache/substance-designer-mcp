"""The unit tests that depend on the system run only where it fits (REVIEW.md TST-508): run under
windows_simulation.py, a test that can't run on Windows skips there rather than failing. Every test file that mentions
the system is run so, but NOT_SIMULATED. Under the simulation, a write in mode 'w', 'a' or 'x', without 'b' or '+',
that gives no `newline` ends each line with '\\r\\n', as on Windows. A read-write mode ('+') is left as it is."""

import os
import re
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

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


# writes text through each way the code opens a file, under the simulation (argv: this folder, then the folder to
# write in), then prints what a text-mode read gives back
WRITES = dedent("""
    import os
    import sys
    from pathlib import Path

    sys.path.insert(0, sys.argv[1])
    import windows_simulation

    windows_simulation.pytest_configure(None)
    folder = Path(sys.argv[2])
    (folder / 'write_text').write_text('a\\n', encoding='utf-8')
    for mode in ('w', 'a', 'x', 'w+'):
        with open(folder / mode, mode, encoding='utf-8') as f:
            f.write('a\\n')
    with os.fdopen(os.open(folder / 'fdopen', os.O_WRONLY | os.O_CREAT), 'w', encoding='utf-8') as f:
        f.write('a\\n')
    for name, newline in (('empty', ''), ('lf', '\\n')):
        with open(folder / name, 'w', encoding='utf-8', newline=newline) as f:
            f.write('a\\n')
    with open(folder / 'binary', 'wb') as f:
        f.write(b'a\\n')
    print(repr((folder / 'w').read_text(encoding='utf-8')))
""")


@pytest.mark.skipif(sys.platform == 'win32', reason='simulates Windows on macOS; on Windows the tests run as they are')
def test_the_simulation_writes_text_as_windows_does(tmp_path: Path) -> None:
    # a text-mode write turns each '\n' into '\r\n' on Windows, unless the call gives its own `newline`, and a text-mode
    # read turns them back. The simulation leaves a read-write mode (`+`) as it is (`.claude/rules/unit-tests.md`)
    done = subprocess.run(
        [sys.executable, '-c', WRITES, HERE, str(tmp_path)], capture_output=True, text=True, timeout=LIMIT_S
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout == "'a\\n'\n"
    written = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    assert written == {
        **dict.fromkeys(('write_text', 'w', 'a', 'x', 'fdopen'), b'a\r\n'),
        **dict.fromkeys(('empty', 'lf', 'binary', 'w+'), b'a\n'),
    }
