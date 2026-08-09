---
paths:
  - mw.py
  - .github/workflows/**
  - .claude/commands/confirm.md
---
# Execution boundary

`--agent` authorises a ledger write only while `mode` is PAPER, and exits 3
otherwise. Do not add a `--force`, an override, or an "experienced user"
setting. A structural gate is worth exactly as much as its lack of an override.

In CI, no job may hold both web access and a write-scoped token. `scan.scan`
gets read permissions, a model, and `WebSearch`/`WebFetch` - nothing that
writes. `scan.decide` gets write permissions and a model but no web tools - it
runs the full decision pipeline unattended and applies through the gates with
no human confirmation (D5, D14), reading only the briefs `scan.scan` already
produced. `execute` gets write permissions and no model at all, behind a
required reviewer, for the manual `/propose`+`/confirm` path. Never add
`WebSearch`/`WebFetch` to `scan.decide` or `execute`, and never add
`Bash(python mw.py apply:*)` to `scan.scan`.

See D5, D12 and D14 in DECISIONS.md.
