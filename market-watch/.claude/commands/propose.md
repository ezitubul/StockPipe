---
description: Turn one watchlist candidate into a gated order proposal
---
Argument: the candidate symbol.

1. Run `price-verifier` on it. If `matched` is false, stop and tell me why.
2. Size the position: never more than 15% of equity on the issuer, and respect
   the market's lot size. Show the arithmetic.
3. Write `state/pending-order.json`:
   {"side","symbol","issuer","market","sector","qty","px","tp","sl",
    "catalyst","rationale","sources":[]}
4. Run `python mw.py gates --order state/pending-order.json`.

Show me every gate with its verdict, the full fee breakdown in shekels, and the
cash before and after. If any gate failed, say which and stop - do not rewrite
the order to squeeze past a limit. A blocked order is the system working.

Never run `mw.py apply`. That is `/confirm`, and it is mine.
