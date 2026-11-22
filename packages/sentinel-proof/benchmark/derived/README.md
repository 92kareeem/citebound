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

## Where `sentinel-proof` stands on it

Source checkout, with the polarity and unit guards.

| Metric | Value |
|---|---|
| Pair accuracy | **22%** (30 of 134) |
| Hallucinated sentences caught | 39 of 134 (29%) |
| Clean sentences wrongly dropped | 23 of 134 (17%) |

| Class | Pairs | Right | Caught | Wrongly dropped |
|---|---:|---:|---:|---:|
| `rt-evident-conflict` | 40 | 7 | 10 / 40 | 8 / 40 |
| `rt-evident-baseless` | 40 | 15 | 17 / 40 | 5 / 40 |
| `rt-subtle-baseless` | 40 | 7 | 11 / 40 | 7 / 40 |
| `rt-subtle-conflict` | 14 | 1 | 1 / 14 | 3 / 14 |

This is much harder than the hand-written set, and the gap is the honest one.
Hand-written cases mutate one operator or one unit, which string logic can see.
Most real hallucinations are new information that simply is not in the passages,
or a quiet contradiction phrased in the source's own vocabulary, and a lexical
checker sees neither. Nobody should read 29% as a hallucination-detection rate
for a production system; read it as how much of the problem the deterministic
layer reaches on its own.

## What the false refusals revealed

Nine of the 23 are not grounding failures at all. They are sentences *about*
the evidence rather than claims drawn from it:

> According to passage 1, you can delete a row by right-clicking in a cell.
>
> The passages do not provide detailed instructions on how to start a paw paw
> tree from seed.
>
> (Unable to answer based on given passages)

The gate treats each as a claim needing support and strips it. Two of them are
the model correctly declining to answer, so stripping them is worse than
useless. A sentence whose subject is the passages themselves is not a claim
about the world, and the package already has the shape of this idea in its
lead-in check. Extending it is the first fix this set has earned.

The remaining fourteen are ordinary paraphrase: the same fact in different
words, below the lexical overlap floor. Those need the optional semantic tier,
not another rule.

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
