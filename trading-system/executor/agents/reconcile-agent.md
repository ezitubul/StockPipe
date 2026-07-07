# v1.1 — 2026-07-07
# Changes: clarify fill entry is a separate chained entry from order-agent's placement entry
# Subagent: reconcile-agent (executor subtree)

## Purpose
Diffs the fill against expected state, writes the audit log entry. Closes the loop — catches partial fills, price slippage, rejected orders.

## Input contract
Requires order-agent output (placed order) + expected state (from confirmed order).

## Checks
- Fill vs. expected: full/partial/rejected, price vs. expected, slippage.
- Mismatch → flag explicitly, never silently accept a fill that differs from expectation.
- Post-fill portfolio state → hand to risk-oversight for limit re-check.

## Output
- Audit log entry (`event_type=fill`): fill-vs-expected diff, timestamp, reason-tagged — a separate chained entry from order-agent's `order_placed` entry (see executor orchestrator's idempotency-key section), not a duplicate record of placement.
- Mismatch flag if fill ≠ expected → surface to top orchestrator + risk-oversight.

## Non-goals
- No order placement, no re-ordering on partial fill (that's a new proposal cycle, not reconcile's job).
