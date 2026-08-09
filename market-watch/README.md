# market-watch

    python -m pytest tests/ -q        # 38 tests, run before anything
    python mw.py clock                # which venues are live right now
    python mw.py status               # the book
    python mw.py rates --set USD=3.01 # a rate you verified

Then, inside Claude Code:

    /scan       macro + regional scouts -> ranked watchlist
    /propose    one candidate -> priced, gated order proposal
    /confirm    execute, after you approve in writing
    /status     positions with stop and target alerts
    /rates      refresh FX from a verified source
    /halt       stop trading

Read `CLAUDE.md` first. The units section is not optional reading.

## Scheduled and unattended

`.github/workflows/scan.yml` runs the whole thing on a cron (weekday windows
around Asia close, TASE/EU midday, the TASE+EU+NY overlap, and the NY close):
`scan` reads the news and writes briefs, `decide` reads only those briefs
(never the open web) and applies through `lib/risk_gates.py` with no human
confirmation - see the Autonomy section in `CLAUDE.md` and D5/D12/D14 in
`DECISIONS.md` for why that split is what makes unattended operation safe
rather than reckless. Requires `ANTHROPIC_API_KEY` as a repository secret.
This wiring is new - dispatch it manually once (`workflow_dispatch`) and read
the run before trusting the cron.

The manual path (`/propose` then `/confirm`, or `execute.yml` dispatched by
hand behind a required reviewer) still exists for anything you want to decide
yourself instead.
