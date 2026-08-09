"""Withdrawal policy.

The target is maximum sustainable extraction, which is NOT the same as maximum
extraction. Three facts drive the whole design:

1. Compounding is the asset. Every shekel withdrawn stops working. The account
   grows at (g - w), so the withdrawal rate is subtracted directly from growth.

2. Volatility eats the arithmetic mean. A book that averages +2% a month with
   large swings does not compound at 2%. Geometric growth is g = mu - sigma^2/2.
   The variance drain is real money and it is invisible in an average.

3. An estimated mean is mostly noise. SE(mu) = sigma / sqrt(n). At 25% annual
   volatility and one year of data the standard error of the mean return is 25
   percentage points - you cannot distinguish a good strategy from a coin flip.
   The policy therefore withdraws against the LOWER CONFIDENCE BOUND on growth,
   which is negative early on and produces a withdrawal of zero. That is correct.

Withdrawal is taken only from profit above the high-water mark, so a drawdown
sets it to zero automatically and principal is never consumed.
"""
import math
from statistics import mean, stdev

Z_DEFAULT = 1.0          # ~84% one-sided confidence
MIN_MONTHS = 12          # below this there is no estimate worth acting on
PROFIT_SHARE = 0.50      # fraction of high-water-mark profit eligible


def monthly_returns(equity_series: list[float]) -> list[float]:
    return [equity_series[i] / equity_series[i - 1] - 1
            for i in range(1, len(equity_series)) if equity_series[i - 1] > 0]


def growth_estimate(rets: list[float], z: float = Z_DEFAULT) -> dict:
    """Geometric growth with a confidence haircut for estimation error."""
    n = len(rets)
    if n < 2:
        return {"n": n, "mu": None, "sigma": None, "g": None, "g_lower": None}
    mu, sigma = mean(rets), stdev(rets)
    g = mu - (sigma ** 2) / 2                    # variance drain
    se = sigma / math.sqrt(n)                    # noise in the estimate of mu
    return {"n": n, "mu": round(mu, 5), "sigma": round(sigma, 5),
            "variance_drain": round((sigma ** 2) / 2, 5),
            "g": round(g, 5), "se": round(se, 5),
            "g_lower": round(g - z * se, 5)}


def policy(equity_ag: int, hwm_ag: int, equity_series: list[float],
           floor_ag: int, profit_share: float = PROFIT_SHARE,
           z: float = Z_DEFAULT, min_months: int = MIN_MONTHS) -> dict:
    """Recommended withdrawal for this month, in agorot.

        W = min( share * max(0, E - HWM),  max(0, g_lower) * E )
        W = 0  while  n < min_months  or  E - W < floor

    The first term is the incentive-fee structure: nothing is paid out until a
    new high is made. The second is the statistical ceiling: never extract
    faster than the growth you can actually demonstrate.
    """
    est = growth_estimate(monthly_returns(equity_series), z)
    reasons = []

    profit = max(0, equity_ag - hwm_ag)
    if profit == 0:
        reasons.append("below high-water mark - principal is not a source of income")

    if est["n"] < min_months:
        reasons.append(f'{est["n"]} months of history, {min_months} required; '
                       "the growth estimate is indistinguishable from noise")
        cap = 0
    else:
        cap = max(0.0, est["g_lower"] or 0.0) * equity_ag
        if cap == 0:
            reasons.append("lower confidence bound on growth is not positive - "
                           "no demonstrated edge to withdraw against")

    w = min(profit * profit_share, cap)
    if equity_ag - w < floor_ag:
        w = max(0, equity_ag - floor_ag)
        reasons.append("clipped by the capital floor")

    w = int(w)
    return {"withdraw_ag": w, "profit_above_hwm_ag": profit,
            "statistical_cap_ag": int(cap), "growth": est,
            "annualised_withdrawal_rate": round((w / equity_ag) * 12, 4) if equity_ag else 0,
            "reasons": reasons,
            "retained_ag": equity_ag - w}


def horizon(g_monthly: float, w_monthly: float) -> dict:
    """What a given withdrawal rate does to compounding. Net growth is g - w;
    once w exceeds g the account is in run-off however good the strategy is."""
    net = g_monthly - w_monthly
    return {"net_monthly_growth": round(net, 5),
            "doubling_months": round(math.log(2) / math.log(1 + net), 1) if net > 0 else None,
            "halving_months": round(math.log(0.5) / math.log(1 + net), 1) if -1 < net < 0 else None,
            "status": "compounding" if net > 0 else "run-off"}
