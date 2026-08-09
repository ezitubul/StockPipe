"""Track record and target feasibility. The numbers that decide whether this
system has earned the right to be trusted with anything.

A withdrawal target is not a strategy input. It is tested against the ledger
here, and when the ledger says the target is unreachable under the risk limits,
that is reported as a shortfall - never resolved by relaxing a limit.
"""
from collections import defaultdict
from datetime import datetime

from .portfolio import START_AG
from .risk_gates import MAX_ISSUER

TAKE_PROFIT_CEILING = 0.20     # the most a single position may contribute


def _month(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%Y-%m")


def realised(state: dict) -> dict:
    """Closed-trade statistics. Open positions are excluded on purpose -
    an unrealised gain is not a track record."""
    wins = [t for t in state["trades"] if (t.get("realized_ag") or 0) > 0]
    losses = [t for t in state["trades"] if (t.get("realized_ag") or 0) < 0]
    closed = wins + losses
    total = sum(t["realized_ag"] for t in closed)
    by_month = defaultdict(int)
    for t in closed:
        by_month[_month(t["at"])] += t["realized_ag"]
    return {
        "closed_trades": len(closed),
        "hit_rate": len(wins) / len(closed) if closed else None,
        "avg_win_ag": sum(t["realized_ag"] for t in wins) // len(wins) if wins else 0,
        "avg_loss_ag": sum(t["realized_ag"] for t in losses) // len(losses) if losses else 0,
        "realised_ag": total,
        "by_month_ag": dict(sorted(by_month.items())),
        "fees_paid_ag": sum(t["commission_ag"] + t["fx_fee_ag"] for t in state["trades"]),
    }


def drawdown(state: dict) -> dict:
    """Peak-to-trough on the cash-after series. Requires a real trade history;
    with fewer than two closed trades it reports None rather than a flattering
    zero."""
    series = [START_AG] + [t["cash_after_ag"] for t in reversed(state["trades"])]
    if len(series) < 3:
        return {"max_drawdown_pct": None, "note": "insufficient history"}
    peak, worst = series[0], 0.0
    for v in series:
        peak = max(peak, v)
        worst = max(worst, (peak - v) / peak)
    return {"max_drawdown_pct": round(worst, 4)}


def feasibility(state: dict, monthly_target_ag: int, tax_rate: float = 0.25) -> dict:
    """Can the stated withdrawal target be met under the stated risk limits?

    Two independent tests, both of which must pass:
      1. Sustainability - a fixed withdrawal against a percentage return has a
         fixed point at W/r. Below it the balance decays monotonically to zero
         regardless of how good the strategy is.
      2. Gate capacity - the largest permitted position, taken to the take-profit
         ceiling, caps what any one trade can contribute. The target implies a
         number of fully-sized, fully-successful trades per month.
    """
    equity = state["cash_ag"] + sum(p["cost_ag"] for p in state["positions"])
    gross_needed = monthly_target_ag / (1 - tax_rate)
    required_monthly_return = gross_needed / equity if equity else float("inf")
    max_per_trade = equity * MAX_ISSUER * TAKE_PROFIT_CEILING
    return {
        "equity_ag": equity,
        "net_target_ag": monthly_target_ag,
        "gross_target_ag": round(gross_needed),
        "required_monthly_return": round(required_monthly_return, 4),
        "required_annual_return": round((1 + required_monthly_return) ** 12 - 1, 3),
        "max_contribution_per_trade_ag": round(max_per_trade),
        "perfect_trades_needed_per_month": round(gross_needed / max_per_trade, 1) if max_per_trade else None,
        "capital_needed_at_1pct_monthly_ag": round(gross_needed / 0.01),
        "feasible": required_monthly_return <= 0.02,
        "verdict": ("target is within a defensible return range"
                    if required_monthly_return <= 0.02 else
                    "target requires a return no systematic strategy sustains; "
                    "it cannot be met without breaching the risk limits"),
    }
