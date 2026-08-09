---
paths:
  - lib/money.py
  - lib/markets.py
  - lib/portfolio.py
  - "**/*portfolio*.jsx"
---
# Units

Integer agorot everywhere. 100,000 shekels is 10,000,000. No float reaches a
balance. Conversion happens only in `lib/money.py`.

TASE quotes in agorot, LSE in pence; both divide by 100. A correct number in
the wrong unit is a hundredfold error inherited silently by everything
downstream.

Non-USD foreign trades route ILS -> USD -> X and pay the conversion fee on both
legs, so a euro round trip costs about 2% before the position moves.

Changing anything here without a matching test is not allowed. See D1 and D10
in DECISIONS.md.
