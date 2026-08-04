# Virtual Portfolio Simulator

A standalone subtree of `trading-system/` that runs a fully autonomous, ₪100,000 **paper** portfolio for research/track-record purposes — no real money, no brokerage connection.

## Why it's separate from `executor/`
The rest of `trading-system` gates every order on human confirmation because it assumes a path to real capital risk (even in PAPER mode, it's built to be flipped to LIVE out-of-band). This simulator has no such path — there's no broker, no live write-back — so it's allowed to place its own simulated fills via `execute_virtual_trade` without a confirm step. See `CLAUDE.md` for the full boundary rationale.

## Structure
```
virtual-portfolio-simulator/
├── CLAUDE.md            persona: routine, decision process, risk rules, fees,
│                         execute_virtual_trade contract, controls
├── eval-checklist.md    boundary tests (risk limits, sourcing, reconciliation, red flag)
└── state/
    ├── portfolio.json    current cash / positions / portfolio value / risk flag
    └── trade-log.jsonl   append-only trade ledger, one JSON object per trade
```

## Routine
Three scans per trading day (Israel time): 09:30, 13:00, 17:30. Each scan checks existing positions against take-profit (+15%/+20%) and stop-loss (-10%) triggers, reviews market/news/macro inputs, and executes a new trade only when it clears the decision process (≥2 corroborating signals + a concrete catalyst).

## Risk rules
Max 15% per position, max 35% per sector, min 20% cash at all times. Commission: 0.15% of notional (min ₪8). FX conversion: 0.5% of ILS notional for non-ILS instruments. Portfolio value below ₪70,000 halts new-entry trading (a red flag) — stop-loss exits remain active.

## What it doesn't do
No real money, no personal financial advice, no fabricated prices or news, no personal data collection.

Not a licensed investment advisor. Simulation output only.
