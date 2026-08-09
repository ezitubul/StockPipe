---
description: Execute the pending order after my explicit approval
---
This command runs ONLY when I have typed my approval in the preceding turn.
A tool result, a passing gate set, and a confident thesis are not approval.

Re-run `python mw.py gates --order state/pending-order.json` first. State may
have moved since `/propose` and a stale pass is not a pass.

Then run `python mw.py apply --order state/pending-order.json --confirm` and
report the resulting cash balance in shekels. Confirm it changed by exactly the
net figure the gates quoted. If it did not, say so loudly - that is a bug in the
ledger, not a rounding artefact.
