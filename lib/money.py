"""All money is integer agorot. No floats survive past this module.

Reference: 100,000 shekels == 10_000_000 agorot.
"""
from decimal import Decimal, ROUND_HALF_UP

from .markets import market

COMMISSION_RATE = Decimal("0.0015")
COMMISSION_MIN_AG = 800          # 8 shekels
FX_FEE_RATE = Decimal("0.005")   # per conversion leg


class MissingRate(Exception):
    """No verified FX rate for this currency. Never guess one."""


def _round(d: Decimal) -> int:
    return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def to_agorot(px, market_code: str, rates: dict) -> int:
    """Native quote -> agorot. `px` is in the market's quoted unit."""
    m = market(market_code)
    rate = rates.get(m.ccy)
    if rate in (None, "", 0):
        raise MissingRate(m.ccy)
    return _round((Decimal(str(px)) / m.div) * Decimal(str(rate)) * 100)


def commission(gross_ag: int) -> int:
    return max(_round(Decimal(gross_ag) * COMMISSION_RATE), COMMISSION_MIN_AG)


def fx_fee(gross_ag: int, market_code: str) -> int:
    return _round(Decimal(gross_ag) * FX_FEE_RATE * market(market_code).legs)


def price_trade(side: str, qty: int, px, market_code: str, rates: dict) -> dict:
    """Full pre-trade arithmetic. BUY net is a debit, SELL net is a credit."""
    if side not in ("BUY", "SELL"):
        raise ValueError("side must be BUY or SELL")
    if qty <= 0:
        raise ValueError("qty must be positive")
    m = market(market_code)
    if m.lot > 1 and qty % m.lot:
        raise ValueError(f"{m.code} trades in lots of {m.lot}")
    unit = to_agorot(px, market_code, rates)
    gross = unit * qty
    comm = commission(gross)
    fx = fx_fee(gross, market_code)
    net = gross + comm + fx if side == "BUY" else gross - comm - fx
    return {"unit_ag": unit, "gross_ag": gross, "commission_ag": comm,
            "fx_fee_ag": fx, "legs": m.legs, "net_ag": net,
            "rate": rates[m.ccy], "ccy": m.ccy}


def ils(ag: int) -> str:
    return f"\u20aa{ag / 100:,.2f}"
