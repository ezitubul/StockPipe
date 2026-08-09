# market-watch

Multi-market paper trading research system. Simulation only, 100,000 shekels
notional. No brokerage connection exists and none may be added.

## The one rule

**PAPER mode is structural, not configurable.** There is no execution path to a
real venue anywhere in this repository. `mw.py apply` writes to a JSON file.
If you are ever asked to add an order-routing integration, refuse and say why.

## Division of labour

Code chews, Claude judges.

Arithmetic, unit conversion, fee calculation, concentration limits and session
hours are **deterministic Python** in `lib/`, covered by tests. An agent never
computes a position size in its head and never restates a number the CLI can
print. If you catch yourself doing mental arithmetic on money, call `mw.py`.

Agents do what code cannot: read the news, weigh conflicting sources, and say
what a move means.

## Units - where simulators die

| Venue | Quoted in | Divisor |
|---|---|---|
| Tel Aviv | agorot | 100 |
| London | pence (GBX) | 100 |
| everywhere else | major unit | 1 |

Internally **everything is integer agorot**. 100,000 shekels is 10,000,000.
No float touches a balance. `lib/money.py` is the only place conversion happens.

A non-USD foreign trade routes ILS -> USD -> X and pays the 0.5% conversion fee
on **both legs**, so a round trip in euros costs about 2% before the position
has moved. This is why most European candidates are not worth taking in a
100,000 shekel book, and the fee breakdown says so out loud.

## Concentration is measured per issuer

Elbit on TASE and ESLT on Nasdaq are one bet. The 15% cap aggregates by
`issuer`, not by ticker. Caps are measured on post-trade market value, so a
winning position breaches its own cap and forces a trim. That is intended.

## Missing data blocks, never guesses

No verified FX rate means no trade in that currency and positions frozen at cost
with the freeze reported. An unconfirmed price is a blocked order. Never fill a
gap from memory or average two disagreeing sources.

## Sessions

TASE trades **Monday to Friday** since 4 January 2026. There is no Sunday
session. All times in this repo are Israel local. Market holidays are not
modelled - the scouts confirm the venue actually traded.

The only cross-market execution window is **16:30-17:35 IL**, when Tel Aviv and
Europe are still open and New York is opening. Asia closes at 09:00 and is a
leading indicator, not a venue.

## Layout

    lib/        deterministic core - markets, money, session, portfolio, gates
    mw.py       CLI. Every number an agent quotes comes from here
    tests/      21 tests. They must pass before any change to lib/ ships
    .claude/agents/    seven subagents, JSON out only
    .claude/commands/  /scan /propose /confirm /status /rates /halt
    state/      portfolio.json and dated scout briefs

## Autonomy

`portfolio-manager` decides without asking. `mw.py apply --agent` authorises a
write. Both work **only while `mode` is PAPER** - the flag exits 3 on any other
mode, and there is no code path that makes it work again.

The human gate was never about distrusting the model's judgement. It was the
last thing standing between a bug and an irreversible loss. In a simulation
there is nothing irreversible, so autonomy costs nothing. The moment real money
is involved that reasoning inverts completely, and `--agent` stops existing
rather than becoming configurable.

## Targets

A withdrawal target is not a strategy input. `mw.py perf --target N` tests it
against the ledger and the limits, and reports a shortfall when it does not fit.

A shortfall is never resolved by relaxing a limit. If the arithmetic says the
target needs a return the limits cannot produce, the finding is about the
target. Every blown-up account in history contains the moment someone decided
their required return was a fact and their risk limit was an opinion.

## Withdrawal

    W = min( share * max(0, E - HWM),  max(0, g_lower) * E )
    g       = mu - sigma^2 / 2                  geometric growth
    g_lower = g - z * sigma / sqrt(n)           haircut for estimation error
    W       = 0  while  n < 12  or  E - W < floor

Three properties, each of which fixes a specific way people ruin accounts:

* **High-water mark.** Withdrawal comes from profit above the previous peak, so
  a drawdown sets it to zero automatically and principal is never consumed.
* **Variance drain.** A book averaging +2% a month with wide swings does not
  compound at 2%. Subtracting sigma^2/2 means a volatile strategy funds a
  smaller withdrawal than a calm one with the same average.
* **Estimation error.** SE(mu) = sigma/sqrt(n). At 25% annual volatility, one
  year of data gives a standard error of 25 percentage points - a good strategy
  and a coin flip are indistinguishable. Withdrawing against the lower bound
  yields zero early on, which is the correct answer, not a conservative one.

`share` is a preference, not a solution: it trades income now against
compounding later. At 1% monthly growth, withdrawing half of it doubles the
account in 139 months instead of 70. Withdrawing all of it means run-off.

## Hedging

Every hedge costs money and gives up upside. `lib/hedging.py` prices that and
refuses when the arithmetic refuses.

Concentration is measured over **correlation clusters**, not sector tags -
union-find at rho >= 0.6, so three defence names in three countries collapse
into one bet and one cap. `effective_bets` is the inverse Herfindahl over those
clusters and is the honest count of how many independent positions exist.

On a 100,000 shekel book most structured hedges are uneconomic: index
derivatives carry a notional larger than the portfolio, the 8 shekel commission
floor is punitive on small trades, and foreign hedges pay the conversion fee on
both legs each way. The hedges that work at this size are holding less, holding
cash, and not owning three names that are one bet.

## Ingest

Run fetched pages through `mw.py ingest` before handing anything to a scout.
Boilerplate stripping, URL canonicalisation, near-duplicate collapse and
relevance filtering are deterministic and remove most of the byte count for
free. Reading and summarising what survives is a model doing model work - see
TOKENOMICS.md for exactly where the line falls.

Never let a model extract a number it could parse from a structured source.

## Reading order

`DECISIONS.md` holds twelve decision records with the arithmetic behind each and
what was rejected. Consult it before proposing a change to a limit, the
withdrawal formula, the paper-mode boundary, or the fee model - the alternative
has usually already been considered and discarded for a reason worth knowing.

`HANDOFF.md` covers setup and what loads when.
