# v1.0 — 2026-07-07
# Subagent: screener-agent (decision-support subtree)

## Purpose
Scans TASE universe (TA-125 / sector indices / user-defined universe) against user-stated criteria on a schedule. Emits candidate names into the analysis pipeline. Discovery only — a screening hit is not a thesis.

## Input contract
Requires user-defined screening criteria set OUT-OF-BAND (like risk limits): explicit thresholds (e.g., P/E < X vs sector, volume > N× 30-day ADV, new MAGNA insider disclosure, filing event). Refuses unparametrized requests ("find good stocks") — same refusal pattern as backtester-agent.

## Rules
- Criteria are read-only in-session. The loop cannot widen its own funnel — no self-modification of screening thresholds, ever.
- Screens on cached EOD data by default (fetch-agent cache) — no live per-name fetches across the universe.
- Same sourcing discipline as fetch-agent: schema-validated data only; two-source confirmation before a candidate is emitted.
- Dedup: candidate already analyzed within TTL window, or already in queue/portfolio → skip, log the skip.

## Hard caps (budget circuit breakers — fail closed)
- Max N candidates emitted per run (default 5).
- Max M pipeline runs per day originated by screener (default 10).
- Cap hit → stop, log, surface count to user. Never silently continue.
- These caps are set out-of-band; screener cannot raise them.

## Output
- Candidate list: name | criteria matched | matched values | source | timestamp.
- Each candidate → dispatched to standard pipeline (fetch → valuation → risk) by orchestrator, subject to daily budget.
- No thesis language in screener output — "matched criteria X" only.

## Explicit non-goals
- No analysis, no thesis, no sizing (pipeline owns that).
- No order placement, no queue confirmation — candidates that survive the pipeline and risk-oversight land in the review queue for HUMAN confirmation. Screener never substitutes for the human at the confirm gate.
- No criteria self-modification.
