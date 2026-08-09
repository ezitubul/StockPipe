# Handoff

    tar xzf market-watch.tgz && cd market-watch
    git init && git add -A && git commit -m "market-watch: paper trading research system"
    python -m pytest tests/ -q      # 38 tests - run this first, always
    claude

## Do not run /init

It regenerates `CLAUDE.md` from the codebase and will overwrite a file that
encodes decisions the code cannot express. If `CLAUDE.md` ever needs
restructuring, edit it directly or use `/memory`.

## What loads, and when

| File | When |
|---|---|
| `CLAUDE.md` | every session, and re-read from disk after `/compact` |
| `.claude/rules/*.md` | only when touching files matching their `paths` |
| `DECISIONS.md` | on demand - point Claude at it when a design question arises |
| `.claude/agents/*.md` | when the agent is invoked |

Keep `CLAUDE.md` under 200 lines. Past that, adherence drops and the file starts
competing with itself. Detail belongs in a path-scoped rule, which loads only
when relevant - `@path` imports do not save context, they load at launch just
the same.

## What actually carries the reasoning

**`DECISIONS.md` is the important file in this repository.** The code says what
the system does; that file says what was rejected and why, which is the part a
fresh session cannot re-derive and will otherwise re-propose. Twelve entries,
each with the number that decided it.

**The tests are the thesis in executable form.** Read the names:

    test_lse_quote_is_pence_not_pounds
    test_dual_listing_aggregates_to_one_issuer
    test_ten_thousand_a_month_on_a_hundred_thousand_is_infeasible
    test_volatile_book_withdraws_less_than_a_calm_one
    test_index_hedge_is_too_coarse_for_a_small_book
    test_correlated_names_collapse_into_one_cluster

Each is a claim about how markets and arithmetic work, and each fails loudly if
someone later disagrees with it in code. A rule in prose can be argued around; a
failing test cannot.

**Git history is the durable memory.** Commit with reasons rather than
summaries. `raise issuer cap to 25%` invites the question the message should
have answered.

## First session in Claude Code

Ask for a read-only orientation before anything else:

    Read CLAUDE.md and DECISIONS.md, run the tests, and run
    `mw.py status`, `mw.py clock`, `mw.py perf --target 10000`.
    Tell me what this system refuses to do and why. Change nothing.

If the answer does not mention the paper-mode boundary and the infeasible
target, the context did not land and it is worth fixing before working.

## What is still open

* Scheduling: GitHub Actions cron drives it end to end now - `scan` then
  `decide` (D14) - but there's no cron or launchd unit for a self-hosted
  alternative, and Actions cron is not punctual - see D12. **This wiring is
  new and has not yet run against a live schedule; dispatch `scan.yml`
  manually (`workflow_dispatch`) and read the run's logs before trusting the
  cron.** Needs an Anthropic API key in a secret named `claude_key`
  (`.github/workflows/scan.yml` reads `secrets.claude_key`) or the scheduled
  runs simply fail at the `claude-code-action` step. If it's an *environment*
  secret rather than a plain repository secret, the `scan`/`decide` jobs also
  need `environment: <name>` added, or GitHub won't expose it to them.
* No live track record exists. `mw.py withdraw` correctly returns zero and will
  keep returning zero until twelve months of real paper history exist. The
  `decide` job now gives that history a chance to actually accumulate instead
  of stopping at an unread brief each run.
* Correlations for the *scheduled* `decide` job are the model's own estimate
  (there's no human to hand `mw.py risk --corr` values to) - treat its risk
  read as a lower-confidence pass compared to an interactive session, and
  weight `calibration`'s monthly review accordingly.

## Subagents

Ten files in `.claude/agents/`, discovered automatically at session start - a
new one needs a restart to appear. `description` is what drives delegation, so
it is written as a routing signal rather than a label.

| Agent | Tools | Model | CLAUDE.md |
|---|---|---|---|
| macro-scout | WebSearch, WebFetch | sonnet | skipped |
| asia / europe / us / israel-scout | WebSearch, WebFetch | haiku | skipped |
| price-verifier | WebSearch, WebFetch | haiku | skipped |
| synthesizer | Read | sonnet | skipped |
| risk-manager | Read, Bash | sonnet | loaded |
| portfolio-manager | Read, Write, Bash | sonnet | loaded |
| calibration | Read, Bash | sonnet | loaded |

The split is the security boundary. Everything that reads the open web has
`WebSearch, WebFetch` and nothing else - no `Bash`, no `Write`, no `Agent`. A
poisoned page cannot reach the ledger, cannot spawn anything, and cannot do
better than write a bad line into a JSON brief that the gates will still block.

Everything that touches the ledger never reads the web.

`tools` is an allowlist of tool names and does not accept command patterns.
Scoping `Bash` is done in `.claude/settings.json`, which denies writes to
`lib/` and `.claude/` - an agent may move the ledger but not rewrite its own
limits or subagent definitions.

**`git push` is a live open question, not settled policy.** `.claude/` used
to live under `market-watch/`, a directory `claude-code-action` never
discovered from the checkout root - so `.claude/settings.json`'s permissions
were local-session-only in practice, and denying `git push` there cost
nothing for CI. Now that `.claude/` sits at the true repo root, the action
likely auto-discovers it for every job, including `scan.decide`, which needs
`git push` to do its one job (D14) - and `deny` rules generally beat `allow`
elsewhere, so a blanket local deny would probably break it silently. The fix
(dropping `Bash(git push:*)` from `deny`, since each job's own
`--allowedTools` is the real, reviewable control - `scan` never gets it,
`decide` does on purpose) needs a human's go-ahead before it lands, because
loosening a denylist is exactly the kind of edit that shouldn't happen on
autopilot. Check `.claude/settings.json`'s current `deny` list against this
paragraph before trusting `scan.decide` to actually commit anything.
