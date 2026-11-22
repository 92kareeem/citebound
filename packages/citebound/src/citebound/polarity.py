"""Conservative English operator checks, not a semantic entailment model.

Compare operators only in sentences with identical normalized content anchors.
An unrelated prohibition elsewhere in a chunk must not invalidate a faithful
claim. Missing modal or ordering words can be a harmless summary; explicit
opposing operators cannot.
Quantifier weakening is deliberately allowed: completeness is a separate task.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .passages import Passage

_SENTENCES = re.compile(r"(?<=[.!?])\s+|[\n;]+")
_WORDS = re.compile(r"[a-z]{2,}|\d[\d,]*(?:\.\d+)?")
_FILLER = frozenset(
    [
        "the",
        "an",
        "and",
        "are",
        "is",
        "was",
        "were",
        "be",
        "been",
        "being",
        "do",
        "does",
        "did",
        "has",
        "have",
        "had",
        "to",
        "of",
        "for",
        "in",
        "on",
        "at",
        "by",
        "with",
        "it",
        "its",
        "that",
        "this",
        "they",
        "their",
        "can",
    ]
)
# Long phrases first so 'no more than' is a ceiling, not a negation.
_OPERATORS = (
    ("comparison", "upper", r"no more than|at most|less than|below|lower than"),
    ("comparison", "lower", r"no fewer than|at least|more than|above|higher than"),
    ("negation", "negative", r"not|never|no|neither|nor"),
    ("modality", "required", r"must|shall|required to|requires?|mandatory"),
    ("modality", "optional", r"may|can|optional"),
    ("modality", "recommended", r"should|recommended"),
    ("quantifier", "universal", r"all|every|each|always"),
    ("quantifier", "partial", r"some|sometimes"),
    ("time", "before", r"prior to|before"),
    ("time", "after", r"following|after"),
)
_PATTERNS = tuple(
    (kind, value, re.compile(rf"\b(?:{pattern})\b")) for kind, value, pattern in _OPERATORS
)
_CONTRACTIONS = re.compile(r"\b(?:cannot|can't|won't|shan't)\b|\b(\w+)n't\b")


@dataclass(frozen=True)
class Statement:
    anchors: frozenset[str]
    operators: dict[str, frozenset[str]]


def statement(text: str) -> Statement:
    text = text.lower().replace("\u2019", "'")
    text = _CONTRACTIONS.sub("not", text)
    # Discourse 'No.' and additive 'not only' do not negate the proposition.
    text = re.sub(r"^\s*no[.,!]\s*|\bnot only\b", "", text)
    operators: dict[str, set[str]] = {}
    for kind, value, pattern in _PATTERNS:
        if pattern.search(text):
            operators.setdefault(kind, set()).add(value)
            text = pattern.sub(" ", text)
    # Only the common plural/third-person suffix is folded. This is an
    # alignment aid, not stemming or a claim of language understanding.
    anchors = frozenset(
        w[:-1] if w.endswith("s") and len(w) > 3 else w.replace(",", "")
        for w in _WORDS.findall(text)
        if w not in _FILLER
    )
    return Statement(anchors, {k: frozenset(v) for k, v in operators.items()})


def _opposes(claim: Statement, evidence: Statement) -> bool:
    c, e = claim.operators, evidence.operators
    if c.get("negation") != e.get("negation"):
        return True
    for kind in ("modality", "comparison", "time"):
        left, right = c.get(kind, frozenset()), e.get(kind, frozenset())
        # Multiple operators need clause scope, which this guard cannot infer.
        if len(left) == len(right) == 1 and left != right:
            return True
    return c.get("quantifier") == frozenset({"universal"}) and e.get("quantifier") == frozenset(
        {"partial"}
    )


def conflicts(claim: Statement, evidence: tuple[Statement, ...]) -> bool:
    """Whether matching evidence sentences all oppose the claim.

    Ties with both polarities are left to a future source-conflict policy.
    Equality after operator removal bounds the rule to explicit mutations;
    weaker lexical matches are not sufficient to infer contradiction. Numbers
    remain anchors so another threshold/year cannot supply the polarity.
    """
    if not claim.anchors:
        return False
    opposing = False
    for candidate in evidence:
        if candidate.anchors != claim.anchors:
            continue
        if not _opposes(claim, candidate):
            return False
        opposing = True
    return opposing


class PolarityGuard:
    """Request-local evidence parsing; no retained document data across calls."""

    def __init__(self) -> None:
        self._evidence: dict[str, tuple[Statement, ...]] = {}

    def allows(self, claim: Statement, passage: Passage) -> bool:
        if passage.id not in self._evidence:
            # Headings still supply lexical/numeric evidence in the grounding
            # gate, but must not supply a body's sentence polarity here.
            self._evidence[passage.id] = tuple(
                statement(text) for text in _SENTENCES.split(passage.text) if text.strip()
            )
        return not conflicts(claim, self._evidence[passage.id])
