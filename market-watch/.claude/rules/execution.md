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

In CI the job that reads the web and the job that writes the ledger are never
the same job. `scan` gets read permissions and a model; `execute` gets write
permissions and no model, behind a required reviewer. Never merge them and never
add `Bash(python mw.py apply:*)` to the scan allowlist.

See D5 and D12 in DECISIONS.md.
