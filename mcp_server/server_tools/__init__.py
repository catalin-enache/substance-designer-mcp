"""The MCP server's code, one module per area; importing this package registers every tool on
core.server. server.py (the entry point) re-exports the names these modules define."""

from . import (
    compare,
    core,
    discovery,
    edits,
    guide,
    layout,
    lifecycle,
    log,
    measure,
    output,
    scripting,
    snapshots,
    views,
)

MODULES = (core, guide, lifecycle, scripting, discovery, views, edits, measure, compare, log, snapshots, layout, output)
