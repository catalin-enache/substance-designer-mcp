"""Runs inside Designer, sent by sd_run outside any undo group: one Redo, sent and waited for by the rollback's own
undo_steps (mcp_server/designer_rollback.py, imported as it is now), on Designer's history the other way round. To
undo_steps, the Redo dropdown is the Undo one, the Undo dropdown the Redo one, and the history manager's redo() slot its
undo() one. So it redoes the Redo dropdown's top step only while that step is on top, and waits until the step tops the
Undo dropdown. It redoes only a step named as an apply_edits call of one edit names its step: that label, then the
tag's prefix. Otherwise it raises, naming the Redo dropdown's top step, and redoes nothing. It raises too when the
Redo wasn't seen landing, with undo_steps' state, which speaks of an undo. Prints REDONE=<the step's name, as JSON>."""

import json
import os
import sys

LABEL = 'Claude: apply 1 edits'  # the label of an apply_edits call of one edit (server_tools/edits.py)
LIMIT_S = 60  # s at most for the Redo to land, a safety net, as the rollback's limit
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), *['..'] * 4)
MCP_SERVER = os.path.join(ROOT, 'mcp_server')

# The files as they are now, not as a run before had them. What sys.modules held under their names is put back after.
found = {name: sys.modules.pop(name, None) for name in ('designer_rollback', 'project_constants')}
sys.path.insert(0, MCP_SERVER)
sys.path.insert(0, ROOT)
try:
    import designer_rollback

    from project_constants import TAG_PREFIX
finally:
    sys.path.remove(ROOT)
    sys.path.remove(MCP_SERVER)
    for name, module in found.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module

history = designer_rollback.history()
if history is None:
    raise RuntimeError("no Undo and Redo dropdowns of Designer's history found")
step = designer_rollback._top(history.redo)
if step is None or not step.startswith(LABEL + TAG_PREFIX):  # a redo only of a step of the check's own
    raise RuntimeError("the Redo dropdown's top step is %r, not an apply_edits call's" % step)
undo, redo = history.held
meta = history.manager.metaObject()
back = designer_rollback.History(redo, undo, history.manager, meta.method(meta.indexOfMethod('redo()')))
_, state = designer_rollback.undo_steps(back, [step], LIMIT_S)
# Drops the toolbar's button and action wrappers, before this job's scope goes (history_facts.py)
del history, back, undo, redo
if state != 'undone':
    raise RuntimeError('the Redo of %r: %s' % (step, state))
print('REDONE=' + json.dumps(step))
