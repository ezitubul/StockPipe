# StockPipe

Two independent, PAPER-only trading research systems for Claude Code. Neither connects to a real brokerage.

- **`market-watch/`** — multi-market (TASE/US/Europe/Asia) ₪100,000 simulation. Deterministic Python core (`lib/`, tested), a CLI (`mw.py`), real Claude Code subagents/commands, and GitHub Actions CI. Autonomous in PAPER mode — see `market-watch/README.md` and `market-watch/CLAUDE.md`.
- **`trading-system/`** — a three-subtree agent hierarchy (decision-support / risk-oversight / executor) built around a structural, always-on human confirm gate before any order, PAPER or (out-of-band, never in-session) live. See `trading-system/README.md`.

Run Claude Code from inside whichever subtree you're working in — each has its own `CLAUDE.md`.
