"""Runs inside Designer, sent by run_designer_script: a call that fails after a change, with a second client acting while
its rollback runs (mcp_server/designer_rollback.py, run by the code the tool sends around this one). It adds a node to
the self-test graph, then hands Qt a function to run at the next event processed, and raises. The rollback's wait for
the undo processes the next events, so the function runs inside it, while the job still runs. With ARGS['what']:

- 'cancel': the function sends cancel_designer_job's request from a second client (client/sd_run.py --cancel), and
  waits for its answer;
- 'queue': the function waits until the bridge's status says a second client's job is queued (the check sends it once
  this job runs), looked at every 0.1 s, 30 s at most.

The function prints UNTRACED=<True: it ran without the plugin's tracer, as the rollback runs>, then CANCEL=<the
cancel's answer> or STATUS=<the bridge's status, last read>. Run after the job ended (a rollback that processed no
event), it does nothing: the job's output is no longer sys.stdout, and a cancel then would land in a later job."""

import os
import subprocess
import sys
import time
from typing import Literal, TypedDict, cast

import sd
from PySide6.QtCore import QTimer
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdpackagemgr import SDPackageMgr

GRAPH = 'mcp_selftest'  # common.TEST_GRAPH
LIMIT_S = 30  # s at most for the second client's job to be queued
POLL_S = 0.1  # s between looks at the bridge's status: nothing says a job was queued (common.POLL_S)


class Args(TypedDict):
    what: Literal['cancel', 'queue']
    client: list[str]  # the command running client/sd_run.py: a Python, then the script


ARGS: Args = globals()['ARGS']
JOB_OUTPUT = sys.stdout  # the plugin's, while the job runs
# Designer's own Python settings aren't for the client's Python; its bridge port is the client's too (SD_BRIDGE_PORT)
ENV = {key: value for key, value in os.environ.items() if not key.startswith('PYTHON')}
# On Windows, the second client starts with no console window of its own: Microsoft's CREATE_NO_WINDOW, for a console
# application started by a GUI one (Designer)
NO_WINDOW: int = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if sys.platform == 'win32' else 0


def client(*args: str) -> str:
    """The second client's answer to `args`."""
    return subprocess.run(
        [*ARGS['client'], *args], capture_output=True, text=True, timeout=60, env=ENV, creationflags=NO_WINDOW
    ).stdout.strip()


def during_the_rollback() -> None:
    if sys.stdout is not JOB_OUTPUT:
        return
    print('UNTRACED=%s' % (sys.gettrace() is None))
    if ARGS['what'] == 'cancel':
        print('CANCEL=' + client('--cancel'))
        return
    deadline = time.monotonic() + LIMIT_S
    status = client('--status')
    while '1 queued' not in status and time.monotonic() < deadline:
        time.sleep(POLL_S)
        status = client('--status')
    print('STATUS=' + status)


pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == GRAPH),
)
g.newNode('sbs::compositing::uniform')
QTimer.singleShot(0, during_the_rollback)
raise RuntimeError('the script failed')
