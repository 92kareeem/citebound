# Changelog

All notable changes to `sentinel-proof`. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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

## [0.1.2] - 2026-11-16

### Added

- `Verdict.to_dict()`: a JSON-ready view of a verdict (lists, plain strings,
  enum values). The CLI's `--json` output and the browser playground both use
  it, so a verdict logged from any of them has the same shape.
- Browser playground at <https://92kareeem.github.io/sentinel-rag/>: runs this
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
inside [Sentinel](https://github.com/92kareeem/sentinel-rag).

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
- `sentinel-proof check` CLI with human and JSON output.
