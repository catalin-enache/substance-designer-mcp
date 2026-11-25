"""Runs inside Designer: the steps the toolbar's Undo dropdown lists, newest first, as the rollback of a failed call reads
them (mcp_server/designer_rollback.py, imported as it is now). Reading makes no step. Prints STEPS=<their names, as
JSON>."""

import json
import os
import sys

MCP_SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), *['..'] * 4, 'mcp_server')

# The file as it is now, not as a run before had it. What sys.modules held under its name is put back after.
found = sys.modules.pop('designer_rollback', None)
sys.path.insert(0, MCP_SERVER)
try:
    import designer_rollback
finally:
    sys.path.remove(MCP_SERVER)
    if found is None:
        sys.modules.pop('designer_rollback', None)
    else:
        sys.modules['designer_rollback'] = found

history = designer_rollback.history()
if history is None:
    raise RuntimeError("no Undo and Redo dropdowns of Designer's history found")
print('STEPS=' + json.dumps([action.text() for action in history.undo.actions()]))
