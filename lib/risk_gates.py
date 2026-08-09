"""Hard limits. Code decides, Claude never argues with the verdict.

Position cap is measured PER ISSUER, not per ticker: Elbit on TASE and ESLT on
Nasdaq are one bet. Caps are measured on post-trade market value, so a winning
position breaches its own cap and forces a trim.
"""
from dataclasses import dataclass, asdict

from .markets import market
from .money import MissingRate, price_trade, to_agorot
from .portfolio import RED_FLAG_AG, find, value
from .session import is_open

MAX_ISSUER = 0.15
MAX_SECTOR = 0.35
MIN_CASH = 0.20
MIN_SOURCES = 2


@dataclass
class Gate:
    name: str
    ok: bool
    detail: str = ""


def evaluate(state: dict, order: dict, when=None) -> tuple[bool, list, dict]:
    """Returns (passed, gates, quote). Never raises on user input."""
    gates, quote = [], None
    m = market(order["market"])
    v = value(state)
    sell = order["side"] == "SELL"

    gates.append(Gate("mode", state.get("mode") == "PAPER", state.get("mode", "?")))
    gates.append(Gate("fx_rate", bool(state["rates"].get(m.ccy)),
                      f'{m.ccy}={state["rates"].get(m.ccy) or "MISSING"}'))
    gates.append(Gate("market_open", is_open(order["market"], when),
                      f"{m.code} {m.open}-{m.close} IL"))
    gates.append(Gate("not_halted", not v["halted"] or sell,
                      f'equity {v["equity_ag"]/100:,.0f} vs floor {RED_FLAG_AG/100:,.0f}'))
    gates.append(Gate("sources", len(order.get("sources") or []) >= MIN_SOURCES,
                      f'{len(order.get("sources") or [])}/{MIN_SOURCES}'))
    gates.append(Gate("catalyst", len((order.get("catalyst") or "").strip()) > 5))
    gates.append(Gate("rationale", len((order.get("rationale") or "").strip()) > 15))

    try:
        quote = price_trade(order["side"], order["qty"], order["px"],
                            order["market"], state["rates"])
    except (MissingRate, ValueError) as e:
        gates.append(Gate("pricing", False, str(e)))
        return False, [asdict(g) for g in gates], None
    gates.append(Gate("pricing", True, f'net {quote["net_ag"]/100:,.2f}'))

    pos = find(state, order["symbol"], order["market"])
    if sell:
        gates.append(Gate("qty_held", bool(pos) and order["qty"] <= pos["qty"],
                          f'{order["qty"]} vs {pos["qty"] if pos else 0}'))
    else:
        gates.append(Gate("cash_sufficient", state["cash_ag"] - quote["net_ag"] >= 0))

        delta = quote["gross_ag"]
        line = (pos["qty"] if pos else 0) * quote["unit_ag"] + delta
        others = [r for r in v["rows"]
                  if not (r["symbol"] == order["symbol"].upper() and r["market"] == order["market"])]
        issuer = (order.get("issuer") or order["symbol"]).upper()
        issuer_mv = sum(r["mv_ag"] for r in others if r["issuer"].upper() == issuer) + line
        sector_mv = sum(r["mv_ag"] for r in others if r["sector"] == order["sector"]) + line
        cash_after = state["cash_ag"] - quote["net_ag"]
        equity_after = cash_after + sum(r["mv_ag"] for r in others) + line

        gates.append(Gate("issuer_cap", issuer_mv / equity_after <= MAX_ISSUER,
                          f'{issuer} {issuer_mv/equity_after:.1%} <= {MAX_ISSUER:.0%}'))
        gates.append(Gate("sector_cap", sector_mv / equity_after <= MAX_SECTOR,
                          f'{sector_mv/equity_after:.1%} <= {MAX_SECTOR:.0%}'))
        gates.append(Gate("cash_floor", cash_after / equity_after >= MIN_CASH,
                          f'{cash_after/equity_after:.1%} >= {MIN_CASH:.0%}'))

    return all(g.ok for g in gates), [asdict(g) for g in gates], quote
