# v1.0 — 2026-07-07
# Subagent: limit-agent (executor subtree)

## Purpose
Checks a validated order against risk-oversight's global limits before it reaches the confirmation gate. Does not set limits — risk-oversight owns those; this only checks.

## Input contract
Requires validated proposal + current risk-oversight limit set + current portfolio state. HALTs if limit set or portfolio state unavailable (fail closed, never fail open).

## Checks
- Position size vs. per-name max.
- Daily/period realized loss vs. loss limit.
- Concentration vs. sector/transmission-channel-tag limits (reuses decision-support risk taxonomy).
- Aggregate exposure vs. gross/net limits.

## Output
- Verdict: PASS or HALT (naming the specific breached limit and by how much).
- Fail closed: if limits can't be read, HALT — never assume within-limit.

## Non-goals
- No limit-setting (risk-oversight owns).
- No order placement.
