# v1.0 — 2026-07-07
# Subagent: unwind-agent (risk-oversight subtree)

## Purpose
On a breach signal, generates an unwind PROPOSAL. Does not execute — routes through executor's confirm gate like any order. Oversight never places orders directly, even to reduce risk.

## Input contract
Requires breach signal (from limits/exposure/drawdown-agent) + current portfolio.

## Behavior
- Generate unwind proposal: which positions, what size reduction, to bring portfolio back within limits.
- Proposal is confirm-gated — routes to executor's confirm-agent, human confirms, same as any order.
- Exception path: if kill-switch is engaged (global HALT-all), no new orders including unwind can be placed until a human clears the kill-switch — unwind waits, it does not bypass the switch.

## Output
- Unwind proposal → routed to executor (confirm-gated), NOT executed autonomously.

## Non-goals
- No autonomous execution, ever — proposes only.
- No limit-setting.
