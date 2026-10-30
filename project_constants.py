"""The bridge plugin's name, in one place for everything that runs from this repo: the MCP
server, the CLI client, the installer and the tests.

The plugin itself (running inside Designer from its installed copy) can't import this file; it
takes its name from its own folder. So renaming the plugin means: change PLUGIN here and rename
both plugin/<PLUGIN>/ folders to match. tests/unit/test_constants.py checks that the folders
match, that no other code spells the name out, and that README.md and AGENTS.md mention it.
"""
import os

PLUGIN = 'sd_claude_bridge_kve'

ROOT = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.join(ROOT, 'plugin', PLUGIN)        # what install.py copies (holds pluginInfo.json)
PLUGIN_PACKAGE_DIR = os.path.join(PLUGIN_DIR, PLUGIN)    # the Python package Designer imports
TOKEN_FILE = os.path.join(os.path.expanduser('~'), '.%s_token' % PLUGIN)   # the plugin's secret
# Seconds the plugin keeps a queued job before dropping it (its own QUEUE_WAIT, which it can't
# import from here; tests/unit/test_queue_wait.py checks they match). A client waits at least
# this long plus the script's time, so a job it gave up on can't start later.
QUEUE_WAIT = 900
