"""
End-to-end self-test of every substance-designer MCP tool, over a real stdio MCP connection.

    macOS:   mcp_server/venv/bin/python tests/test_all_tools.py
    Windows: mcp_server\\venv\\Scripts\\python tests\\test_all_tools.py

If Designer isn't running, the test starts it (launch_designer) and closes it again at the end
(quit_designer); a Designer that was already running is left open. Everything that changes state happens in a
temporary graph ("mcp_selftest") that is removed at the end; the graph you had open in the
editor is reopened. It triggers Undo/Redo only while the self-test graph is the one in the editor
(Undo acts on the document in focus), checks that exactly its own step was undone, and redoes at
once if not. "designer facts" checks the Designer behaviour AGENTS.md documents.
The 3D screenshot is skipped if no 3D View is visible. Exits with code 1 if any check fails.
"""
import asyncio
import base64
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

BUNDLE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(BUNDLE, 'mcp_server', 'server.py')
TEST_GRAPH = 'mcp_selftest'
PARAMS = StdioServerParameters(command=sys.executable, args=[SERVER])

results = {}
skipped = []


def check(tool, name, ok, detail=''):
    results.setdefault(tool, []).append(ok)
    print('%s  %-22s %s | %s' % ('PASS' if ok else 'FAIL', tool, name, detail.strip()[:150].replace('\n', ' / ')))


def skip(tool, name, why):
    results.setdefault(tool, [])
    skipped.append((tool, name))
    print('SKIP  %-22s %s | %s' % (tool, name, why))


def text(r):
    return '\n'.join(c.text for c in r.content if c.type == 'text')


def is_image(r):
    return bool(r.content) and r.content[0].type == 'image' and not r.is_error


def added_id(t):
    return re.search(r'added (\d+)', t).group(1)


def _mean_png(path):
    from PIL import Image
    import numpy as np
    a = np.array(Image.open(path)).astype(float)
    return float(a.mean() / (65535.0 if a.max() > 255 else 255.0))


def pixel_values(t):
    """'pixel (x,y): R=0.1, G=0.2' lines -> {(x, y): [0.1, 0.2]}"""
    return {(int(x), int(y)): [float(v) for v in re.findall(r'=(-?[\d.]+)', vals)]
            for x, y, vals in re.findall(r'pixel \((\d+),(\d+)\): (.*)', t)}


def clipboard_fingerprint():
    """Hash of the clipboard (never printed). None where we can't read it (non-macOS)."""
    if sys.platform != 'darwin':
        return None
    info = subprocess.run(['osascript', '-e', 'clipboard info'], capture_output=True).stdout
    data = subprocess.run(['pbpaste'], capture_output=True).stdout
    return hashlib.sha256(info + data).hexdigest()


CLEAN = ("import sd\npm=sd.getContext().getSDApplication().getPackageMgr()\nn=0\n"
         "for p in list(pm.getUserPackages()):\n"
         "    if any(r.getIdentifier()=='%s' for r in p.getChildrenResources(False)):\n"
         "        pm.unloadUserPackage(p); n+=1\nprint('removed', n)" % TEST_GRAPH)
# Undo/Redo via Designer's Edit menu, scheduled to run after this call's own undo group closes
UNDO_REDO = ("import sd\nfrom PySide6.QtCore import QTimer\nfrom PySide6.QtWidgets import QApplication, QMenu\n"
             "g=sd.getContext().getSDApplication().getQtForPythonUIMgr().getCurrentGraph()\n"
             "if g is None or g.getIdentifier()!='%s':\n    print('NOT_FOCUSED')\nelse:\n"
             "    acts=[a for w in QApplication.instance().allWidgets() if isinstance(w, QMenu) and w.title()=='&Edit'\n"
             "          for a in w.actions() if a.text()=='%s' and a.isEnabled()]\n"
             "    if acts:\n        QTimer.singleShot(0, acts[0].trigger)\n        print('SCHEDULED')\n"
             "    else:\n        print('NO_ACTION')")
NODE_EXISTS = ("import sd\nfrom PySide6.QtWidgets import QApplication\n"
               "for _ in range(20):\n    QApplication.processEvents()\n"
               "g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() "
               "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\n"
               "print('EXISTS=%%s' %% (g.getNodeFromId('%s') is not None))")
FACTS = ("import sd\nfrom sd.api.apiexception import APIException\nfrom sd.api.sdproperty import SDPropertyCategory\n"
         "g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() "
         "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\n"
         "print('ATOMIC=%%d' %% len(g.getNodeDefinitions()))\n"
         "print('APIEXC_BASE_ONLY=%%s' %% (issubclass(APIException, BaseException) and not issubclass(APIException, Exception)))\n"
         "n=g.getNodeFromId('%s')\nc=n.getPropertyConnections(n.getPropertyFromId('input1', SDPropertyCategory.Input))[0]\n"
         "print('QUERIED_SIDE=%%s' %% (c.getOutputPropertyNode().getIdentifier()=='%s' and "
         "c.getInputPropertyNode().getIdentifier()=='%s' and c.getOutputProperty().getId()=='input1'))")
CURRENT_GRAPH = ("import sd\ng=sd.getContext().getSDApplication().getQtForPythonUIMgr().getCurrentGraph()\n"
                 "print('CURRENT=' + (g.getIdentifier() if g else ''))")


async def cancel_from_second_client():
    await asyncio.sleep(2)
    async with stdio_client(PARAMS) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            return text(await s.call_tool('cancel_designer_job', {}))


async def run(scratch):
    async with stdio_client(PARAMS) as (r, w):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            c = lambda name, args=None: s.call_tool(name, args or {})
            tools = sorted(t.name for t in (await s.list_tools()).tools)
            print('server instructions: %d chars (AGENTS.md: %s); tools: %d\n' % (
                len(init.instructions or ''), (init.instructions or '').startswith('# AGENTS.md'), len(tools)))
            was_running = not (await c('designer_status')).is_error
            t = text(await c('launch_designer', {'wait_s': 240}))
            check('launch_designer', 'already running' if was_running else 'started from closed',
                  ('already running' if was_running else 'Designer started in') in t and 'ERROR' not in t, t)
            user_graph = re.search(r'CURRENT=(.*)', text(await c('execute_designer_code', {'code': CURRENT_GRAPH}))).group(1).strip()
            await c('execute_designer_code', {'code': CLEAN})
            try:
                # --- connection
                t = text(await c('designer_status'))
                check('designer_status', 'idle + version', 'idle' in t and 'Designer ' in t, t.splitlines()[0])
                t = text(await c('cancel_designer_job'))
                check('cancel_designer_job', 'idle', 'running: False' in t, t)
                job = asyncio.create_task(c('execute_designer_code', {
                    'code': 'import time\nwhile True:\n    time.sleep(0.05)', 'timeout_s': 60}))
                cancel_text = await cancel_from_second_client()
                t = text(await job)
                check('cancel_designer_job', 'running job', 'running: True' in cancel_text and 'cancelled by client' in t, cancel_text)

                # --- discovery
                t = text(await c('search_nodes', {'query': 'slope blur'}))
                check('search_nodes', 'library hit', 'slope_blur.sbs/slope_blur_grayscale_2' in t, t.splitlines()[0])
                t = text(await c('search_nodes', {'query': 'levels', 'limit': 2}))
                check('search_nodes', 'atomic ranked first', t.startswith('atomic   levels'), t.splitlines()[0])
                t = text(await c('describe_node', {'definition': 'blend'}))
                check('describe_node', 'atomic enum', 'max=5' in t, '')
                t = text(await c('describe_node', {'definition': 'slope_blur.sbs/slope_blur_grayscale_2'}))
                check('describe_node', 'library', "output connector ids: ['Slope_Blur']" in t, t.splitlines()[0])

                # --- build a temporary graph with the edit tools
                t = text(await c('create_graph', {'name': TEST_GRAPH, 'size_log2': 9}))
                check('create_graph', '512 px', '(512 px)' in t, t)
                G = {'graph': TEST_GRAPH}
                await c('open_graph', {'graph': TEST_GRAPH})   # so you can watch the nodes appear
                t = text(await c('add_node', {'definition': 'noise_clouds_2.sbs/clouds_2', 'params': {'scale': 4}, **G}))
                check('add_node', 'library + param', 'instance:clouds_2' in t and '-> 4' in t, t)
                clouds = added_id(t)
                slope = added_id(text(await c('add_node', {'definition': 'slope_blur.sbs/slope_blur_grayscale_2', **G})))
                t = text(await c('add_node', {'definition': 'levels', **G}))
                check('add_node', 'atomic', 'levels' in t, t.splitlines()[0])
                lv = added_id(t)
                out = added_id(text(await c('add_node', {'definition': 'output', **G})))
                r_ = await c('add_node', {'definition': 'not_a_real_node', **G})
                check('add_node', 'error on unknown type', r_.is_error and 'neither an atomic' in text(r_), '')
                t = text(await c('set_params', {'node_id': slope, 'params': {'Samples': 16, 'Intensity': 8.0}, **G}))
                check('set_params', 'int + float', '-> 16' in t and '-> 8.0' in t, t)
                t = text(await c('set_params', {'node_id': lv, 'params': {'levelinlow': [0.3] * 4}, **G}))
                check('set_params', 'float4', '(0.3, 0.3, 0.3, 0.3)' in t, t)
                t = text(await c('set_params', {'node_id': 'graph', 'params': {'$outputsize': [9, 9]}, **G}))
                check('set_params', 'graph $outputsize', '(9, 9)' in t, t)
                r_ = await c('set_params', {'node_id': lv, 'params': {'levelinlow': [1, 2]}, **G})
                check('set_params', 'error on bad length', r_.is_error and 'expects 4' in text(r_), text(r_))
                for a, b, port in [(clouds, slope, 'Source'), (clouds, slope, 'Effect'),
                                   (slope, lv, 'input1'), (lv, out, 'inputNodeOutput')]:
                    t = text(await c('connect', {'from_node': a, 'to_node': b, 'to_input': port, **G}))
                check('connect', '4 links', 'connected' in t, t)
                r_ = await c('connect', {'from_node': clouds, 'to_node': lv, 'to_input': 'nope', **G})
                check('connect', 'error on bad port', r_.is_error and 'connectors:' in text(r_), text(r_))
                t = text(await c('execute_designer_code', {'code': (
                    "import sd\nfrom sd.api.sdvaluestring import SDValueString\n"
                    "g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() "
                    "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\n"
                    "n=g.getNodeFromId('%s'); n.setAnnotationPropertyValueFromId('identifier', SDValueString.sNew('height'))\n"
                    "print('output named height')") % (TEST_GRAPH, out), 'undo_label': 'self-test: name output'}))
                check('execute_designer_code', 'sd API call', 'output named height' in t, t)
                r_ = await c('execute_designer_code', {'code': 'raise ValueError("boom")'})
                check('execute_designer_code', 'error traceback', 'ValueError: boom' in text(r_), '')
                t = text(await c('execute_designer_code', {'code': 'while True: pass', 'timeout_s': 2}))
                check('execute_designer_code', 'timeout', 'ScriptAborted: timed out' in t, '')
                t = text(await c('execute_designer_code', {'code': (
                    "import sd\nprint('MODIFIED=%%s' %% any(p.isModified() for p in sd.getContext().getSDApplication()"
                    ".getPackageMgr().getUserPackages() if any(r.getIdentifier()=='%s' for r in p.getChildrenResources(False))))"
                    % TEST_GRAPH)}))
                if 'MODIFIED=True' in t:   # otherwise quit_designer could really close Designer
                    r_ = await c('quit_designer')
                    still = not (await c('designer_status')).is_error
                    check('quit_designer', 'refuses with unsaved changes', r_.is_error and 'unsaved changes' in text(r_)
                          and TEST_GRAPH in text(r_) and still, text(r_))
                else:
                    skip('quit_designer', 'refuses with unsaved changes', 'self-test package not reported as modified')
                t = text(await c('move_nodes', {'positions': {clouds: [-600, 0], slope: [-300, 0], lv: [0, 0], out: [300, 0]}, **G}))
                check('move_nodes', '4 moved', t.count('moved') == 4, '')
                await c('open_graph', {'graph': TEST_GRAPH})   # fit the view to the nodes so far
                t = text(await c('describe_graph', {'include_params': True, **G}))
                check('describe_graph', 'links + params', 'Effect<-%s' % clouds in t and 'Samples = 16' in t, t.splitlines()[0])
                r_ = await c('preview_node', {'node_id': slope, **G})
                check('preview_node', 'intermediate node', is_image(r_), '' if is_image(r_) else text(r_))
                t = text(await c('disconnect', {'node_id': slope, 'input_id': 'Effect', **G}))
                check('disconnect', 'one link', 'removed 1' in t, t)
                tmp = added_id(text(await c('add_node', {'definition': 'blur', **G})))
                t = text(await c('delete_nodes', {'node_ids': [tmp], **G}))
                check('delete_nodes', 'one node', 'deleted %s blur' % tmp in t, t)

                # --- bitmaps
                from PIL import Image
                png = os.path.join(scratch, 'selftest_bitmap.png')
                Image.new('RGB', (64, 32), (200, 100, 50)).save(png)
                t = text(await c('import_bitmap', {'path': png, 'position': [-600, 300], **G}))
                check('import_bitmap', 'linked, native size', 'size (6, 5)' in t, t)
                bm = added_id(t)
                t = text(await c('node_stats', {'node_id': bm, 'points': [[0, 0]], **G}))
                check('import_bitmap', 'pixels match file', 'R=0.7843, G=0.3922, B=0.1961' in t, t)
                t = text(await c('apply_edits', {'ops': [{'op': 'bitmap', 'path': png, 'ref': 'img'},
                                                         {'op': 'delete', 'node': 'img'}], **G}))
                check('import_bitmap', 'apply_edits op, link reused', 'reusing bitmap resource' in t, t)
                r_ = await c('compare_to_reference', {'node_id': bm, 'reference_path': png, 'aligned': True, **G})
                t = text(r_)
                check('compare_to_reference', 'same image matches', 'EMD 0.000' in t and 'mean abs diff 0.0000' in t
                      and any(x.type == 'image' for x in r_.content), t)
                darker = os.path.join(scratch, 'selftest_darker.png')
                Image.new('RGB', (128, 64), (100, 50, 25)).save(darker)
                t = text(await c('compare_to_reference', {'node_id': bm, 'reference_path': darker, **G}))
                check('compare_to_reference', 'shift measured', 'R     0.784' in t and 'mean -0.392' in t, t)
                r_ = await c('compare_to_reference', {'node_id': bm, 'reference_path': png, 'region': [100, 100, 120, 120], **G})
                check('compare_to_reference', 'error on empty region', r_.is_error and 'is empty' in text(r_), text(r_))
                r_ = await c('import_bitmap', {'path': os.path.join(scratch, 'missing.png'), **G})
                check('import_bitmap', 'error on missing file', r_.is_error and 'no such file' in text(r_), '')

                # --- pixel statistics
                t = text(await c('node_stats', {'node_id': lv, 'points': [[0, 0]], 'region': [0, 0, 64, 64], **G}))
                check('node_stats', 'stats + region + point', 'min' in t and 'pixel (0,0)' in t and 'region' in t, t.splitlines()[0])
                uni = added_id(text(await c('add_node', {'definition': 'uniform', 'params': {'outputcolor': [0.2, 0.4, 0.6, 0.8]}, **G})))
                t = text(await c('node_stats', {'node_id': uni, 'points': [[1, 1]], **G}))
                check('node_stats', 'exact known colour', 'R=0.2000, G=0.4000, B=0.6000, A=0.8000' in t, t.splitlines()[-1])
                await c('delete_nodes', {'node_ids': [uni], **G})

                # --- parameter sweep, tiling, log
                before = text(await c('describe_graph', {'node_ids': [clouds], 'include_params': True, **G}))
                r_ = await c('sweep_param', {'node_id': clouds, 'param': 'scale', 'values': [1, 4, 16],
                                             'view_node': slope, 'tile_size': 128, **G})
                sweep_text = text(r_)
                images = [x for x in r_.content if x.type == 'image']
                after = text(await c('describe_graph', {'node_ids': [clouds], 'include_params': True, **G}))
                check('sweep_param', '3 values + image', len(images) == 1 and sweep_text.count('scale = ') == 3, sweep_text.splitlines()[0])
                check('sweep_param', 'original restored', 'restored' in sweep_text and before == after, '')
                r_ = await c('sweep_param', {'node_id': lv, 'param': 'nope', 'values': [1], **G})
                check('sweep_param', 'error on bad param', r_.is_error and 'not a parameter' in text(r_), text(r_))
                t = text(await c('check_tiling', {'node_id': clouds, **G}))
                check('check_tiling', 'tileable noise passes both axes', t.count('tiles seamlessly') == 2, t)
                grad = added_id(text(await c('add_node', {'definition': 'gradient_linear_1', **G})))
                t = text(await c('check_tiling', {'node_id': grad, 'axis': 'vertical', **G}))
                check('check_tiling', 'vertical gradient has a seam', 'VISIBLE SEAM' in t, t.splitlines()[-1])
                await c('delete_nodes', {'node_ids': [grad], **G})
                t = text(await c('read_designer_log', {'contains': 'sd_bridge', 'lines': 5}))
                check('read_designer_log', 'finds bridge start', 'listening on' in t, t.splitlines()[0])
                t = text(await c('read_designer_log', {'errors_only': True, 'lines': 3}))
                check('read_designer_log', 'errors_only filter', 'matching line' in t and all(
                    ('[ERROR]' in l or '[WARNING]' in l) for l in t.splitlines()[1:]), t.splitlines()[0])

                # --- batch edits
                t = text(await c('apply_edits', {'ops': [
                    {'op': 'add', 'definition': 'uniform', 'ref': 'u', 'position': [-300, 300],
                     'params': {'colorswitch': False, 'outputcolor': [0.5, 0.5, 0.5, 1]}},
                    {'op': 'add', 'definition': 'blend', 'ref': 'b', 'params': {'blendingmode': 'multiply'}},
                    {'op': 'connect', 'from': 'u', 'to': 'b', 'input': 'source'},
                    {'op': 'connect', 'from': slope, 'to': 'b', 'input': 'destination'},
                    {'op': 'move', 'node': 'b', 'position': [0, 300]},
                    {'op': 'set', 'node': 'b', 'params': {'opacitymult': 0.5}},
                ], **G}))
                check('apply_edits', '6 ops with refs', 'applied 6 op(s)' in t, t.splitlines()[-1])
                batch_blend = re.search(r"'b': '(\d+)'", t).group(1)
                r_ = await c('apply_edits', {'ops': [
                    {'op': 'add', 'definition': 'levels', 'ref': 'x'},
                    {'op': 'connect', 'from': 'x', 'to': batch_blend, 'input': 'nope'},
                ], **G})
                check('apply_edits', 'stops at failing op', r_.is_error and 'op 1 (connect) failed' in text(r_), text(r_))
                t = text(await c('describe_graph', G))
                x_ids = [l.split()[0] for l in t.splitlines() if ' levels ' in l and l.split()[0] != lv]
                await c('delete_nodes', {'node_ids': x_ids + [batch_blend] + [l.split()[0] for l in t.splitlines()
                                         if ' uniform ' in l], **G})

                # --- exposed inputs and graph size
                t = text(await c('set_graph_size', {'size_log2': 9, 'overridable': True, **G}))
                check('set_graph_size', 'overridable 512', 'overridable, default 512 px' in t, t)
                t = text(await c('expose_param', {'node_id': lv, 'param': 'leveloutlow', 'input_id': 'floor',
                                                  'label': 'Floor', 'default': [0.25] * 4, 'min': 0, 'max': 1, **G}))
                check('expose_param', 'float4 with range', "graph input 'floor'" in t, t)
                t = text(await c('expose_param', {'node_id': slope, 'param': 'Samples', **G}))
                check('expose_param', 'int, defaults to current value', "'Samples'" in t and 'default 16' in t, t)
                r_ = await c('expose_param', {'node_id': lv, 'param': 'leveloutlow', 'input_id': 'floor', **G})
                check('expose_param', 'error on duplicate input', r_.is_error and 'already has an input' in text(r_), text(r_))
                t = text(await c('list_graph_inputs', G))
                check('list_graph_inputs', 'inputs + users', "floor (float4)" in t and "label='Floor'" in t
                      and '%s.leveloutlow' % lv in t and 'Samples' in t, t)
                r_ = await c('sweep_param', {'node_id': 'graph', 'param': 'floor', 'values': [[0.1] * 4, [0.9] * 4],
                                             'view_node': lv, 'tile_size': 96, **G})
                means = [float(m) for m in re.findall(r'L [0-9.]+\.\.[0-9.]+ \(mean ([0-9.]+)\)', text(r_))]
                check('sweep_param', 'graph input changes output', len(means) == 2 and means[1] > means[0] + 0.3, text(r_))
                t = text(await c('remove_graph_input', {'input_id': 'Samples', **G}))
                check('remove_graph_input', 'unbinds + keeps value', 'kept value 16' in t and 'removed graph input' in t, t)

                # --- snapshots, diff, layout, frames
                t = text(await c('snapshot_graph', {'label': 'before tweak', **G}))
                check('snapshot_graph', 'saved', 'snapshot of %s saved' % TEST_GRAPH in t, t)
                snap_path = t.split('saved: ', 1)[1].strip()
                t = text(await c('list_snapshots', G))
                check('list_snapshots', 'lists it', snap_path in t, '')
                await c('set_params', {'node_id': lv, 'params': {'levelinhigh': [0.8] * 4}, **G})
                tmp_node = added_id(text(await c('add_node', {'definition': 'blur', **G})))
                t = text(await c('diff_graph', {'against': 'latest', **G}))
                check('diff_graph', 'sees param change + new node', 'levelinhigh' in t and '+ node %s blur' % tmp_node in t, t.splitlines()[0])
                t = text(await c('diff_graph', {'against': 'before tweak', **G}))
                check('diff_graph', 'by label', 'levelinhigh' in t, '')
                await c('delete_nodes', {'node_ids': [tmp_node], **G})
                await c('set_params', {'node_id': lv, 'params': {'levelinhigh': [1.0] * 4}, **G})   # undo the tweak
                t = text(await c('diff_graph', {'against': 'latest', **G}))
                check('diff_graph', 'no differences after reverting', 'No differences' in t or 'Only node positions' in t, t.splitlines()[-1])
                os.remove(snap_path)
                if not os.listdir(os.path.dirname(snap_path)):
                    os.rmdir(os.path.dirname(snap_path))
                t = text(await c('arrange_graph', G))
                check('arrange_graph', 'columns by data flow', 'arranged' in t and 'column' in t, t)
                t = text(await c('describe_graph', G))
                xs = {l.split()[0]: int(re.search(r'@\((-?\d+),', l).group(1)) for l in t.splitlines() if '@(' in l}
                check('arrange_graph', 'upstream left of downstream', xs[clouds] < xs[slope] < xs[lv] < xs[out], str(xs))
                t = text(await c('add_frame', {'node_ids': [clouds, slope], 'title': 'Shape', 'color': [0.2, 0.4, 0.8], **G}))
                check('add_frame', 'frame drawn', "frame 'Shape' around 2 node(s)" in t, t)
                t = text(await c('add_comment', {'text': 'self-test note', 'node_id': lv, **G}))
                check('add_comment', 'attached comment', 'comment added on node' in t, t)
                t = text(await c('describe_graph', G))
                check('describe_graph', 'lists frames + comments', "frames: 'Shape'" in t and 'comments: 1' in t, t.splitlines()[1])
                t = text(await c('describe_node', {'definition': 'bevel'}))
                check('describe_node', 'library slider range', 'range -1.0..1.0' in t, '')

                # --- Designer facts that AGENTS.md relies on (fail if a Designer update changes them)
                F = 'designer facts'
                t = text(await c('describe_node', {'definition': 'blend'}))
                check(F, 'blend mode ids', 'copy=0, add=1, substract=2, multiply=3, addsub=4, max=5, min=6, '
                      'switch=7, divide=8, overlay=9, screen=10, softlight=11' in t, '')
                check(F, '$format ids', '8_bits_per_channel=0, 16_bits_per_channel=1, hdr_low_precision=2, '
                      'hdr_high_precision=3' in t, '')
                for definition, ins, outs in [('bevel', ['input'], ['height', 'normal']),
                                              ('tile_generator', [], ['TileGenerator']),
                                              ('hbao', ['input'], ['output']),
                                              ('curvature_smooth', ['input'], ['height'])]:
                    t = text(await c('describe_node', {'definition': definition}))
                    out_line = re.search(r'output connector ids: (.*)', t)
                    ok = (out_line is not None and all("'%s'" % o in out_line.group(1) for o in outs)
                          and all(re.search(r'^\s+%s\s+CONNECTOR' % i, t, re.M) for i in ins))
                    check(F, '%s connectors' % definition, ok, out_line.group(0) if out_line else t[:150])
                t = text(await c('execute_designer_code', {'code': FACTS % (TEST_GRAPH, lv, lv, slope)}))
                check(F, '29 atomic nodes', 'ATOMIC=29' in t, t)
                check(F, 'APIException is not an Exception', 'APIEXC_BASE_ONLY=True' in t, t)
                check(F, 'connections reported from queried side', 'QUERIED_SIDE=True' in t, t)
                grad = added_id(text(await c('add_node', {'definition': 'gradient_linear_1', 'position': [-600, 600], **G})))
                nrm = added_id(text(await c('add_node', {'definition': 'normal', 'position': [-400, 600],
                                                         'params': {'intensity': 5.0, 'inversedy': True}, **G})))
                await c('connect', {'from_node': grad, 'to_node': nrm, 'to_input': 'input1', **G})
                px = pixel_values(text(await c('node_stats', {'node_id': grad, 'points': [[0, 0], [511, 0], [0, 511], [300, 511]], **G})))
                check(F, 'gradient_linear_1: 1 at top, 0 at bottom', min(px[(0, 0)][0], px[(511, 0)][0]) > 0.99
                      and max(px[(0, 511)][0], px[(300, 511)][0]) < 0.01, str(px))
                # height rises towards the top: OpenGL (Y up) normals lean down there, so green < 0.5
                gl = pixel_values(text(await c('node_stats', {'node_id': nrm, 'points': [[256, 256]], **G})))[(256, 256)]
                await c('set_params', {'node_id': nrm, 'params': {'inversedy': False}, **G})
                dx = pixel_values(text(await c('node_stats', {'node_id': nrm, 'points': [[256, 256]], **G})))[(256, 256)]
                # a full-height ramp is a gentle slope (G about 0.49 vs 0.51); the sign is what matters
                check(F, 'normal inversedy=True is OpenGL', gl[1] < 0.497 and dx[1] > 0.503 and abs(gl[1] + dx[1] - 1) < 0.002,
                      'OpenGL G=%.3f, DirectX G=%.3f' % (gl[1], dx[1]))
                await c('delete_nodes', {'node_ids': [grad, nrm], **G})

                # --- editor + screenshots
                t = text(await c('open_graph', {'graph': TEST_GRAPH, 'node_id': slope}))
                check('open_graph', 'open + focus', 'focused node' in t, t)
                r_ = await c('open_graph', {'graph': 'no_such_graph'})
                check('open_graph', 'error on unknown graph', r_.is_error and 'not found' in text(r_), '')

                # --- one tool call = one undo step (only acts while the self-test graph is in the editor)
                ub = added_id(text(await c('add_node', {'definition': 'blur', 'position': [0, 400], **G})))
                t = text(await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Undo')}))
                if 'SCHEDULED' not in t:
                    skip('add_node', 'one undo step', 'self-test graph not in focus or Undo unavailable (%s)' % t.strip())
                else:
                    gone = 'EXISTS=False' in text(await c('execute_designer_code', {'code': NODE_EXISTS % (TEST_GRAPH, ub)}))
                    if not gone:
                        # Undo hit some other step: put it back at once
                        await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Redo')})
                        await c('execute_designer_code', {'code': NODE_EXISTS % (TEST_GRAPH, ub)})
                    check('add_node', 'one Undo removes the added node', gone, '')
                    if gone:
                        await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Redo')})
                        back = 'EXISTS=True' in text(await c('execute_designer_code', {'code': NODE_EXISTS % (TEST_GRAPH, ub)}))
                        check('add_node', 'Redo restores it', back, '')
                await c('delete_nodes', {'node_ids': [ub], **G})
                for panel in ('window', 'graph', '2d', 'parameters', 'explorer'):
                    r_ = await c('screenshot_designer', {'panel': panel, 'max_size': 700})
                    if not is_image(r_) and 'not visible' in text(r_):
                        skip('screenshot_designer', panel, 'panel not visible in Designer')
                    else:
                        check('screenshot_designer', panel, is_image(r_), '' if is_image(r_) else text(r_))
                before = clipboard_fingerprint()
                r_ = await c('screenshot_designer', {'panel': '3d', 'max_size': 700})
                if not is_image(r_) and 'not visible' in text(r_):
                    skip('screenshot_designer', '3d', 'no 3D View visible in Designer')
                else:
                    same = before is None or clipboard_fingerprint() == before
                    if not same:
                        # the user may have copied something meanwhile: measure again around a second capture
                        before = clipboard_fingerprint()
                        r_ = await c('screenshot_designer', {'panel': '3d', 'max_size': 700})
                        same = clipboard_fingerprint() == before
                    check('screenshot_designer', '3d' + (' + clipboard kept' if before else ''), is_image(r_) and same,
                          '' if is_image(r_) else text(r_))
                r_ = await c('screenshot_designer', {'panel': 'foo'})
                check('screenshot_designer', 'error on bad panel', r_.is_error, '')

                # --- save / export / render
                sbs = os.path.join(scratch, TEST_GRAPH + '.sbs')
                t = text(await c('save_package', {'graph_or_path': TEST_GRAPH, 'save_as': sbs}))
                check('save_package', 'save as', os.path.exists(sbs), t)
                t = text(await c('save_package', {'graph_or_path': TEST_GRAPH}))
                check('save_package', 'save in place', 'saved' in t, t)
                t = text(await c('import_bitmap', {'path': png, 'embed': 'copy', 'name': 'selftest_copy', **G}))
                copied = re.search(r'selftest_copy \(copy\): (.*)', t)
                check('import_bitmap', 'copy into <package>.resources, named', copied is not None and os.path.isfile(copied.group(1))
                      and os.path.dirname(copied.group(1)) == os.path.join(scratch, TEST_GRAPH + '.resources'), t)
                await c('delete_nodes', {'node_ids': [added_id(t)], **G})
                stats_before = text(await c('node_stats', {'node_id': lv, **G}))
                t = text(await c('set_link_display', {'mode': 'portal', 'from_nodes': [clouds], **G}))
                check('set_link_display', 'portals from a node', 'changed to portal' in t and 'reloaded' in t, t.split(';')[0])
                t = text(await c('diff_graph', {'against': 'latest', **G}))
                check('set_link_display', 'diff shows display only', 'shown as portal' in t and '0 added, 0 removed' in t, t.splitlines()[0])
                stats_after = text(await c('node_stats', {'node_id': lv, **G}))
                check('set_link_display', 'output unchanged', stats_after == stats_before, stats_after)
                t = text(await c('set_link_display', {'mode': 'wire', 'from_nodes': [clouds], **G}))
                check('set_link_display', 'back to wires', 'changed to wire' in t, t.split(';')[0])
                t = text(await c('export_outputs', {'graph': TEST_GRAPH, 'output_dir': os.path.join(scratch, 'export')}))
                check('export_outputs', 'from Designer', 'height.png  512x512' in t, t)
                t = text(await c('sbsar_info', {'sbs_path': sbs}))
                check('sbsar_info', 'graph + output', 'pkg://%s' % TEST_GRAPH in t and 'OUTPUT height' in t, t.splitlines()[0])
                render_dir = os.path.join(scratch, 'render')
                t = text(await c('render_sbs', {'sbs_path': sbs, 'output_dir': render_dir, 'outputs': ['height']}))
                check('render_sbs', 'png', 'height.png  512x512' in t, t)
                from PIL import Image
                import numpy as np
                exported = np.array(Image.open(os.path.join(scratch, 'export', 'height.png'))).astype(int)
                rendered = np.array(Image.open(os.path.join(render_dir, 'height.png'))).astype(int)
                # same up to the last 16-bit step (seen: 27 of 262144 pixels off by <= 3/65535)
                worst = np.abs(exported - rendered).max() if exported.shape == rendered.shape else -1
                check('export_outputs', 'matches render_sbs within 16-bit rounding', 0 <= worst <= 8,
                      'max difference %d/65535, %d pixel(s) differ' % (worst, int((exported != rendered).sum())))
                t = text(await c('sbsar_info', {'sbs_path': sbs}))
                check('sbsar_info', 'exposed input + size', 'INPUT floor FLOAT4' in t and 'INPUT $outputsize' in t, '')
                means = []
                for v in (0.1, 0.9):
                    d = os.path.join(scratch, 'floor_%s' % v)
                    t = text(await c('render_sbs', {'sbs_path': sbs, 'output_dir': d, 'size_log2': 7,
                                                    'params': {'floor': [v] * 4}}))
                    means.append(t)
                check('render_sbs', 'size override 128', 'height.png  128x128' in means[0], means[0])
                check('render_sbs', 'exposed param changes output',
                      _mean_png(os.path.join(scratch, 'floor_0.1', 'height.png')) + 0.3
                      < _mean_png(os.path.join(scratch, 'floor_0.9', 'height.png')), '')
                t = text(await c('render_sbs', {'sbs_path': sbs, 'output_dir': render_dir, 'output_format': 'exr',
                                                'params': {'nope': 1}}))
                check('render_sbs', 'exr + unexposed warning', 'height.exr' in t and "input 'nope' is not exposed" in t, t)
                r_ = await c('preview_maps', {'map_dir': render_dir, 'names': ['height'], 'tile_size': 256})
                check('preview_maps', 'side by side', is_image(r_), '')
                r_ = await c('preview_maps', {'map_dir': render_dir, 'names': ['height'], 'crop': [0, 0, 128, 128]})
                check('preview_maps', 'crop', is_image(r_), '')

                # --- script runner
                script = os.path.join(scratch, 'probe_script.py')
                with open(script, 'w') as f:
                    f.write("import sd\nprint('script file', __file__.endswith('probe_script.py'), "
                            "sd.getContext().getSDApplication().getVersion())\n")
                t = text(await c('run_designer_script', {'path': script, 'timeout_s': 30}))
                check('run_designer_script', '__file__ + sd', 'script file True' in t, t)
            finally:
                print('\ncleanup:', text(await c('execute_designer_code', {'code': CLEAN})).strip())
                shutil.rmtree(os.path.join(os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(
                    os.path.expanduser('~'), '.sd_mcp', 'snapshots'), TEST_GRAPH), ignore_errors=True)
                if user_graph and user_graph != TEST_GRAPH:
                    await c('open_graph', {'graph': user_graph})
                    print('reopened your graph:', user_graph)
                if was_running:
                    skip('quit_designer', 'closes Designer', 'Designer was already running, so it is left open')
                else:
                    # our own instance: nothing of the user's can be lost
                    t = text(await c('quit_designer', {'discard_unsaved': True}))
                    gone = (await c('designer_status')).is_error
                    check('quit_designer', 'closes the Designer it started', 'Designer quit after' in t and gone, t)
    return tools


def main():
    scratch = tempfile.mkdtemp(prefix='sd_mcp_selftest_')
    try:
        tools = asyncio.run(run(scratch))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    missing = sorted(set(tools) - set(results))
    failed = sorted(k for k, v in results.items() if not all(v))
    passed = sum(sum(v) for v in results.values())
    total = sum(len(v) for v in results.values())
    print('\n%d/%d tools covered%s' % (len(set(tools) & set(results)), len(tools),
                                      ('; NOT covered: %s' % missing) if missing else ''))
    print('checks passed: %d/%d; skipped: %d; tools with failures: %s' % (
        passed, total, len(skipped), ', '.join(failed) or 'none'))
    sys.exit(1 if failed or missing else 0)


if __name__ == '__main__':
    main()
