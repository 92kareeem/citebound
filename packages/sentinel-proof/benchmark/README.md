# A contrastive benchmark for citation-level grounding

104 cases, 52 paired examples, 16 failure classes. Most pairs contrast a
claim to reject with a faithful claim to keep. Seven pairs change the evidence
and one citation-repair pair has two keep labels; these are paired controls,
not strictly contrastive minimal pairs.

```bash
python benchmark/run.py                  # score and write report.md
python benchmark/run.py --check          # fail if any class or pinned case got worse
python benchmark/run.py --update-baseline
```

No dependencies, no model, no network. It runs in under a second.

## Regression checks and reproducibility

`--check` compares both the historical class totals in `baseline.json` and
individual outcomes in `case-baseline.json`. A previously correct case becoming
wrong fails even if an improvement elsewhere leaves its class totals unchanged.
Existing failures may stay unchanged or improve. Improvements become protected
when the reviewed baseline is updated; an ordinary check never updates it.

The case baseline records schema version 1, scorer `first-claim-status-v1`, and
SHA-256 of each complete case object serialized as sorted-key, compact UTF-8 JSON
with non-ASCII characters preserved. This pins inputs, labels, pair membership
and rationale, but ignores JSON whitespace, object key order and case order.
Changes to case content, additions and removals fail until explicitly reviewed.
Hashes detect changes relative to the checked-in baseline; they do not establish
label correctness or external authenticity.

`--update-baseline` deliberately updates **both** baseline files. Review their
diffs alongside the code and report; never use it simply to make CI green.
It cannot be combined with `--check`. Dataset validation rejects duplicate IDs,
invalid labels and missing, nonreciprocal or cross-class pairs before scoring.
Two-keep citation-repair controls remain valid. No labels or verifier behavior
were changed by introducing these checks.

## Why pairs

A verifier that rejects every claim has a false-accept rate of zero and is
useless. A verifier that accepts everything never refuses a good answer and is
also useless. Either one looks excellent on a one-sided metric.

So the headline number here is **pair accuracy**: the share of pairs where the
verifier rejects the bad half *and* keeps the good half. You cannot buy it with
caution, and you cannot buy a high score with permissiveness. On this version,
accepting everything scores 1/52 because the repair control has two keep labels;
rejecting everything scores 0/52.

## Where `sentinel-proof` stands today

Measured on this set, not on a friendly one. The current report is in
[`report.md`](report.md).

| Metric | 0.1.2 |
|---|---|
| Pair accuracy | 19% (10 of 52) |
| False accepts | 38 of 51 |
| False refusals | 5 of 53 |

The unreleased source checkout reaches 31/52 pairs (60%), with 17/51 false
accepts and the same 5/53 false refusals on these unchanged inputs. Two
dependency-free guards account for the difference.

The polarity guard checks English negation, explicit modality changes,
comparison direction, temporal order and quantifier strengthening, only when
normalized content anchors match. It deliberately allows universal-to-partial
weakening; the two existing `quantifier` reject labels for that behavior remain
visible as disagreements.

The unit guard binds each figure to the unit it is quoted with, so "3 days"
stops supporting "3 months". It rejects a passage only when that passage quotes
the claim's own figure under a different unit, which leaves ranges, spelled-out
units and unknown units alone.

Neither guard changes the headline tables above, which report the released
version. Both were also run against the roughly 4,900 good-quality question
answering responses in the public RAGTruth training split, scored by whether a
sentence is removed, as an external false-refusal check: the polarity guard
changed no decision there, and the unit guard caught three more unsupported
answers while refusing no additional clean one. That split has no citation
labels and is used here for development only, never as an accuracy claim.

That is a poor score and it is published on purpose. The gate compares bags of
words and figures, so it cannot see the word that carries the meaning: "not",
"may", "below", "after", or a name it has never read. Three classes it already
handles (fabricated figures, citation repair, number formatting) score full
marks; most of the rest do not. The numbers exist so that every change can be
measured against them instead of argued about.

**This set is adversarial by construction.** It is not an estimate of how often
a real RAG answer is wrong, and a score here does not transfer to production
rates. It measures whether a specific failure mode is detectable at all.

## Interpretation limits before external comparisons

- This is a development regression set, not an independently held-out test.
  Changes are designed with these cases visible.
- `all` to `some` and `always` to `sometimes` can preserve entailment while
  losing completeness. Do not count these as unambiguous hallucinations when
  comparing entailment classifiers. Version and review revised labels separately;
  do not silently rewrite the original baseline.
- Staleness needs an explicit evaluation date and source precedence policy.
  The current string-only cases do not supply a structured policy.
- The runner reads the first parsed claim's status. Before adding decomposition,
  score every claim and the final released text; otherwise a kept first clause
  can hide a stripped later clause or a whole-answer refusal.
- Individual correctness and input hashes are now pinned, preventing class
  totals from hiding regressions. Citation targets, final-output scoring and
  retention metrics still need implementation before an external leaderboard.
- Detector-only and repair-capable systems need separate detection and
  enforcement tracks. Freeze thresholds on development data, then evaluate an
  untouched test split grouped by source and template.

## The case schema

`cases.jsonl`, one JSON object per line, deliberately plain so that any tool in
any language can be scored on the same inputs.

| Field | Meaning |
|---|---|
| `id` | unique, stable; referenced by `pair` |
| `class` | the failure class, for the per-class table |
| `expect` | `reject` if the claim must not survive, `keep` if it must |
| `pair` | the `id` of the other half of the minimal pair |
| `passages` | the retrieved evidence, in the order the model saw it |
| `answer` | one claim, with its citation |
| `question` | optional; figures the user typed are not fabrications |
| `citation_style` | optional, `numeric` (default) or `tag` |
| `why` | one line on what the case is testing |

Each `answer` holds exactly one claim, so scoring needs no judgement: the claim
survived, or it did not.

## The classes

| Class | What it tests |
|---|---|
| `negation` | "not permitted" read as "permitted" |
| `modality` | an obligation (`must`) weakened to a permission (`may`) |
| `quantifier` | `all` narrowed to `some`, `always` to `sometimes` |
| `comparison` | a threshold direction inverted, `above` to `below` |
| `time-order` | `before` and `after` swapped |
| `unit` | the right figure with the wrong unit, 3 days to 3 months |
| `entity` | the right action credited to the wrong person or company |
| `attribute` | a real figure attached to the wrong subject |
| `compound` | a sentence where only half is supported |
| `staleness` | a superseded version quoted as current |
| `paraphrase` | faithful restatement kept, unfaithful one rejected |
| `multilingual` | the same checks in Spanish, German, French, Hindi, Chinese |
| `arithmetic` | a figure correctly derived from two cited figures |
| `number-format` | `1,200` and `1200` are one figure; `5.4` is not `4.5` |
| `fabrication` | a figure that appears in no passage |
| `repair` | a wrong citation that another retrieved passage supports |

## Scoring another tool

Read `cases.jsonl`, run your verifier on each `answer` with its `passages`, and
decide whether the claim survived. Then score pairs the way `run.py` does. The
comparison is only fair if every tool sees the same passages in the same order
and is asked the same question: does this one claim survive.

For model-based detectors that return a score rather than a decision, pick the
threshold on a held-out split and say which threshold you used.

## Adding a case

Add both halves of the pair, keep the difference between them as small as the
failure allows, then run `--update-baseline` in the same commit as the change
that justifies it. Review both baseline files and the report. A new class needs
at least two pairs.

Good cases come from real failures. If a user reports an answer that should
have been refused, reduce it to a minimal pair and add it here.

## Related work

These measure different things and are worth running alongside, not instead:
[RAGTruth](https://arxiv.org/abs/2401.00396) and LLM-AggreFact score detection
over naturally generated text; [PARCEL](https://arxiv.org/html/2610.10971v1)
does adversarial claim-level work for legal citations;
[Faithfulness-QA](https://arxiv.org/html/2604.25313v2) supplies entity
substitution at scale. This suite focuses on small executable regressions for
citation-level verification across these classes. Its research novelty has not
been established by a comprehensive literature review.
