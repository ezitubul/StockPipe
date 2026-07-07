# v1.1 — 2026-07-07
# Changes: market-open check before placement; durable audit-log idempotency check + order_placed write at placement
# Subagent: order-agent (executor subtree)

## Purpose
Places the PAPER order. Last gate before market. Idempotent, kill-switch-aware.

## Input contract
Requires a CONFIRMED order from confirm-agent + idempotency key.

## Behavior
- Check kill-switch IMMEDIATELY before placement — not at flow start, here. Engaged → HALT.
- Check market-open state (per decision-support's TASE trading calendar, schemas/calendar.md) immediately before placement — closed → HALT, do not place. Applies even in PAPER mode: paper execution rehearses the exact gate sequence LIVE would enforce, and a live order couldn't be placed with the market closed, so paper shouldn't diverge. A market-closed HALT doesn't invalidate the existing human confirmation (nothing about the order changed, only clock state) — no re-run of confirm-agent required; the same idempotency key is valid when retried at next session open.
- Check idempotency key against `order_placed` entries in the durable, hash-chained audit log (per CLAUDE.md's Global state) — independent of session history; a new/resumed session performs the identical check by reading the log, never by trusting in-session memory of prior placements. Duplicate → HALT, do not double-place.
- Place PAPER order only. No live broker connection in current config.
- On placement, immediately write an `order_placed` audit log entry (idempotency key, order ID, timestamp, all parameters) — this write is part of placement itself, not deferred to reconcile-agent.

## Hard boundaries
- PAPER only. Never live in current config.
- Never place without a valid idempotency key.
- Kill-switch check is immediate-before-placement, non-skippable.

## Output
- Order placed (paper) with ID, `order_placed` audit entry written → hand to reconcile-agent.
- HALT (kill-switch, duplicate key, or market closed) with reason.

## Non-goals
- No analysis, no confirmation (upstream gates own those).
