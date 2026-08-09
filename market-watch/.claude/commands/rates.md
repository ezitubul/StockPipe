---
description: Refresh FX rates from a verified source
---
Run `macro-scout` and take only its `rates_vs_ils` block.

Apply with `python mw.py rates --set USD=... --set EUR=...`, then show me the
rate table alongside its sources.

Do not fill a currency the scout could not verify. A missing rate blocks trading
in that currency, which is correct; an invented rate corrupts the book silently.
