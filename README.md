# market-watch

    python -m pytest tests/ -q        # 39 tests, run before anything
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
rather than reckless. Requires an Anthropic API key in a repository secret
named `CLAUDE_APIKEY` (Settings -> Secrets and variables -> Actions ->
Repository secrets - not an environment secret, which needs `environment:`
added to every job that reads it, including scheduled ones). Also needs
`id-token: write` in the workflow's permissions - `claude-code-action`
fetches a GitHub OIDC token as part of its own setup even when an explicit
API key is supplied, and hard-fails without it. Both were found by actually
dispatching the workflow and reading the failure, not by inspection -
dispatch it yourself (`workflow_dispatch`) after any change here and read
the run before trusting the cron. Beyond the workflow itself, the Anthropic
account behind `CLAUDE_APIKEY` needs a positive credit balance
(console.anthropic.com -> Billing) - a real API call fails with
`billing_error: Credit balance is too low` otherwise, distinguishable from
every config problem above by getting all the way to a genuine model call
before failing.

The manual path (`/propose` then `/confirm`, or `execute.yml` dispatched by
hand behind a required reviewer) still exists for anything you want to decide
yourself instead.
