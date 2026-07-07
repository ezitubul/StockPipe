# v1.0 — 2026-07-07
# Subagent: drawdown-agent (risk-oversight subtree)

## Purpose
Tracks realized + unrealized drawdown vs. limit. Triggers global HALT-all (kill-switch) on breach.

## Input contract
Requires P&L history + current unrealized. Fail closed on missing data.

## Checks
- Current drawdown vs. max-drawdown limit.
- Rate-of-drawdown (fast breach = higher urgency).
- Trigger: max-drawdown breached → signal top orchestrator to engage kill-switch (HALT-all).

## Output
- Drawdown status + HALT-all trigger signal if breached.

## Non-goals
- No trading, no unwind execution (signals; unwind-agent proposes, executor gates).
