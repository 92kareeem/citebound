# Changelog

All notable changes to `citebound`. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.1] - 2026-11-22

### Changed

- A sentence that admits no answer is available, or merely points at its own
  citations, is accepted outright instead of being checked for lexical
  support it was never going to have: "(Unable to answer based on given
  passages)" and "(Passages 1, 2, 3)" no longer get stripped, and a one-line
  answer that is only such a sentence is now verified rather than refused
  (previously `total == 0` for that answer, which refused it regardless of
  how honest it was). A sentence naming a specific absent topic - "the
  passages do not mention pricing" - is deliberately NOT included: measured
  against RAGTruth's own labels, four real hallucinations used that exact
  wording to falsely deny that the evidence covers something it actually
  does, and lexical overlap could not separate the honest cases from the
  false ones. See `_is_evidence_commentary` in `grounding.py` for the full
  rationale, including the broader version tried first and rejected.
- On the RAGTruth-derived benchmark (`benchmark/derived`): false refusals
  23 -> 20 of 134, pair accuracy 30 -> 32 of 134 (22% -> 24%). Zero change in
  false accepts; the reduction was measured against the derived set's own
  `-marked` cases before shipping, not assumed. The hand-written benchmark is
  unchanged (31/52 pairs, 17/51 false accepts, 5/53 false refusals): no case
  in it exercises this sentence shape yet.

### Added

- `tests/test_evidence_commentary.py`: the four real RAGTruth sentences that
  the broader, rejected version of this fix would have wrongly accepted are
  permanent regression tests, run against their real passages, not a
  paraphrase.

## [0.2.0] - 2026-11-22

### Changed

- **Renamed: `sentinel-proof` is now `citebound`.** Import `citebound` instead
  of `sentinel_proof` and run `citebound` instead of `sentinel-proof`; every
  other name is unchanged, so the only edit a caller makes is the import line.
  "Sentinel" collides with Microsoft Sentinel and with HashiCorp Sentinel, a
  policy-as-code product close enough in purpose to be genuinely confusing, so
  the library could not be found by the people who needed it. `citebound` names
  what it actually enforces: every claim is bound to the passage it cites.
- `sentinel-proof` 0.1.3 is a final shim release that depends on this package
  and re-exports it, so pinned installs keep working and keep getting the real
  implementation. It is deprecated, not yanked, and receives no further
  releases. New work happens here.
- Benchmarks derived from RAGTruth's human labels are now part of the published
  record alongside the hand-written suite: 22% pair accuracy there against 60%
  here. The gap is the honest measure of how much of the real problem a
  deterministic layer reaches on its own.

### Changed

- Add a dependency-free English polarity guard for sentences with matching
  normalized content anchors: negation, explicit modality changes, reversed
  comparisons/time order, and quantifier strengthening. Apply the same check
  during citation repair. Parse evidence once per verification call.
- On the unchanged 104-case development suite: pairs right 10 -> 27 of 52,
  false accepts 38 -> 21 of 51, false refusals unchanged at 5 of 53.
  Quantifier weakening is intentionally allowed; this is not semantic proof.
- Document benchmark label/scoring limitations before competitor comparisons.
  Generated reports identify a source checkout rather than implying the
  unreleased behavior is available in the declared PyPI version.

### Added

- `benchmark/`: a contrastive benchmark for citation-level grounding. 104 cases
  in 52 minimal pairs across 16 failure classes, each pair one claim that must
  be rejected and a near-identical one that must be kept. `run.py` scores the
  gate and writes `report.md`; `--check` fails if any class regresses against
  `baseline.json`, and CI runs it on every pull request. The case file is plain
  JSONL so another verifier can be scored on identical inputs.
- The package README now publishes the score rather than describing the
  limitation in prose: 19% pair accuracy, 38 false accepts of 51, 5 false
  refusals of 53. No behaviour changed in this entry; the numbers are the
  baseline the next release is measured against.

- Unit guard: a figure is bound to the unit it is quoted with, so a passage
  saying "3 days" no longer supports a claim of "3 months", and a citation
  repair cannot land on such a passage either. It rejects a passage only when
  that passage quotes the claim's own figure under a different unit, so a
  figure inside a range ("3 to 5 days"), a spelled-out unit and anything
  outside the closed vocabulary are left to the existing numeric check. A
  figure may carry more than one unit, because "$1,720 per year" is both a sum
  and a rate. Benchmark: `unit` 0/4 to 4/4 pairs, overall 27 to 31 of 52,
  false accepts 21 to 17 of 51, false refusals unchanged at 5 of 53. On the
  public RAGTruth training split it detected three more unsupported answers
  and refused no additional clean one.

### Fixed

- An answer with no surviving claims now refuses even when
  `max_stripped_ratio=1`. `Verdict.passed` also requires nonempty answer text.
- Reject invalid citation styles and nonfinite/out-of-range thresholds with
  `ValueError` at the core API boundary, including before refusal short-circuits.
  CLI configuration errors exit with usage status 2; its human report shows
  the configured stripping limit.

## [0.1.2] - 2026-11-16

### Added

- `Verdict.to_dict()`: a JSON-ready view of a verdict (lists, plain strings,
  enum values). The CLI's `--json` output and the browser playground both use
  it, so a verdict logged from any of them has the same shape.
- Browser playground at <https://92kareeem.github.io/citebound/>: runs this
  exact package in the browser through Pyodide; nothing leaves the page.

### Changed

- A sentence too short to be a claim (fewer than two words, e.g. `Fee 5% [1].`)
  is still stripped, but its text is now kept in `Claim.text` so the row is
  readable in reports. Verdicts are unchanged.

## [0.1.1] - 2026-11-15

Documentation and packaging metadata only; no change to verification behaviour.

### Changed

- README leads with the problems the package solves, and adds a comparison with
  LLM-judge metrics, hallucination classifiers and guardrail frameworks, plus an FAQ.
- PyPI summary, keywords and classifiers describe the package in the terms
  people search for.

### Added

- `tests/test_readme_claims.py`: every behaviour the README promises is tested.

## [0.1.0] - 2026-11-15

First release, extracted from the grounding gate that runs in production
inside [Citebound](https://github.com/92kareeem/citebound).

### Added

- `verify()`: per-sentence grounding check with three outcomes (supported,
  repaired, stripped), a strip-ratio refusal threshold, and fail-closed
  behaviour for uncited answers.
- `Verdict` and `Claim` with per-claim detail, including the figures a stripped
  claim contained that no cited passage did.
- Numeric (`[1]`, `[2, 3]`) and tag (`[chunk:id]`) citation styles; lenticular,
  padded and full-width tag shapes are normalised.
- `Passage` with duck-typed adapters `from_langchain` and `from_llamaindex`.
- Provenance hashing (`provenance_hash`, `check_provenance`, `HASH_RECIPE`).
- Refusal reason codes and safe refusal prose that never carries the draft.
- `citebound check` CLI with human and JSON output.
