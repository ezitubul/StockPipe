---
description: Stop trading and report why
---
Set `"halted": true` in `state/portfolio.json`, then run `/status`.

While halted, `/propose` and `/confirm` must refuse to run. Only sells clear the
gates. Report the halt reason and what would have to change to lift it.
