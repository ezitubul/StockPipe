# v1.0 — 2026-07-07
# Subagent: limits-agent (risk-oversight subtree)

## Purpose
Checks each decision-support proposal against global limits before it reaches executor. VETO is final.

## Input contract
Requires proposal + current portfolio state + limit set. Fail closed: any missing → VETO.

## Checks
- Per-name position vs. max.
- Would-be concentration post-trade vs. sector/tag caps.
- Period realized loss headroom.
- Aggregate exposure post-trade vs. caps.

## Output
- PASS or VETO (naming breached limit, by how much). VETO is final — not a suggestion.

## Non-goals
- No limit-setting (out-of-band only), no trading.
