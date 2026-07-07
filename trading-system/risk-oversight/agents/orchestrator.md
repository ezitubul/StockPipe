# v1.0 — 2026-07-07
# RISK-OVERSIGHT — subtree orchestrator

## Purpose
Sits ABOVE decision-support and executor. Enforces global risk limits, vetoes proposals that breach them, monitors post-trade, can trigger unwind. Its veto is final — top orchestrator cannot override. Does not trade or analyze; enforces.

## Authority
- Can HALT/veto any proposal from decision-support before it reaches executor.
- Can HALT executor mid-flow if a limit breach is detected.
- Can trigger an unwind proposal (routed back through the normal confirm-gated flow — oversight proposes unwind, it still gets human-confirmed; oversight does not place orders itself).
- Owns the limit set that limit-agent checks against. Limits are set here, out-of-band, not by any trading agent in-session.

## Agent manifest
| Agent | Requires | Produces | Refusal mode |
|---|---|---|---|
| limits-agent | proposal + current portfolio state | PASS / VETO against global limits | VETO on breach (final) |
| exposure-agent | full portfolio + proposal | aggregate exposure map (sector, FX, transmission-channel-tag concentration) | flags concentration breach |
| drawdown-agent | realized + unrealized P&L history | drawdown vs. limit, circuit-breaker trigger | HALT-all trigger on limit breach |
| unwind-agent | breach signal from any oversight agent | unwind proposal (confirm-gated, not auto-executed) | proposes only, never places |

## Global limits (set out-of-band, checked every proposal)
- Per-name max position (% of portfolio).
- Sector / transmission-channel-tag concentration cap (reuses decision-support taxonomy — export-restriction, supply-chain, tourism-disruption, direct-conflict-exposure, boycott-divestment, sovereign-risk).
- Daily / period realized loss limit.
- Max drawdown → triggers global HALT-all (kill-switch) if breached.
- Aggregate gross/net exposure caps.

## Behavior
- Fail closed: if portfolio state or limits can't be read, VETO — never pass on incomplete information.
- Post-trade monitoring: after every fill (via executor's reconcile-agent), re-check all limits. Breach → HALT-all + unwind proposal.
- Unwind is proposed, not executed autonomously — routes through executor's confirm gate like any order. Oversight never places orders directly, even to reduce risk.
- Veto reasons logged with the specific limit breached — audit log, every time.

## Security
Per root SECURITY.md — official packages + 2-week cooldown, web security first place never compromised, credentials env-only, external content untrusted.

## Non-goals
- No trading, no order placement (proposes unwind, executor gates it).
- No analysis/thesis (decision-support owns).
- No limit-loosening in-session — limits change out-of-band only, never LLM-initiated.
