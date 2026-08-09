"""Hedging and correlation-aware risk.

Every hedge costs money. A hedge that removes downside removes upside with it,
and on a small book the frictions decide the question before the thesis does.
The job of this module is to price that honestly and say no when the arithmetic
says no, which on a 100,000 shekel book is most of the time.
"""
from .markets import market
from .money import COMMISSION_MIN_AG, FX_FEE_RATE, commission, fx_fee

CORR_LINK = 0.60          # above this, two names are one bet
HEDGE_COST_CEILING = 0.02  # a hedge costing more than 2% of what it protects is noise


# ---------------------------------------------------------------- clustering
def clusters(positions: list[dict], corr: dict, threshold: float = CORR_LINK) -> list[dict]:
    """Sector tags are a human guess; correlation is the measurable thing.

    Elbit, Rheinmetall and AeroVironment sit in three sectors, three countries
    and three currencies, and they are one trade on defence spending. Union-find
    over the correlation matrix collapses them, and the concentration cap then
    applies to the cluster rather than to the label.
    """
    parent = {p["symbol"]: p["symbol"] for p in positions}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (a, b), rho in corr.items():
        if abs(rho) >= threshold and a in parent and b in parent:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

    out = {}
    for p in positions:
        out.setdefault(find(p["symbol"]), []).append(p)
    total = sum(p["mv_ag"] for p in positions) or 1
    return sorted(({"members": [q["symbol"] for q in g],
                    "mv_ag": sum(q["mv_ag"] for q in g),
                    "weight": round(sum(q["mv_ag"] for q in g) / total, 4)}
                   for g in out.values()), key=lambda c: -c["mv_ag"])


def effective_bets(positions: list[dict], corr: dict) -> float:
    """Inverse Herfindahl over correlation clusters. Eight positions that move
    together are one bet, and this is the number that says so."""
    cs = clusters(positions, corr)
    return round(1 / sum(c["weight"] ** 2 for c in cs), 2) if cs else 0.0


# ------------------------------------------------------------------- beta
def portfolio_beta(positions: list[dict], betas: dict) -> float:
    total = sum(p["mv_ag"] for p in positions)
    if not total:
        return 0.0
    return round(sum(p["mv_ag"] * betas.get(p["symbol"], 1.0) for p in positions) / total, 3)


def beta_hedge(positions: list[dict], betas: dict, hedge_px_ag: int,
               contract_multiplier: int = 1) -> dict:
    """Notional of an index short needed to neutralise market beta, and whether
    the smallest tradeable unit is finer than the exposure being hedged.

    On a small book it usually is not. A TA-35 future or option carries a
    notional far larger than the whole portfolio, so one unit does not hedge the
    position - it replaces it with a larger opposite position.
    """
    exposure = sum(p["mv_ag"] for p in positions)
    beta = portfolio_beta(positions, betas)
    needed = int(exposure * beta)
    unit = hedge_px_ag * contract_multiplier
    units = needed / unit if unit else 0
    return {"exposure_ag": exposure, "portfolio_beta": beta,
            "hedge_notional_ag": needed, "unit_notional_ag": unit,
            "units_required": round(units, 3),
            "granular_enough": units >= 1,
            "overshoot_pct": round((unit - needed) / needed, 3) if needed and units < 1 else 0.0,
            "note": ("" if units >= 1 else
                     "smallest tradeable unit exceeds the exposure; hedging here "
                     "adds risk rather than removing it")}


# ------------------------------------------------------------------ costs
def hedge_economics(protected_ag: int, premium_ag: int, market_code: str,
                    round_trip: bool = True) -> dict:
    """All-in cost of putting a hedge on and taking it off, against what it
    protects. Commission floor and the double FX conversion are included because
    on this book they dominate the premium."""
    legs = 2 if round_trip else 1
    comm = commission(premium_ag) * legs
    fx = fx_fee(premium_ag, market_code) * legs
    total = premium_ag + comm + fx
    ratio = total / protected_ag if protected_ag else 1.0
    return {"premium_ag": premium_ag, "commission_ag": comm, "fx_fee_ag": fx,
            "total_cost_ag": total, "cost_of_protected": round(ratio, 4),
            "worth_it": ratio <= HEDGE_COST_CEILING,
            "note": ("" if ratio <= HEDGE_COST_CEILING else
                     f"costs {ratio:.1%} of what it protects; a smaller position "
                     "achieves the same risk reduction for nothing")}


def currency_exposure(positions: list[dict]) -> dict:
    """Unhedged FX is a position you did not choose. A book of US names is a
    short-shekel trade whether or not that was the thesis.

    Hedging it costs 0.5% per conversion leg each way, so on a small book the
    cheap hedge is holding less foreign stock, not buying a forward.
    """
    total = sum(p["mv_ag"] for p in positions) or 1
    by = {}
    for p in positions:
        c = market(p["market"]).ccy
        by[c] = by.get(c, 0) + p["mv_ag"]
    foreign = sum(v for k, v in by.items() if k != "ILS")
    return {"by_currency_ag": by, "foreign_pct": round(foreign / total, 4),
            "shekel_move_1pct_impact_ag": round(foreign * 0.01),
            "note": "a 1% shekel move changes the book by this much before any "
                    "stock has traded"}
