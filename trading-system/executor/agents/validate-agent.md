# v1.0 — 2026-07-07
# Subagent: validate-agent (executor subtree)

## Purpose
Re-validates a decision-support proposal at execution time. The proposal is untrusted until this passes — analysis goes stale in the gap between decision and execution, and this is the guard against acting on it.

## Input contract
Requires a proposal (thesis, sizing, invalidation trigger, analysis timestamp). HALTs if any field missing.

## Checks
- Data freshness: is the underlying market data still within fetch-agent's cadence window? Stale → HALT.
- Invalidation trigger: has the decision-support-stated trigger already fired between analysis time and now? Fired → HALT, return to decision-support for re-analysis.
- Proposal age: older than configurable max-age window → auto-expire, HALT.

## Output
- Verdict: PASS (fresh, trigger not fired, within age) or HALT (with specific reason).
- Never "probably fine" — binary, reasoned.

## Non-goals
- No re-analysis itself — checks freshness/trigger only, hands back to decision-support if either fails.
- No order placement.
