"""The MCP server's code, one module per area; importing this package registers every tool on
core.server. server.py (the entry point) re-exports the names these modules define."""

from . import (
    compare,
    core,
    discovery,
    edits,
    functions,
    guide,
    image_reading,
    layout,
    lifecycle,
    log,
    measure,
    output,
    reference,
    scripting,
    snapshots,
    views,
)

MODULES = (
    core,
    guide,
    lifecycle,
    scripting,
    discovery,
    views,
    edits,
    functions,
    measure,
    image_reading,
    compare,
    reference,
    log,
    snapshots,
    layout,
    output,
)
