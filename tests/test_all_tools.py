"""
End-to-end self-test of every substance-designer MCP tool, over a real stdio MCP connection.

    macOS:   mcp_server/venv/bin/python tests/test_all_tools.py
    Windows: mcp_server\\venv\\Scripts\\python tests\\test_all_tools.py

Needs Designer running with the sd_bridge plugin. Everything that changes state happens in a
temporary graph ("mcp_selftest") that is removed at the end; the graph you had open in the
editor is reopened. It never triggers Undo (that would act on the document in focus).
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
            t = text(await c('launch_designer', {'wait_s': 240}))
            check('launch_designer', 'running / started', 'sd_bridge' in t, t)
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
                t = text(await c('move_nodes', {'positions': {clouds: [-600, 0], slope: [-300, 0], lv: [0, 0], out: [300, 0]}, **G}))
                check('move_nodes', '4 moved', t.count('moved') == 4, '')
                t = text(await c('describe_graph', {'include_params': True, **G}))
                check('describe_graph', 'links + params', 'Effect<-%s' % clouds in t and 'Samples = 16' in t, t.splitlines()[0])
                r_ = await c('preview_node', {'node_id': slope, **G})
                check('preview_node', 'intermediate node', is_image(r_), '' if is_image(r_) else text(r_))
                t = text(await c('disconnect', {'node_id': slope, 'input_id': 'Effect', **G}))
                check('disconnect', 'one link', 'removed 1' in t, t)
                tmp = added_id(text(await c('add_node', {'definition': 'blur', **G})))
                t = text(await c('delete_nodes', {'node_ids': [tmp], **G}))
                check('delete_nodes', 'one node', 'deleted %s blur' % tmp in t, t)

                # --- editor + screenshots
                t = text(await c('open_graph', {'graph': TEST_GRAPH, 'node_id': slope}))
                check('open_graph', 'open + focus', 'focused node' in t, t)
                r_ = await c('open_graph', {'graph': 'no_such_graph'})
                check('open_graph', 'error on unknown graph', r_.is_error and 'not found' in text(r_), '')
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
                t = text(await c('export_outputs', {'graph': TEST_GRAPH, 'output_dir': os.path.join(scratch, 'export')}))
                check('export_outputs', 'from Designer', 'height.png  512x512' in t, t)
                t = text(await c('sbsar_info', {'sbs_path': sbs}))
                check('sbsar_info', 'graph + output', 'pkg://%s' % TEST_GRAPH in t and 'OUTPUT height' in t, t.splitlines()[0])
                render_dir = os.path.join(scratch, 'render')
                t = text(await c('render_sbs', {'sbs_path': sbs, 'output_dir': render_dir, 'outputs': ['height']}))
                check('render_sbs', 'png', 'height.png  512x512' in t, t)
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
                if user_graph and user_graph != TEST_GRAPH:
                    await c('open_graph', {'graph': user_graph})
                    print('reopened your graph:', user_graph)
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
