"""The old ``sentinel-proof`` command, forwarding to ``citebound``."""

from __future__ import annotations

import sys

from citebound.cli import main as _main


def main(argv: list[str] | None = None) -> int:
    print(
        "note: `sentinel-proof` is now `citebound`. This command still works, "
        "but it is the final release under the old name. "
        "Install citebound and use `citebound` instead.",
        file=sys.stderr,
    )
    return _main(argv)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
