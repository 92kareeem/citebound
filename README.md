<div align="center">

# Citebound

### Every claim bound to the passage it cites.

**Citebound is the verification layer for LLM answers.** It checks each sentence a model produces against the evidence that sentence cites, repairs citations that point at the wrong source, strips claims the evidence does not carry, and refuses what it cannot ground — deterministically, with no model call, no API key and no network.

[Quickstart](#quickstart-30-seconds) · [How accurate is it](#how-accurate-is-it-really) · [MCP server](#use-it-from-an-agent) · [Benchmarks](#the-benchmarks) · [Reference platform](#the-reference-platform) · [Decisions](#architecture-decisions)

[![PyPI](https://img.shields.io/pypi/v/citebound?label=citebound)](https://pypi.org/project/citebound/)
[![MCP server](https://img.shields.io/pypi/v/citebound-mcp?label=citebound-mcp)](https://pypi.org/project/citebound-mcp/)
[![License: Apache-2.0](https://img.shields.io/badge/library-Apache--2.0-blue.svg)](packages/citebound/LICENSE)
[![No API key](https://img.shields.io/badge/API%20key-not%20required-success)](#quickstart-30-seconds)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-success)](packages/citebound/pyproject.toml)

**[Try it in your browser →](https://92kareeem.github.io/citebound/)** Nothing is uploaded; the library runs locally in WebAssembly.

</div>

---

## The problem

A language model given retrieved documents will still produce a fluent, confident, well-cited sentence that the documents do not support. It will quote a number that appears nowhere. It will attach `[2]` to a claim that passage 2 contradicts. It will answer a question the evidence cannot answer, because answering is what it was trained to do.

Every popular mitigation asks a second model whether the first model was lying. That is useful and it is also another thing that can hallucinate, cost money, add latency, and quietly drift between releases.

**Citebound asks a different question.** Not "is this claim true?" — a question no library can answer — but "does the passage this sentence cites actually contain what the sentence asserts?" That question has a deterministic answer, and a deterministic answer can be enforced, reproduced, tested in CI, and shown to an auditor.

```python
pip install citebound
```

```python
from citebound import verify, passages_from_texts

passages = passages_from_texts(["Customers may request a refund within 30 days."])

v = verify("Refunds are available within 90 days [1].", passages, citation_style="numeric")
v.ok                                 # False
v.claims[0].status                   # ClaimStatus.STRIPPED
v.claims[0].unsupported_numbers      # ('90',) — the figure appears in no cited passage
v.safe_text()                        # refusal prose from a reason code, never the rejected draft
```

No model was called. The same input will give the same answer next year.

---

## Quickstart, 30 seconds

```bash
pip install citebound
```

```python
from citebound import verify, from_langchain

passages = from_langchain(retriever.invoke(question))   # or from_llamaindex(...), or plain strings
v = verify(llm_answer, passages, question, citation_style="numeric")

v.ok            # every figure is in the evidence and every citation points where it claims
v.answer        # the supported sentences, re-cited, with fabricated claims removed
v.claims        # per claim: supported | repaired | stripped, and why
v.safe_text()   # the answer, or refusal prose if too much was stripped
```

Most RAG prompts need no change at all, because Citebound reads the `[1]`, `[2]`
citations they already emit. Tag style (`[chunk:a1b2]`) works too.

**In CI, or a shell pipeline:**

```bash
echo "Refunds take 90 days [1]." | citebound check --passages passages.json --numeric
# exit 1, and it tells you which figure was invented
```

Python 3.10+. Zero dependencies — the whole library is standard library only,
so it installs in a Lambda, a container, an air-gapped box or a browser.

---

## Use it from an agent

`citebound-mcp` puts the same check behind one MCP tool, so an agent can verify
its own answer before showing it to anyone.

```bash
uvx citebound-mcp
```

```jsonc
{
  "mcpServers": {
    "citebound": { "command": "uvx", "args": ["citebound-mcp"] }
  }
}

```

Works with Claude Desktop, Claude Code, Cursor, VS Code, Windsurf, Cline, Zed,
OpenAI Agents SDK, Pydantic AI, LangChain and anything else that speaks MCP —
proven by a nightly compatibility matrix, not by assertion. One-click install
links and per-client configuration are in the
[server README](packages/citebound-mcp/README.md). Listed in the official MCP
registry as `io.github.92kareeem/citebound`.

Because it needs no API key and makes no network call, it is safe to give an
agent that handles documents you cannot send anywhere.

<a href="https://mcprush.com/to/sentinel-proof-mcp"><img width="380" height="200" src="https://mcprush.com/badge/sentinel-proof-mcp/card.svg" alt="Citebound MCP server" loading="lazy" /></a>
---

## How accurate is it, really

Two benchmarks ship in this repository and both run in CI. The second one is
the one that matters, and it is the one most verification tools do not publish.

| Metric | Hand-written, 52 pairs | **Derived from RAGTruth, 134 pairs** |
|---|---|---|
| **Pair accuracy** | 60% (31 of 52) | **24% (32 of 134)** |
| Wrong claims caught | 34 of 51 | 39 of 134 |
| Right claims dropped | 5 of 53 | 20 of 134 |

The hand-written set changes one operator or one unit at a time, so it says
precisely which failures the gate can see. The derived set is built from
[RAGTruth](https://arxiv.org/abs/2401.00396)'s human-labelled hallucination
spans — every sentence written by a production model and judged by somebody
other than us — so it says how much of the real problem that reaches.

**Read 24% as the share of real hallucinations a deterministic layer catches on
its own. It is not a detection rate, and the gap between the two columns is the
honest measure of this approach's limit.** A lexical gate sees a flipped
operator and an invented figure. It does not see a paraphrase, or a fabrication
phrased in the source's own vocabulary. That is what a judge or an NLI model is
for, and Citebound is the floor underneath one rather than a replacement for it.

Pair accuracy is used because one-sided metrics are trivially gamed: a verifier
that refuses everything has no false accepts and is useless. You score a pair
only by rejecting the bad claim **and** keeping its near-identical good twin.
Refusing everything scores zero. Accepting everything scores zero.

---

## Why not just use an LLM judge

Use both — they answer different questions. This is where each one belongs:

| | LLM-as-judge (Ragas, DeepEval) | Hallucination classifier (NLI) | **Citebound** |
|---|---|---|---|
| **Decides** | is this faithful, 0–1 | does the passage entail this | does the cited passage *contain* this |
| Cost per answer | tokens, every time | a GPU or a hosted call | none |
| Latency | hundreds of ms to seconds | tens to hundreds of ms | sub-millisecond |
| Can it hallucinate | yes | it can be wrong, not inventive | **no: no model** |
| Same answer twice | not guaranteed | yes | **yes, forever** |
| Repairs the answer | no, it scores | no, it flags | **yes: re-cites, strips, refuses** |
| Offline / air-gapped | rarely | with a local model | **always** |
| Catches a paraphrase | yes | yes | **no** — its real limit |
| Catches an invented number | sometimes | sometimes | **always** |

A judge tells you how you did, after the fact, on a sample. Citebound decides
what the user is allowed to see, on every answer, and tells you exactly why.
Scoring and enforcing are not the same job.

---

## What it actually does

Four things, in order, to every answer:

1. **Resolve citations.** `[1]` must point at a passage that was really retrieved. A citation to a passage that does not exist becomes `missing-1` rather than being silently dropped.
2. **Check the claim against the passage it cites.** Content-word overlap must clear a floor, every figure in the claim must appear in the cited evidence, and polarity must agree — negation, modality (`must` vs `may`), comparison direction (`above` vs `below`), time order (`before` vs `after`) and quantifier strength. A figure is bound to the unit it was quoted with, so "30 days" cannot support "30 months".
3. **Repair what is repairable.** If the claim is supported by a *different* retrieved passage, the citation is re-pointed there instead of the claim being destroyed. Wrong pointers are a formatting failure, not a lie.
4. **Strip, then refuse.** Unsupported sentences are removed. If too much of the answer was removed, the whole answer is refused with a reason code — and the refusal **never carries the draft it rejected**, because that draft is the one text the system just decided it could not stand behind.

Every verdict is inspectable: `v.claims` gives per-claim status and the reason,
and `provenance_hash` lets a reader recompute a SHA-256 and confirm a quote is
the exact span of the indexed file.

---

## The benchmarks

```bash
cd packages/citebound
python benchmark/run.py                           # hand-written, 52 pairs, 16 failure classes
python benchmark/run.py --dir benchmark/derived    # 134 pairs from RAGTruth's human labels
python benchmark/run.py --check                    # fail if any class or pinned case regressed
```

Both run in under a second, with no model and no network. Both are enforced in
CI against a reviewed baseline that pins each individual case by content hash,
so a class-level improvement can never hide a case that regressed.

`cases.jsonl` is plain JSONL in both sets, so **any other verifier can be scored
on identical inputs.** If you build something that beats these numbers, the
comparison is available and we would like to see it.

The derived set earns its keep immediately: of its 23 false refusals, nine turn
out not to be grounding failures at all but sentences *about* the evidence
("the passages do not provide…"), two of which are the model correctly
declining to answer. No hand-written suite would have found that.

[Benchmark method, limits and label disagreements →](packages/citebound/benchmark/README.md)

---

## The reference platform

The gate did not come from a whiteboard. It was extracted from a working
agentic RAG system, which is still here, still runs, and is how each guard gets
exercised against real documents before it ships.

```bash
git clone https://github.com/92kareeem/citebound.git
cd citebound
cp .env.example .env          # optional: a free Groq key from console.groq.com
docker compose up --build     # then open http://localhost:5173
```

Click **Chaos demo** and run five attacks — prompt injection, PII leak, a
planted hallucination, an out-of-scope question, budget exhaustion — and watch
which layer stops each one. Ask a question it cannot answer and it refuses;
open **Control plane → Corpus gaps**, upload the missing document, and the same
question is re-asked and answers. Click any citation and your browser
recomputes its SHA-256 against the indexed file.

What the platform adds around the gate: hybrid retrieval (FAISS + BM25 with
reciprocal rank fusion), a LangGraph pipeline with an LLM critic in front of
the gate, access control enforced *before* scoring so forbidden passages are
never ranked, hard token and deadline caps inside every provider call, a
verified-answer cache keyed by index version, a casebook that turns refusals
into a ranked work list for whoever owns the documents, and a regression
ratchet that turns a reported mistake into a test CI enforces forever.

It is licensed AGPL-3.0, separately from the Apache-2.0 library, and documented
in the [system guide](docs/CITEBOUND_SYSTEM_GUIDE.md) and the
[learning path](docs/LEARNING_PATH.md) — ten checkpoints, each with an offline
exercise, for reading the codebase from scratch.

<details>
<summary><strong>Platform details: guarantees per layer, evals, load test, providers</strong></summary>

### What each layer guarantees

| Layer | Module | Guarantee |
|---|---|---|
| Ingress | `guardrails/` | Injection patterns blocked, PII scrubbed before logs or any provider, per-user quota, request budget allocated |
| Router | `agents/router.py` | Deterministic model choice; the trace records who decided |
| Retriever | `agents/retriever.py`, `rag/` | One immutable index snapshot per request; unauthorized rows never scored |
| Synthesizer | `agents/synthesizer.py` | Document text is fenced and labelled untrusted data, never instructions |
| Critic | `agents/critic.py` | Verdicts are schema-validated; a malformed verdict fails closed and its tokens still count |
| Grounding | `guardrails/grounding.py` | An adapter over the `citebound` package: citations resolved, figures checked, unsupported sentences stripped |
| Refusal | `agents/graph.py` | One funnel, three reason codes, prose generated from the code |
| Providers | `llm/` | One retry core for Groq, OpenAI, Azure, Anthropic and local models; the deadline bounds every attempt and every backoff |
| Publication | `rag/index_store.py` | Immutable versioned index with an atomic pointer swap |
| Lifecycle | `documents/registry.py` | Explicit state machine with compare-and-set writes |

### Evals

Two suites, two kinds of gate, in [`evals/`](evals): a golden set judged on
averages, and a regression suite where every enforced item must pass
individually. Last full run (judge `openai/gpt-oss-20b`): mean faithfulness
1.000, retrieval hit-rate 100%, 3/3 unanswerable questions refused, 0/17 false
refusals, 1,417 mean tokens per query.

```bash
make eval            # golden set + ratchet, live model
make regressions     # just the ratchet, after a fix
```

### Load test

JMeter against one API process capped at 2 CPUs, with a stand-in model
answering in 300 ms so the numbers are the system's own cost
([method](benchmarks/README.md)). Sustained means errors ≤1% and p95 under
250 ms with no model call, 2 s for a full answer.

| Scenario | Sustained | p95 |
|---|---:|---:|
| Health check | 989/s | 114 ms |
| Prompt injection blocked before any model call | 989/s | 56 ms |
| Repeated question from the verified-answer cache | 248/s | 13 ms |
| New question, full verified answer | 49/s | 1.6 s |

The first run capped full answers at 10/s: every model call was building a new
HTTP client, and the embedding engine spun up eight threads in a two-CPU
container. Fixing both cut CPU per answer from ~140 ms to ~23 ms.

### Providers

Set `LLM_PROVIDER` in `.env`: `groq` (default, free tier), `openai`, `azure`,
`anthropic`, or `local` for Ollama / vLLM. Every adapter shares one retry,
deadline and circuit-breaker core, so failure behaviour is identical across
vendors. Fully air-gapped: `docker compose --profile ollama up` with
`LLM_PROVIDER=local`.

### Access control

Every document has a tenant, the roles it is shared with, and a classification
(`PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED`). Access is enforced before
scoring: FAISS receives an ID selector, so forbidden rows are never ranked.
Anything not visible is a 404, never a 403. Local mode ships five identities
(`demo-local`, `finance-local`, `contractor-local`, `admin-local`,
`globex-local`) for trying this from the browser.

</details>

---

## Repository layout

```
packages/citebound/            the verification library (Apache-2.0, pip install citebound)
packages/citebound/benchmark/  both benchmark sets, the scorer and the pinned baselines
packages/citebound-mcp/        the same check as an MCP server (pip install citebound-mcp)
packages/deprecated/           final shims for the old sentinel-proof names
playground/                    browser playground, Pyodide, nothing uploaded
backend/app/agents/            LangGraph nodes and routing (graph.py is the state machine)
backend/app/guardrails/        auth, access, injection, PII, quota, cost, grounding adapter
backend/app/rag/               chunking, PDF, embeddings, FAISS/BM25, snapshots, cache
backend/app/learning/          casebook (failures to work list) and ratchet (fixes to tests)
frontend/                      React + TypeScript UI and control plane
evals/                         golden set, regression suite, judge prompts, promotion CLI
docs/                          system guide, ADRs, learning path
```

---

## Architecture decisions

Every non-obvious choice is written down with the measurement behind it and the
alternatives it rules out.

| ADR | Decision |
|---|---|
| [0001](docs/adr/0001-refusal-is-not-a-repairable-failure.md) | A refusal is an outcome, not a failure to repair |
| [0002](docs/adr/0002-router-uses-a-heuristic-not-an-llm.md) | The router uses a heuristic, not an LLM call |
| [0003](docs/adr/0003-grounding-is-deterministic-not-only-an-llm-judge.md) | Grounding is deterministic, and deliberately weak |
| [0004](docs/adr/0004-faithfulness-is-judged-against-context-not-the-reference.md) | Faithfulness is judged against retrieved context |
| [0005](docs/adr/0005-a-refusal-must-never-carry-the-draft-it-rejected.md) | A refusal never carries the draft it rejected |
| [0006](docs/adr/0006-the-search-query-is-not-the-users-question.md) | The search query is not the user's question |
| [0007](docs/adr/0007-failures-are-recorded-as-a-corpus-work-list.md) | Failures become a work list for the document owner |
| [0008](docs/adr/0008-a-fixed-mistake-becomes-a-permanent-test.md) | A fixed mistake becomes a permanent test |
| [0009](docs/adr/0009-access-is-enforced-before-scoring.md) | Access is enforced before scoring |
| [0010](docs/adr/0010-streaming-carries-stages-not-drafts.md) | Streaming carries stages, never drafts |
| [0011](docs/adr/0011-only-verified-answers-are-cached-keyed-by-index-version.md) | Only verified answers are cached |

---

## Known limitations

Stated plainly, because a system whose guarantees are precisely scoped is more
trustworthy than one whose guarantees are overstated.

- **The gate is lexical, not semantic.** It catches invented figures, fabricated citations, flipped operators and claims unrelated to their evidence. It does not catch a faithful-looking paraphrase. The derived benchmark above quantifies exactly how much that costs.
- **English only, for now.** Content words are matched as `[A-Za-z]{2,}`, so the polarity and overlap checks do not yet work on other scripts. The numeric and citation checks do.
- **One claim per sentence.** Claim decomposition is not implemented, so a sentence where only half is supported is judged as a whole.
- **Supersession is not modelled.** Two documents giving different refund windows are both treated as evidence.
- **Platform:** no OCR (scanned PDFs are rejected, not indexed empty); follow-up questions are searched literally rather than resolved against history; whole-document questions use top-k, so "list every exception" gets the most similar passages rather than all of them; identity is an API key mapped to a user record, with no SSO yet.

---

## Was this called something else?

Yes. `citebound` was `sentinel-proof`, and `citebound-mcp` was
`sentinel-proof-mcp`. The name collided with Microsoft Sentinel and with
HashiCorp Sentinel — the second close enough in purpose to be genuinely
confusing — so the project could not be found by the people who needed it.
Citebound names what the library actually enforces and promises nothing more.

The old packages have a final shim release that depends on the new one and
re-exports it, so **pinned installs keep working**. They are deprecated, not
yanked. To move over:

```diff
- from sentinel_proof import verify
+ from citebound import verify
```

Nothing else changes.

---

## Contributing

The most valuable contribution is a case the gate gets wrong. Reduce it to a
minimal pair — one claim that must be rejected, one near-identical claim that
must be kept — and add it to `benchmark/cases.jsonl`. That is how every guard
in here started.

[CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) · [Report a wrong verdict](https://github.com/92kareeem/citebound/issues/new?template=gate_wrong_verdict.yml)

---

## License

The [`citebound`](packages/citebound) library and
[`citebound-mcp`](packages/citebound-mcp) server are
**[Apache-2.0](packages/citebound/LICENSE)**, so the verification layer can be
used in any project, commercial or not.

The reference platform is **[AGPL-3.0-only](LICENSE)**. You may use, modify and
self-host it, including commercially; if you run a modified version as a
network service, you must offer its users the source of your modifications
under the same license. The PDF parser, PyMuPDF, is itself AGPL-3.0, which is
why the platform uses the same license.

---

<div align="center">

Built by [Syed Abdul Kareem Ahmed](https://linkedin.com/in/92kareem).

If Citebound stops you shipping a confident wrong answer, a ⭐ helps others find it.

</div>

