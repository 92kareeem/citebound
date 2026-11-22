# Pairs derived from RAGTruth's human labels

134 pairs, 268 cases. Every sentence here was written by a production language
model and marked, or left unmarked, by RAGTruth's human annotators. We chose
only which labelled sentences to include.

```bash
python benchmark/run.py --dir benchmark/derived          # score
python benchmark/run.py --dir benchmark/derived --check  # fail on regression
python benchmark/derived/build.py --ragtruth <dir>       # rebuild from upstream
```

## Why this set exists

The hand-written set next door is open to a fair objection: the same person
wrote the system and the test. This set answers it. The pairing is ours, the
sentences and the judgements are not.

A pair is one answer, one context, two sentences from that answer: the sentence
an annotator marked as unsupported, and a sentence from the same answer
carrying no mark. Both are checked against the same passages, so the pair
isolates the claim rather than the evidence, and refusing everything still
scores zero.

## Where `citebound` stands on it

Source checkout, with the polarity, unit and evidence-commentary guards.

| Metric | Value |
|---|---|
| Pair accuracy | **24%** (32 of 134) |
| Hallucinated sentences caught | 39 of 134 (29%) |
| Clean sentences wrongly dropped | 20 of 134 (15%) |

| Class | Pairs | Right | Caught | Wrongly dropped |
|---|---:|---:|---:|---:|
| `rt-evident-conflict` | 40 | 7 | 10 / 40 | 8 / 40 |
| `rt-evident-baseless` | 40 | 16 | 17 / 40 | 4 / 40 |
| `rt-subtle-baseless` | 40 | 8 | 11 / 40 | 5 / 40 |
| `rt-subtle-conflict` | 14 | 1 | 1 / 14 | 3 / 14 |

This is much harder than the hand-written set, and the gap is the honest one.
Hand-written cases mutate one operator or one unit, which string logic can see.
Most real hallucinations are new information that simply is not in the passages,
or a quiet contradiction phrased in the source's own vocabulary, and a lexical
checker sees neither. Nobody should read 29% as a hallucination-detection rate
for a production system; read it as how much of the problem the deterministic
layer reaches on its own.

## What the false refusals revealed

Of the original 23, three were not grounding failures at all: a blanket
admission of no answer, and a bare pointer to citations with nothing asserted,
which the gate used to treat as a claim needing support and strip:

> (Unable to answer based on given passages)
>
> Please note that the provided passages may not have all the necessary
> information to answer the question completely.

Neither names anything specific the evidence lacks, so neither can be a false
claim about coverage, and stripping them was worse than useless on the one
that is a correct refusal. This is now fixed: see `_is_evidence_commentary` in
`grounding.py`.

A broader version of this fix was tried first, also accepting a sentence that
names a specific absent topic - "the passages do not provide detailed
instructions on how to start a paw paw tree from seed" - on the reasoning that
such a sentence, true or false, says nothing about passage content a lexical
check could use. Measured against this set's own `-marked` half, that
reasoning does not hold: four real labelled hallucinations use the identical
wording to *falsely* deny that the evidence covers something it actually does,
and topic-word overlap could not separate the honest cases from the false
ones (both ranged 0.06-0.40 on their own content words). That broader version
is documented in `grounding.py`'s history for the record, not shipped: a
3-case fix with zero measured cost was kept over a wider one with four.

The remaining twenty are the true shape of the problem: ordinary paraphrase,
or a specific coverage claim that may or may not be true. Both need an actual
judge or an entailment model to resolve; no rule over word surfaces reaches
them without the same false-accept risk just measured.

## Limits, stated plainly

* **Train split only.** The 160 labelled QA responses in RAGTruth's test split
  are never read by the builder, so they remain a genuinely held-out set for a
  later evaluation. Do not tune against that split.
* **No citations upstream.** RAGTruth answers cite nothing, so each case cites
  every passage, which is what an answer generated from the whole context
  asserts. These cases measure claim verification; the hand-written set is what
  measures citation resolution and repair.
* **Unmarked is not verified.** A "keep" case is a sentence no annotator
  marked. It is evidence about false refusals, not a certificate of truth.
* **One sentence per case.** The scorer reads the first parsed claim, so a case
  carries one. Answers in production carry many, and a per-answer metric would
  be a different measurement.
* **Sentence splitting is independent.** The builder uses a plain regular
  expression, never the package's own splitter, so the test does not inherit
  the behaviour it measures.
* **QA only.** RAGTruth also covers summarisation and data-to-text. Those tasks
  have different grounding conventions and are left out.

## Scoring another tool

Same contract as the hand-written set: read `cases.jsonl`, decide for each case
whether the claim survives, and score pairs. The `source` field on every case
gives the upstream ids, so anyone can confirm the derivation against RAGTruth
rather than trusting this file.

See [NOTICE](NOTICE) for attribution and the citation the RAGTruth authors ask
for.
