# StockPipe

## market-watch — the active project

`market-watch/` is a multi-market (TASE/US/Europe/Asia) ₪100,000 PAPER trading
research system: deterministic, tested Python core (`lib/`) for money/session/
risk math, a real CLI (`mw.py`), genuine Claude Code subagents and slash
commands, and GitHub Actions CI. No brokerage connection exists or may be
added — `mw.py apply` writes a JSON file, nothing more.

Start here: `market-watch/README.md` (quickstart), `market-watch/CLAUDE.md`
(design), `market-watch/DECISIONS.md` (why, and what was rejected).

## trading-system — earlier design, kept for reference

`trading-system/` is a three-subtree agent hierarchy (decision-support /
risk-oversight / executor) built around a structural, always-on human confirm
gate before any order. It predates `market-watch` and is not under active
development; `market-watch/README.md` explains how the two differ in their
autonomy model. See `trading-system/README.md`.

Run Claude Code from inside whichever project you're working in — each has
its own `CLAUDE.md`.
