# market-watch

    python -m pytest tests/ -q        # 21 tests, run before anything
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
