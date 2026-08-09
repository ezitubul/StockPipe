# Tokenomics

Code chews, Claude judges - but be precise about which half is which.

## What actually runs outside a model

| Step | Outside a model? |
|---|---|
| Issuing the search, fetching the page | yes - a network call |
| Choosing the query | **no** |
| Stripping boilerplate, canonicalising URLs | yes - `lib/ingest.py` |
| Deduplicating a wire story across outlets | yes |
| Filtering out articles matching nothing in the universe | yes |
| Caching between the 13:00 and 17:00 scans | yes |
| Arithmetic, fees, gates, sessions, clustering | yes - `lib/` |
| **Reading the page and deciding what it means** | **no** |
| **Summarising into the brief schema** | **no** |

The middle column is the honest answer: retrieval is external, comprehension is
not. A scout summarising an article is a model doing summarisation, and the page
body sits in its context window while it happens. `lib/ingest.py` does not
change that - it shrinks and filters the input first so the model sees the
smallest set of already-relevant, already-deduplicated text that still answers
the question.

On a realistic scan that pass removes roughly three quarters of the bytes before
a token is spent: navigation and script chrome, one wire story reprinted by five
outlets, and everything mentioning nothing in the universe.

## Numbers must never be extracted by a model

The place where LLM extraction is both most expensive and most dangerous is
reading a price out of prose. Prefer a structured source - a quote endpoint,
JSON-LD on the page, an exchange feed - parsed in Python. Where that is not
available, `price-verifier` requires a second independent source and blocks on
disagreement, which is a mitigation rather than a fix.

`lib/money.py` will happily convert a hallucinated price with perfect precision.
Determinism downstream is worthless if the input was invented upstream.

## Orchestrator never reads raw pages

Scouts fetch and compress. They write JSON to `state/briefs/` and return a path.
The synthesizer reads paths, not page bodies. The orchestrator reads the
synthesizer's ranked output. A full multi-market scan therefore costs the
orchestrator a few thousand tokens instead of the hundreds of thousands the raw
articles would.

## JSON out, never prose

Every scout returns a fixed schema and nothing else - no preamble, no summary,
no markdown fence. Prose from a subagent is tokens spent on something the
orchestrator will paraphrase anyway.

## Model tiering

| Tier | Used for |
|---|---|
| Haiku | regional scouts, price verification - fetch, extract, emit |
| Sonnet | macro-scout, synthesizer - weighing conflicting evidence |
| Opus | reserved for the human conversation and for design changes |

## Deterministic before probabilistic

Anything with a right answer is Python: unit conversion, fees, concentration,
session hours, ledger arithmetic. This is cheaper than an LLM, and unlike an LLM
it is testable and it cannot be talked out of a limit.

## Static prefix first

`CLAUDE.md`, agent definitions and the registry are stable and cacheable. Dated
briefs and portfolio state are volatile and come last in the context. Never
interleave them.

## Scan on a schedule, not a loop

Four scans a day at fixed times beat continuous polling. The market does not
reward attention between the bells, and neither does the token budget.

## What subagents actually save

They save the **orchestrator's** context, not total tokens. Each subagent runs
in its own context window, so a scan that fans out to five scouts can use
several times the tokens of a single-threaded run. What it buys is that the
article bodies, search results and page dumps never enter the main thread, so
the orchestrator stays coherent across a long session instead of compacting
away the parts that matter.

Delegate for context isolation and for parallelism. Do not delegate expecting a
smaller bill.

Two settings do reduce real cost:

* `load-claude-md: false` on every scout. A scout needs the pence-and-agorot
  warning, which is in its own prompt; it does not need the withdrawal formula
  or the hedging doctrine. That is 139 lines skipped per scout per scan.
* Haiku wherever the job is fetch, extract, emit.

## Tool scoping lives in settings.json

The subagent `tools` field is an allowlist of tool **names** - `Read`, `Bash`,
`WebSearch`. It does not accept command patterns. `Bash(python mw.py:*)` in a
subagent's frontmatter does not scope anything; scoping belongs in
`.claude/settings.json` under `permissions`.

The scouts are restricted the reliable way instead: they are given
`WebSearch, WebFetch` and nothing else. With no `Bash` and no `Write` they
cannot touch the ledger regardless of what a fetched page tells them to do, and
with no `Agent` they cannot spawn anything either.

## How much the ingest pass actually saves

The 75% figure from the first demonstration was three synthetic documents and
is not evidence of anything. The real answer depends on which fetch path the
scouts use, and the two paths differ by a factor of two.

**Path A - scouts use `WebFetch`.** It already returns stripped text, so
boilerplate removal contributes almost nothing on top. What remains is dedup,
relevance filtering and truncation:

| duplicates | irrelevant | truncation | total |
|---|---|---|---|
| 15% | 10% | none | 24% |
| 25% | 20% | none | 40% |
| 25% | 20% | 30% | 58% |
| 35% | 20% | 30% | 64% |

**Path B - a script fetches raw HTML.** News HTML runs 200-800 KB for 5-10 KB
of article text, so stripping alone removes 90-95% and the compound figure
reaches 94-97%. This path is worth building only if the volume justifies it.

**Realistic expectation on the current design: 35-55%.** The variance is real -
a day heavy with wire syndication dedups far better than a day of original
reporting.

`mw.py ingest` appends every run to `state/ingest-log.jsonl` and reports a
cumulative figure. After roughly twenty scans that number is measured rather
than assumed, and it is the only one worth quoting.
