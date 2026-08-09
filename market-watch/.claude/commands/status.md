---
description: Portfolio status with stop-loss and take-profit alerts
---
Run `python mw.py status` and `python mw.py clock`.

Report equity, cash percentage, and every position with its weight and P&L.

Flag loudly:
  * any position past its take-profit or stop-loss band
  * any price older than 24 hours - a stop cannot trigger on a stale mark
  * any currency in `missing_rates` that a held position depends on
  * equity below the 70,000 shekel floor

Do not propose trades here. Report only.
