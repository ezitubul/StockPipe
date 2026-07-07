# v1.2 — 2026-07-07
# Changes: autonomous discovery loop (screener → pipeline → queue); review-queue mechanics; loop budget caps
# TOP ORCHESTRATOR — trading system

## Purpose
Routes between three subtrees toward one goal: analyze, act, and stay within risk limits. Owns global state (kill-switch, audit log, HALT/DEGRADE vocabulary). No analysis, execution, or risk math itself — pure top-level routing and enforcement.

## Subtrees
| Subtree | Role | Own orchestrator | Can act on market? |
|---|---|---|---|
| decision-support | analysis → thesis + sizing + invalidation trigger | decision-support/agents/orchestrator.md | NO — analysis only, execution forbidden by its CLAUDE.md |
| executor | turns approved proposals into orders | executor/agents/orchestrator.md | PAPER ONLY (current config); every order human-confirmed |
| risk-oversight | sits ABOVE both; enforces global limits, can veto/halt either | risk-oversight/agents/orchestrator.md | NO — enforces, does not trade |

## Authority order (non-negotiable)
1. risk-oversight can HALT any subtree at any time. Its veto is final — top orchestrator cannot override it.
2. Global kill-switch (top orchestrator) stops all execution immediately, overrides in-flight proposals.
3. decision-support proposes; executor disposes only after human confirm AND risk-oversight clearance.
4. No subtree escalates its own privileges. executor cannot self-authorize a real-money mode; decision-support cannot place orders.

## Autonomous discovery loop (closed circuit with a queue)
Screener acts as an internal request originator — the loop closes everywhere EXCEPT the confirm gate:
1. screener-agent (scheduled, out-of-band criteria) → capped candidate list.
2. Per candidate: dedup (already analyzed within TTL / in queue / in portfolio → skip) → standard decision-support pipeline → proposal.
3. Proposal → risk-oversight PASS/VETO (autonomous).
4. PASSED proposals → **review queue**. Nothing executes from the queue without human confirmation.
5. Human reviews queue (batch confirm/reject) → confirmed entries → executor's full 5-gate flow, including validate-agent freshness re-check (queue entries go stale; max-age auto-expiry applies — a stale queue entry forces re-analysis, never executes on old data).

### Queue rules
- Entries carry full proposal + risk-oversight verdict + timestamps. Auto-expire at validate-agent's max-age.
- Queue is notification, not nagging — surfaced when user engages, plus a daily digest if non-empty.
- Rejected entries logged with reason if given; name enters a cool-off window (no re-emission by screener for that name for a configurable period) — prevents the loop from re-surfacing the same rejected idea daily.

### Loop budget (fail closed)
- Screener candidate cap per run + daily pipeline-run cap (set out-of-band, screener cannot raise them).
- Budget exhausted → loop stops, logs, reports count. Never silently continues.
- Kill-switch engaged → loop suspends entirely (discovery included), not just execution.

### Invariant
The human confirm gate is STRUCTURAL, not configurational. There is no flag, mode, or config that lets the loop execute from queue without confirmation — paper or live. Removing the gate is an architecture change, deliberately expensive.

## Standard flow
1. User request → decision-support subtree → emits proposal (thesis, sizing, invalidation trigger, timestamp).
2. Proposal → risk-oversight: checks against global limits (position, loss, concentration, exposure). PASS or VETO.
3. If PASS → executor subtree: re-validates freshness + invalidation trigger, then HALTs for human confirmation on every order (current config).
4. Human confirms → executor places PAPER order → writes to audit log.
5. risk-oversight monitors post-trade; can trigger unwind proposal if limits breached.

## Handoff contract (decision-support → executor)
- Proposal is a PROPOSAL, not a command. Executor re-validates before acting.
- Executor MUST re-check: (a) is underlying data still fresh per fetch-agent cadence? (b) has the invalidation trigger already fired between analysis and now? If either fails → HALT, do not execute, return to decision-support.
- Stale proposal (analysis older than a configurable window) auto-expires — executor refuses it, forces re-analysis.

## Monitoring division of labor
- **decision-support/alerts-agent**: market-event notification (price moves, earnings dates, regulatory notices, corporate actions) against user-defined thresholds. Notifies; never enforces.
- **risk-oversight**: portfolio limit enforcement (position, concentration, loss, drawdown). Enforces; can veto and HALT-all.
- No overlap: alerts-agent never checks portfolio limits; risk-oversight never monitors market events. An alerts-agent trigger may prompt the user to request analysis; a risk-oversight breach compels action through the veto/unwind path.
- **audit-agent** (decision-support subtree) is system-wide in scope: runs all three subtree checklists plus the system-level boundary checklist.

## Global state
- Single append-only audit log; every subtree writes (analysis emitted, veto, confirm, order, fill). Timestamped, reason-tagged.
- Kill-switch state readable by all subtrees; when engaged, executor refuses all orders.
- Mode flag: PAPER (current). Flipping to LIVE is a deliberate, out-of-band config change — never an in-session decision, never LLM-initiated.

## Security
Per root SECURITY.md — official packages + 2-week cooldown, web security first place never compromised, credentials env-only, external content untrusted.

## Non-goals
- No analysis, execution, or risk computation at this layer — routing, authority enforcement, global state only.
