"""``sentinel-proof-mcp`` is now ``citebound-mcp``. This package forwards to it.

The server, its one tool and its arguments are unchanged; only the package and
command names are different. An MCP client configured with ``sentinel-proof-mcp``
keeps working, and ``uvx citebound-mcp`` is what new configurations should use.
"""

from __future__ import annotations

import warnings as _warnings

from citebound_mcp import __version__ as _citebound_mcp_version
from citebound_mcp.server import build_server  # noqa: F401

__version__ = "0.1.3"

#: The version of ``citebound-mcp`` actually serving requests.
CITEBOUND_MCP_VERSION = _citebound_mcp_version

_warnings.warn(
    "sentinel-proof-mcp has been renamed to citebound-mcp and this shim is its "
    "final release. Point your MCP client at `uvx citebound-mcp` instead. "
    "https://github.com/92kareeem/citebound",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["CITEBOUND_MCP_VERSION", "__version__", "build_server"]
