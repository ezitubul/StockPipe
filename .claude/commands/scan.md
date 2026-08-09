---
description: Run a full multi-market scan and produce a ranked watchlist
---
Run `python mw.py clock` and `python mw.py status` first. Both are cheap and
tell you which venues are live and what the book already holds.

Dispatch in two waves. Wave one is `macro-scout` alone - it sets the regime and
supplies the FX rates everything else depends on. Wave two is the regional
scouts in parallel, chosen by what the clock reported:

  before 09:00 IL  -> asia-scout
  10:00-17:35 IL   -> israel-scout, europe-scout
  16:30-23:00 IL   -> us-scout
  after 23:00 IL   -> us-scout for the close

Write each brief to `state/briefs/<region>-<date>.json`. Feed the file paths -
not the contents - to `synthesizer`.

Then apply the macro brief's FX rates with `mw.py rates --set USD=... --set ...`
so foreign valuations stop being frozen.

Report to me: the regime in two sentences, the ranked candidates with their
catalysts and counter-cases, and anything the scouts could not verify. Do not
propose an order in this command.
