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
