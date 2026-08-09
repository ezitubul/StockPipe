---
paths:
  - lib/risk_gates.py
  - lib/hedging.py
  - lib/withdrawal.py
  - state/pending-order.json
---
# Limits

The constants in `risk_gates.py` are not tuning parameters. If a limit blocks a
trade, the answer is a smaller trade or no trade.

Never resize an order specifically to slip past a limit it just failed. Never
edit a constant to accommodate a thesis or a return target. Both are the moment
the limits become decorative.

Caps are measured on post-trade market value, so a winning position breaches its
own cap and forces a trim. That is intended.

Concentration aggregates by issuer, and above that by correlation cluster at
rho >= 0.6. Sector tags are a human guess; correlation is measurable.

See D2, D3, D6, D8 in DECISIONS.md.
