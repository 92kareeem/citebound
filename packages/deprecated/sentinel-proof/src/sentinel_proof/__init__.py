"""``sentinel-proof`` is now ``citebound``. This package forwards to it.

The name changed because "Sentinel" collides with Microsoft Sentinel and
HashiCorp Sentinel, so the project could never be found by the people who
needed it. Nothing else changed: same API, same Apache-2.0 licence, same
author. ``citebound`` says what the library actually enforces, which is that
every claim is bound to the passage it cites.

Nothing here is reimplemented. Every name below is re-exported from
``citebound``, so a pinned ``sentinel-proof`` keeps behaving exactly as the
installed ``citebound`` does.

    pip uninstall sentinel-proof && pip install citebound

Then change ``sentinel_proof`` to ``citebound`` in your imports; the names
after it are unchanged. This shim receives no further releases.
"""

from __future__ import annotations

import warnings as _warnings

from citebound import (  # noqa: F401
    HASH_RECIPE,
    MAX_STRIPPED_RATIO,
    MIN_LEXICAL_OVERLAP,
    REFUSAL_SENTINEL,
    CitationStyle,
    Claim,
    ClaimStatus,
    Passage,
    RefusalReason,
    Verdict,
    check_provenance,
    document_sha256,
    from_langchain,
    from_llamaindex,
    is_refusal,
    normalize_citations,
    passages_from_texts,
    provenance_hash,
    refusal_text,
    strip_citations,
    verify,
)
from citebound import __version__ as _citebound_version

# The shim's own version, not the library's: `citebound.__version__` is what
# tells you which implementation is actually answering.
__version__ = "0.1.3"

#: The version of ``citebound`` doing the work behind this shim.
CITEBOUND_VERSION = _citebound_version

_warnings.warn(
    "sentinel-proof has been renamed to citebound and this shim is its final "
    "release. Run `pip install citebound` and import `citebound` instead of "
    "`sentinel_proof`; the API is unchanged. "
    "https://github.com/92kareeem/citebound",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "CITEBOUND_VERSION",
    "HASH_RECIPE",
    "MAX_STRIPPED_RATIO",
    "MIN_LEXICAL_OVERLAP",
    "REFUSAL_SENTINEL",
    "CitationStyle",
    "Claim",
    "ClaimStatus",
    "Passage",
    "RefusalReason",
    "Verdict",
    "__version__",
    "check_provenance",
    "document_sha256",
    "from_langchain",
    "from_llamaindex",
    "is_refusal",
    "normalize_citations",
    "passages_from_texts",
    "provenance_hash",
    "refusal_text",
    "strip_citations",
    "verify",
]
