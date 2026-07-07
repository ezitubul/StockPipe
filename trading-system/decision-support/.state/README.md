# decision-support/.state — local subtree state

Working state for this subtree's `.claude/agents/ds-*` subagents (the vertical-
slice implementation of `decision-support/agents/fetch-agent.md` and
`valuation-agent.md`). Written and read by `ds-fetch-agent`; nothing here is
committed to git except this README — see `.gitignore`.

## Layout
- `schema-hashes/tase.json` — per-endpoint canonical field-name signature (sorted,
  comma-joined field names — **not a cryptographic hash**; a subagent can't
  reliably compute one, and this is a deliberate substitution for the spec's
  literal word "hash" in `schemas/README.md`. Functionally equivalent for the
  actual goal, change-detection.). First fetch of an endpoint seeds
  `status: "bootstrap"`; a matching subsequent fetch flips it to `"confirmed"`.
- `cache/tase/<TICKER>.json` — per-ticker record, fields shaped per
  `decision-support/agents/schemas/tase.md`, each tagged `value | source |
  fetched_at`, plus `confirmation_status` and `session_state_at_fetch`.
- `cache/tase/calendar.json` — cached TASE session state per
  `decision-support/agents/schemas/calendar.md`.
- `fetch-log.jsonl` — append-only local event log for this subtree's fetch
  activity only (`cache_hit` / `network_fetch` / `schema_mismatch` / etc.).

## Not the global audit log
This is **not** `trading-system/CLAUDE.md`'s hash-chained, append-only global
audit log (the `Global state` section — `seq`, `entry_hash`, `prev_entry_hash`,
etc.). That log is owned by the top orchestrator and will live at a sibling path
under `trading-system/.state/` when built, covering all three subtrees
(analysis emitted, veto, confirm, order, fill...). This directory is a local,
subtree-scoped precursor for the fetch-agent → valuation-agent slice only — when
the global audit log exists, `fetch-log.jsonl`'s events should be reconciled
into it, not treated as a second permanent audit trail.

## Deliberately deferred (not built by this slice)
- Top-level hash-chained audit log, portfolio state, risk limits, kill-switch.
- `boi.md` / `cbs.md` / `edgar.md` / `isa.md` caches — only `tase.md` (+
  `calendar.md` as a freshness dependency) is touched by this slice.
- Corporate-action-triggered forced refetch — the rule is stated in
  `ds-fetch-agent.md` but isn't exercised unless the test ticker happens to have
  a pending action.
- DuckDB migration (named as an alternative in `decision-support/CLAUDE.md`) —
  flat JSON is the right call at N=1 ticker.

## Derived-implementation note
`.claude/agents/ds-*.md` is a trimmed, functional translation of the canonical
spec files under `decision-support/agents/`. The spec files remain the design
source of truth; if they diverge from the subagent files, the spec wins and the
subagent files should be updated to match — not the other way around. When
`audit-agent` is built out, it should periodically diff spec vs. implementation
for drift, per the same principle it already applies to prompt-output drift.
