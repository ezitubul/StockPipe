# Expected TASE trading calendar response fields
# Validation rule: see README.md

## Trading week
Sunday–Thursday. Friday and Saturday are always non-trading (Shabbat) — distinct from the Western Monday–Friday week; do not default to it.

## Session structure
Pre-open/opening auction → continuous trading → closing auction. Exact clock times are sourced from TASE's official calendar/circular, not hardcoded here — TASE has changed session hours before.

## Holiday source of truth
TASE's official published annual trading calendar (holiday eves = early close, full holidays = closed). Fetched/cached the same way as other sources, not computed independently from a generic Israeli-holiday list.

## Calendar endpoint
- `date, is_trading_day, session_type (full/early_close/closed), open_time, close_time, holiday_name`

## Cache/refresh rule
Mostly static per calendar year — periodic refresh (e.g. daily check) is sufficient, with override on any TASE circular announcing an ad hoc closure or hours change, same cache-override pattern fetch-agent already uses for corporate actions.

## Explicit non-goals
- No intraday circuit-breaker prediction (that's risk-agent's liquidity-check territory).
- No timezone conversion logic beyond stating the source is Israel local time.
