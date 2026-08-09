# Decision record

The code says what the system does. This file says why, and - more usefully -
what was considered and rejected, so that a later session does not spend a day
re-deriving an answer that was already reached and discarded.

Each entry: what was decided, the number that decided it, and what was rejected.

---

## D1 - Money is integer agorot, never a float

**Decided.** Every balance, price and fee is an integer number of agorot.
100,000 shekels is 10,000,000. Conversion happens in exactly one place,
`lib/money.py`, using `Decimal` and `ROUND_HALF_UP`.

**Why.** TASE quotes in agorot and the London Stock Exchange quotes in pence.
Both carry a divisor of 100. A correct number in the wrong unit is a
hundredfold error that every downstream calculation inherits silently, and it
is the single most common way a trading simulator produces confident nonsense.

**Rejected.** Floats with a shekel denomination. Rounding drift accumulates in
the ledger and there is no natural place to catch it.

**Guarded by** `test_lse_quote_is_pence_not_pounds`,
`test_tase_quote_is_agorot`.

---

## D2 - Concentration is capped per issuer, not per ticker

**Decided.** The 15% cap aggregates by `issuer`. Elbit on TASE and ESLT on
Nasdaq are one position.

**Why.** Two lines of the same company in two currencies look like
diversification to a ticker-level check and are a single bet on a single
balance sheet.

**Extended in D8** to correlation clusters, because the same failure recurs one
level up: three defence names in three countries are also one bet.

**Guarded by** `test_dual_listing_aggregates_to_one_issuer`.

---

## D3 - Caps are measured on post-trade market value

**Decided.** Limits are evaluated against current market value, not entry cost.

**Why.** A winning position therefore breaches its own cap and forces a trim.
This is the intended behaviour, not a bug to be smoothed over. Measuring
against cost lets a position grow to any size as long as it grows by winning,
which is exactly how concentrated blow-ups are built.

---

## D4 - Missing data blocks; it never gets filled in

**Decided.** No verified FX rate means no trade in that currency and positions
frozen at cost with the freeze reported. Two sources disagreeing by more than
1% returns `matched: false` and neither is used. Nothing is averaged and
nothing is recalled from memory.

**Why.** A blocked order costs one missed opportunity. An invented price
corrupts the ledger silently and every number computed from it afterwards.

**Rejected.** Seeding plausible default FX rates at install. Only USD was
seeded, because only USD was verified against a source.

---

## D5 - Autonomy exists only in simulation

**Decided.** `portfolio-manager` decides without asking, and
`mw.py apply --agent` authorises a write. The flag exits 3 unless `mode` is
`PAPER`, and there is no code path that re-enables it.

**Why.** The human gate was never about distrusting the model's judgement. It
was the last thing standing between a bug and an irreversible loss. In a
simulation nothing is irreversible, so autonomy is free. With real money that
reasoning inverts completely, so the flag stops existing rather than becoming
configurable.

**Rejected.** A `--force` escape hatch, and an "experienced user" setting. Both
are the same thing wearing different names, and the whole value of a structural
gate is that it has no override.

---

## D6 - The 10,000 shekel monthly target was rejected on arithmetic

**Decided.** `mw.py perf --target` reports feasibility, and
`portfolio-manager` is instructed to ignore an infeasible target entirely
rather than stretch toward it.

**The numbers.** On a 100,000 shekel book, 10,000 shekels a month net is 13,333
gross after 25% capital gains tax, which is **13.3% a month** and 349% a year.

A fixed withdrawal against a percentage return has a fixed point at `W/r`.
Below it the balance decays monotonically to zero however good the strategy is:

| annual return | capital that sustains 10k/month | months to zero from 100k |
|---|---|---|
| 8.7% | 1,433,000 | 11 |
| 12.7% | 999,000 | 11 |
| 20% | 653,000 | 11 |
| 40% | 352,000 | 12 |

Forty percent a year - an exceptional result - still empties the account inside
a year. The difference between a mediocre strategy and an excellent one is one
month, because the withdrawal, not the strategy, is what drains it.

Separately, the target contradicts the risk limits directly. A maximum position
is 15,000 shekels; at the +20% take-profit ceiling it contributes 3,000. The
target needs **4.4 fully-sized, fully-successful trades every month with no
losers**, which is not a strategy.

**The conclusion that matters.** 10,000 a month is a capital problem, not a
return problem. It needs roughly 1.2 to 1.5 million at a defensible rate.

**Rejected.** Raising the position cap to make the target reachable. Every
blown-up account contains the moment someone decided their required return was
a fact and their risk limit was an opinion.

---

## D7 - Withdrawal comes from profit above a high-water mark, capped by
demonstrated growth

**Decided.**

    W = min( share * max(0, E - HWM),  max(0, g_lower) * E )
    g       = mu - sigma^2 / 2
    g_lower = g - z * sigma / sqrt(n)
    W       = 0  while  n < 12  or  E - W < floor

**Why each term exists.**

*High-water mark* - withdrawal is zero during a drawdown automatically, so
principal is never consumed. This is the incentive-fee structure, and it is the
part that defeats the ruin dynamic in D6.

*Variance drain* `-sigma^2/2` - a book averaging +2% a month with wide swings
does not compound at 2%. The gap is real money and it is invisible in an
average, so a volatile strategy funds a smaller withdrawal than a calm one with
the same mean.

*Estimation error* `-z*sigma/sqrt(n)` - the term nobody implements. At 25%
annual volatility, one year of data gives a standard error on the mean of 25
percentage points; a good strategy and a coin flip are indistinguishable.
Withdrawing against the lower bound yields zero early on. **That is the correct
answer, not a conservative one.**

*share* is a preference, not a solution. At 1% monthly growth, taking half
doubles the account in 139 months instead of 70; taking all of it is run-off.
Maximum profit and withdrawal are the same variable with opposite signs.

---

## D8 - Risk is measured over correlation clusters, not sector tags

**Decided.** Union-find over the correlation matrix at rho >= 0.6.
`effective_bets` is the inverse Herfindahl over the resulting clusters.

**Why.** Elbit, Rheinmetall and AeroVironment carry three sector labels, three
countries and three currencies, and they are one bet on defence budgets. A
sector tag is a human guess; correlation is the measurable thing. A book of
eight names with two effective bets is concentrated in disguise.

---

## D9 - Most structured hedges are rejected at this book size

**Decided.** `hedge_economics` refuses any hedge costing more than 2% of what
it protects, and `beta_hedge` refuses when the smallest tradeable unit exceeds
the exposure.

**Why.** A Maof index option or future carries a notional larger than the whole
portfolio, so one unit does not hedge the position - it replaces it with a
larger opposite one. The 8 shekel commission floor is punitive on small
protective trades. A foreign hedge pays the conversion fee on both legs each
way, about 2% round trip, before the hedge has done anything.

**What replaces it.** Holding less of the thing, holding more cash, and not
owning three names that are one bet. These are free and they achieve the same
risk reduction. `risk-manager` is instructed to say this plainly rather than
engineer a structure that sounds prudent.

---

## D10 - Non-USD foreign trades pay the conversion fee twice per direction

**Decided.** `fx_legs` returns 2 for any currency other than ILS or USD.

**Why.** The route is ILS -> USD -> X. A euro round trip costs about 2% in
conversion alone. This is why most European candidates do not survive contact
with the fee model on a five-figure book, and the ticket says so out loud
rather than burying it.

---

## D11 - TASE trades Monday to Friday

**Decided.** Since 4 January 2026 there is no Sunday session. Weekday hours are
10:00-17:35 Israel local.

**Why it is written down.** Pre-2026 sources still describe a Sunday-Thursday
week, and a model recalling this from training data will get it wrong. The
scouts are instructed to flag a source implying a Sunday close as stale.

The only cross-market execution window is 16:30-17:35 Israel time, when Tel
Aviv and Europe are still open and New York is opening. Asia closes at 09:00
and is a leading indicator, not a venue.

---

## D12 - In CI, the job that reads the web and the job that writes the ledger
are never the same job

**Decided.** `scan` has read permissions and a model. `execute` has write
permissions and no model, behind a GitHub environment with a required reviewer.

**Why.** Scouts read the open web, which is hostile input. Locally, a poisoned
page produces a bad line in a JSON brief. In CI the same scout runs in a
container holding an API key and possibly a write-scoped token, so injection
gains a path to a secret and to the repository. Neither job has both
capabilities, and merging them is the one change that must never be made.

**Also decided.** Actions cron is UTC only and Israel observes DST, so fire
times drift by an hour twice a year and GitHub delays scheduled runs under
load. `mw.py clock --require` aborts cheaply instead of the schedule pretending
to be precise. Never build a stop-loss around a CI schedule.

---

## D13 - Retrieval is deterministic, comprehension is not, and the docs say so

**Decided.** `lib/ingest.py` performs URL canonicalisation, boilerplate
stripping, near-duplicate collapse, relevance filtering and caching before any
page reaches a context window. Reading and summarising the survivors remains a
model job and is described as one.

**Why the distinction is written down.** "Code chews, Claude judges" is easy to
read as a claim that the whole retrieval-and-summarise pipeline is external. It
is not. The fetch is a network call; everything after it - deciding what the
page means, compressing it into the brief schema - happens inside a model with
the page body in its context. Overstating this leads to sizing the token budget
for a pipeline that does not exist.

**What the deterministic pass actually buys.** On a realistic scan, roughly
three quarters of the bytes never reach a model: navigation and script chrome,
one wire story reprinted by five outlets, and articles matching nothing in the
universe. That is a genuine saving and it is bounded and measurable, which is
why `prepare` reports `tokens_before`, `tokens_after` and `reduction` rather
than asserting an improvement.

**Rejected.** Shingle simhash as the dedup comparator. Simhash exists to make
comparison O(1) across millions of documents; a scan handles a few dozen, where
exact shingle Jaccard is both cheap and materially more accurate on short text.
Simhash is retained only for a cross-session seen-set.

**Rejected.** `trafilatura` and `readability-lxml`, which strip boilerplate
better than the stdlib parser here. This module handles hostile input from the
open web, so every dependency is a supply-chain surface facing it directly. If
one is added later, pin it and let it age first.

**Guarded by** `test_boilerplate_is_removed_before_any_model_sees_it`,
`test_one_wire_story_across_outlets_counts_once`,
`test_irrelevant_articles_never_reach_a_context`.
