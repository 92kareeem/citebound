"""Derive contrastive pairs from RAGTruth's human-labelled hallucination spans.

    python benchmark/derived/build.py --ragtruth <dir holding the two jsonl files>

The hand-written set beside this one is open to a fair objection: the same
person wrote the system and the test. This set answers it. Every sentence here
was written by a production language model and labelled by RAGTruth's human
annotators, not by us. We choose only which labelled sentences to include.

How a pair is made. One answer, one context, two sentences from that answer:
the sentence a human marked as unsupported, and a sentence from the same answer
that carries no mark at all. Both are checked against the same passages, so the
pair isolates the claim rather than the evidence, and a verifier that refuses
everything scores zero exactly as it does on the hand-written set.

Deliberate limits, so nobody reads more into the score than it carries.

* Train split only. The 160 labelled QA responses in RAGTruth's test split are
  never read here, so they remain available as a genuinely held-out set.
* RAGTruth answers carry no citations. Each case cites every passage, which is
  what an answer generated from the whole context asserts. These cases
  therefore measure claim verification, not citation resolution; the
  hand-written set is what measures citation behaviour.
* An unlabelled sentence is one no annotator marked. That is not the same as a
  sentence proved correct, so a "keep" case is evidence about false refusals
  rather than a certificate of truth.
* Sentences are split by a plain regular expression here, never by the splitter
  inside the package, so the test does not inherit the behaviour it measures.

RAGTruth is MIT licensed; see NOTICE for attribution and the citation its
authors ask for.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "cases.jsonl"

# Independent of the package's own splitter, on purpose.
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_PASSAGE = re.compile(r"\n*passage \d+\s*:", re.IGNORECASE)

_LABEL_CLASS = {
    "Evident Conflict": "rt-evident-conflict",
    "Evident Baseless Info": "rt-evident-baseless",
    "Subtle Conflict": "rt-subtle-conflict",
    "Subtle Baseless Info": "rt-subtle-baseless",
}
# Enough of a cap per class that no single failure mode dominates the score.
_PER_CLASS = 40
_MIN_CHARS, _MAX_CHARS = 40, 400
_MIN_WORDS = 6
# A label has to account for a real part of the sentence, or the sentence is
# mostly supported text that happens to touch a marked span.
_MIN_SPAN_SHARE = 0.30


def sentences(text: str) -> list[tuple[int, int, str]]:
    """Every sentence with its character span in ``text``."""
    spans, start = [], 0
    for piece in _SENTENCE.split(text):
        begin = text.find(piece, start)
        if begin < 0:
            continue
        spans.append((begin, begin + len(piece), piece.strip()))
        start = begin + len(piece)
    return spans


def usable(sentence: str) -> bool:
    if not _MIN_CHARS <= len(sentence) <= _MAX_CHARS:
        return False
    if sentence.rstrip().endswith(":"):
        return False  # a lead-in asserts nothing, and the gate skips it
    return len(re.findall(r"[A-Za-z]{2,}", sentence)) >= _MIN_WORDS


def passages_of(source: dict) -> list[str]:
    raw = source["source_info"]["passages"]
    parts = [part.strip() for part in _PASSAGE.split(raw)]
    return [part for part in parts if part]


def pair_for(response: dict, source: dict) -> tuple[dict, dict] | None:
    """The marked sentence and a clean one from the same answer, or nothing."""
    text = response["response"]
    marked: list[tuple[int, str, str, str]] = []
    clean: list[str] = []
    for begin, end, sentence in sentences(text):
        if not usable(sentence):
            continue
        covered = 0
        label_type = meta = ""
        for label in response["labels"]:
            overlap = min(end, label["end"]) - max(begin, label["start"])
            if overlap > 0:
                covered += overlap
                if not label_type:
                    label_type = label["label_type"]
                    meta = " ".join((label.get("meta") or "").split())[:160]
        if covered == 0:
            clean.append(sentence)
        elif covered / max(len(sentence), 1) >= _MIN_SPAN_SHARE:
            marked.append((covered, sentence, label_type, meta))

    if not marked or not clean:
        return None
    covered, bad_sentence, label_type, meta = max(marked)
    good_sentence = max(clean, key=len)
    group = _LABEL_CLASS.get(label_type)
    if group is None:
        return None

    texts = passages_of(source)
    if len(texts) < 2:
        return None
    citation = "[" + ", ".join(str(n) for n in range(1, len(texts) + 1)) + "]"
    stem = f"rt-{response['source_id']}"
    common = {
        "class": group,
        "passages": texts,
        "question": source["source_info"]["question"],
        "citation_style": "numeric",
        "source": {
            "dataset": "RAGTruth",
            "split": "train",
            "response_id": response["id"],
            "source_id": response["source_id"],
            "model": response["model"],
        },
    }
    bad = {
        "id": f"{stem}-marked",
        "expect": "reject",
        "pair": f"{stem}-clean",
        "answer": f"{bad_sentence} {citation}",
        "why": f"{label_type} marked by a RAGTruth annotator: {meta}" if meta else label_type,
        **common,
    }
    good = {
        "id": f"{stem}-clean",
        "expect": "keep",
        "pair": f"{stem}-marked",
        "answer": f"{good_sentence} {citation}",
        "why": "same answer and passages, carrying no annotator mark",
        **common,
    }
    return bad, good


def build(ragtruth: Path) -> list[dict]:
    sources = {
        row["source_id"]: row
        for row in map(json.loads, (ragtruth / "source_info.jsonl").read_text("utf-8").splitlines())
    }
    lines = (ragtruth / "response.jsonl").read_text("utf-8").splitlines()
    responses = [row for row in map(json.loads, lines)]
    # Deterministic, and one pair per context so near-identical passages cannot
    # dominate: sorting by id makes the selection reproducible.
    responses.sort(key=lambda row: str(row["id"]))

    taken: dict[str, int] = {}
    seen_sources: set[str] = set()
    cases: list[dict] = []
    for response in responses:
        source = sources[response["source_id"]]
        if source["task_type"] != "QA" or response["split"] != "train" or not response["labels"]:
            continue
        if response["source_id"] in seen_sources:
            continue
        made = pair_for(response, source)
        if made is None:
            continue
        group = made[0]["class"]
        if taken.get(group, 0) >= _PER_CLASS:
            continue
        taken[group] = taken.get(group, 0) + 1
        seen_sources.add(response["source_id"])
        cases.extend(made)
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--ragtruth",
        type=Path,
        required=True,
        help="directory holding RAGTruth's response.jsonl and source_info.jsonl",
    )
    args = parser.parse_args()
    cases = build(args.ragtruth)
    with OUT.open("w", encoding="utf-8", newline="\n") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n")

    counts: dict[str, int] = {}
    for case in cases:
        counts[case["class"]] = counts.get(case["class"], 0) + 1
    print(f"{len(cases)} cases ({len(cases) // 2} pairs) written to {OUT.name}")
    for group in sorted(counts):
        print(f"  {group:<22} {counts[group] // 2:>3} pairs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
