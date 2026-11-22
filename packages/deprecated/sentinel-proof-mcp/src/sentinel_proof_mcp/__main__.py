"""The old ``sentinel-proof-mcp`` command, forwarding to ``citebound-mcp``.

The notice goes to stderr on purpose. An MCP client talks to this process over
stdout, so anything printed there would corrupt the protocol stream.
"""

from __future__ import annotations

import sys

from citebound_mcp.__main__ import main as _main


def main(argv: list[str] | None = None) -> int:
    print(
        "note: sentinel-proof-mcp is now citebound-mcp. This command still "
        "works, but it is the final release under the old name. Update your "
        "MCP client config to `uvx citebound-mcp`.",
        file=sys.stderr,
    )
    return _main(argv)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
