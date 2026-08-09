import copy
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from lib import money, portfolio, risk_gates, session

IL = ZoneInfo("Asia/Jerusalem")
RATES = {"ILS": 1, "USD": 3.01, "GBP": 4.05, "EUR": 3.50, "JPY": 0.0198}


# ---------- unit conversion: the agorot / pence trap ----------
def test_tase_quote_is_agorot():
    # 300,000 agorot == 3,000 shekels == 300,000 agorot internally
    assert money.to_agorot(300_000, "TASE", RATES) == 300_000


def test_lse_quote_is_pence_not_pounds():
    # 4,200 pence == 42 GBP == 42 * 4.05 = 170.10 shekels = 17,010 agorot
    assert money.to_agorot(4_200, "LSE", RATES) == 17_010


def test_us_quote_is_dollars():
    assert money.to_agorot(100, "US", RATES) == 30_100


def test_missing_rate_raises_never_guesses():
    with pytest.raises(money.MissingRate):
        money.to_agorot(100, "SIX", RATES)


# ---------- fees ----------
def test_commission_floor_applies_to_small_trades():
    assert money.commission(1000) == 800          # 0.15% of 10 shekels < 8 shekels floor
    assert money.commission(10_000_000) == 15_000  # 0.15% of 100k


def test_domestic_trade_has_no_fx_fee():
    assert money.fx_fee(1_000_000, "TASE") == 0


def test_non_usd_leg_is_charged_twice():
    assert money.fx_fee(1_000_000, "US") == 5_000     # one leg
    assert money.fx_fee(1_000_000, "XETRA") == 10_000  # routed via USD


def test_lot_size_enforced():
    with pytest.raises(ValueError):
        money.price_trade("BUY", 150, 1000, "TSE", RATES)


# ---------- cash arithmetic ----------
def test_buy_then_full_sell_conserves_cash_minus_fees():
    s = portfolio.blank()
    s["rates"] = dict(RATES)
    order = dict(side="BUY", symbol="ESLT", issuer="ELBIT", market="TASE",
                 sector="defence", qty=4, px=300_000, catalyst="Q2 report 18.8",
                 rationale="record backlog and a doubled dividend",
                 sources=["Reuters", "Globes"])
    s2 = portfolio.apply(s, order)
    spent = s["cash_ag"] - s2["cash_ag"]
    assert spent == 1_200_000 + 1800  # gross + commission, no fx
    s3 = portfolio.apply(s2, {**order, "side": "SELL"})
    # round trip at an unchanged price loses exactly two commissions
    assert s3["cash_ag"] == portfolio.START_AG - 1800 - 1800
    assert s3["positions"] == []
    assert s3["trades"][0]["realized_ag"] == -3600


def test_partial_sell_prorates_cost():
    s = portfolio.blank(); s["rates"] = dict(RATES)
    buy = dict(side="BUY", symbol="AAPL", issuer="APPLE", market="US",
               sector="tech", qty=10, px=200, catalyst="earnings beat",
               rationale="services margin expansion continues", sources=["a", "b"])
    s = portfolio.apply(s, buy)
    cost = s["positions"][0]["cost_ag"]
    s = portfolio.apply(s, {**buy, "side": "SELL", "qty": 4})
    assert s["positions"][0]["qty"] == 6
    assert s["positions"][0]["cost_ag"] == cost - round(cost * 4 / 10)


# ---------- session clock ----------
def test_tase_closed_on_saturday_and_sunday():
    sat = datetime(2026, 8, 8, 12, 0, tzinfo=IL)
    sun = datetime(2026, 8, 9, 12, 0, tzinfo=IL)
    assert not session.is_open("TASE", sat)
    assert not session.is_open("TASE", sun)


def test_tase_open_monday_midday():
    assert session.is_open("TASE", datetime(2026, 8, 10, 12, 0, tzinfo=IL))


def test_tokyo_closed_at_israeli_evening():
    assert not session.is_open("TSE", datetime(2026, 8, 6, 22, 0, tzinfo=IL))


def test_overlap_window_is_the_execution_hour():
    assert session.overlap_window(datetime(2026, 8, 6, 17, 0, tzinfo=IL))
    assert not session.overlap_window(datetime(2026, 8, 6, 12, 0, tzinfo=IL))


# ---------- risk gates ----------
def _base():
    s = portfolio.blank()
    s["rates"] = dict(RATES)
    return s


OPEN_TASE = datetime(2026, 8, 10, 12, 0, tzinfo=IL)


def _order(**kw):
    base = dict(side="BUY", symbol="ESLT", issuer="ELBIT", market="TASE",
                sector="defence", qty=4, px=300_000, catalyst="Q2 report 18.8",
                rationale="record backlog and a doubled dividend",
                sources=["Reuters", "Globes"])
    base.update(kw)
    return base


def test_clean_order_passes():
    ok, gates, q = risk_gates.evaluate(_base(), _order(), OPEN_TASE)
    assert ok, [g for g in gates if not g["ok"]]


def test_single_source_is_rejected():
    ok, gates, _ = risk_gates.evaluate(_base(), _order(sources=["Reuters"]), OPEN_TASE)
    assert not ok
    assert not next(g for g in gates if g["name"] == "sources")["ok"]


def test_closed_market_is_rejected():
    sat = datetime(2026, 8, 8, 12, 0, tzinfo=IL)
    ok, gates, _ = risk_gates.evaluate(_base(), _order(), sat)
    assert not next(g for g in gates if g["name"] == "market_open")["ok"]


def test_oversized_position_breaches_issuer_cap():
    ok, gates, _ = risk_gates.evaluate(_base(), _order(qty=10), OPEN_TASE)
    assert not next(g for g in gates if g["name"] == "issuer_cap")["ok"]


def test_dual_listing_aggregates_to_one_issuer():
    s = _base()
    s = portfolio.apply(s, _order(qty=4))            # ~12% of equity on TASE
    # now buy the Nasdaq line of the same issuer
    ok, gates, _ = risk_gates.evaluate(
        s, _order(symbol="ESLT.US", market="US", qty=3, px=1000), OPEN_TASE)
    cap = next(g for g in gates if g["name"] == "issuer_cap")
    assert not cap["ok"], "dual listings must aggregate under one issuer cap"


def test_cash_floor_blocks_over_deployment():
    s = _base()
    ok, gates, _ = risk_gates.evaluate(
        s, _order(symbol="A", issuer="A", qty=1, px=8_500_000), OPEN_TASE)
    names = {g["name"]: g["ok"] for g in gates}
    assert not names["cash_floor"]


def test_halted_portfolio_blocks_buys_but_allows_sells():
    s = _base()
    s["cash_ag"] = 6_000_000
    ok, gates, _ = risk_gates.evaluate(s, _order(qty=1), OPEN_TASE)
    assert not next(g for g in gates if g["name"] == "not_halted")["ok"]


# ---------- target feasibility ----------
from lib import performance


def test_ten_thousand_a_month_on_a_hundred_thousand_is_infeasible():
    s = portfolio.blank()
    f = performance.feasibility(s, 1_000_000)      # 10,000 shekels
    assert not f["feasible"]
    assert f["required_monthly_return"] > 0.10     # before tax it is already 10%
    assert f["perfect_trades_needed_per_month"] > 4


def test_a_defensible_target_is_reported_feasible():
    s = portfolio.blank()
    f = performance.feasibility(s, 100_000)        # 1,000 shekels a month
    assert f["feasible"]


def test_feasibility_marks_open_positions_to_market_not_cost():
    # cash_ag + cost_ag is invariant across any number of BUYs (fees just move
    # from cash into cost basis 1:1), so it is always exactly START_AG for a
    # book with only open positions - using it as "equity" silently discards
    # every unrealised gain or loss, which is precisely what feasibility (D6)
    # exists to catch honestly.
    s = portfolio.blank(); s["rates"] = dict(RATES)
    buy = dict(side="BUY", symbol="ESLT", issuer="ELBIT", market="TASE",
               sector="defence", qty=10, px=150_000, catalyst="Q2 report 18.8",
               rationale="record backlog and a doubled dividend",
               sources=["Reuters", "Globes"])
    s = portfolio.apply(s, buy)
    s["positions"][0]["px"] = 300_000        # position has since doubled
    f = performance.feasibility(s, 100_000)
    assert f["equity_ag"] > portfolio.START_AG


def test_drawdown_refuses_to_flatter_an_empty_ledger():
    assert performance.drawdown(portfolio.blank())["max_drawdown_pct"] is None


# ---------- withdrawal policy ----------
from lib import hedging, withdrawal


def test_no_withdrawal_below_high_water_mark():
    r = withdrawal.policy(9_500_000, 10_000_000, [100.0] * 30, floor_ag=7_000_000)
    assert r["withdraw_ag"] == 0
    assert any("high-water" in x for x in r["reasons"])


def test_no_withdrawal_without_enough_history():
    series = [100 * 1.02 ** i for i in range(4)]
    r = withdrawal.policy(11_000_000, 10_000_000, series, floor_ag=7_000_000)
    assert r["withdraw_ag"] == 0
    assert any("noise" in x for x in r["reasons"])


def test_volatile_book_withdraws_less_than_a_calm_one():
    calm = [100 * 1.01 ** i for i in range(25)]
    vol = [100.0]
    for i in range(24):
        vol.append(vol[-1] * (1.13 if i % 2 else 0.90))   # same drift, huge swings
    a = withdrawal.policy(12_000_000, 10_000_000, calm, floor_ag=7_000_000)
    b = withdrawal.policy(12_000_000, 10_000_000, vol, floor_ag=7_000_000)
    assert a["withdraw_ag"] > b["withdraw_ag"]


def test_withdrawing_all_of_growth_stops_compounding():
    assert withdrawal.horizon(0.01, 0.01)["status"] == "run-off"
    assert withdrawal.horizon(0.01, 0.005)["status"] == "compounding"


# ---------- correlation-aware risk ----------
def _p(sym, mv):
    return {"symbol": sym, "mv_ag": mv, "market": "TASE"}


def test_correlated_names_collapse_into_one_cluster():
    pos = [_p("ESLT", 1_000_000), _p("RHM", 1_000_000), _p("NVMI", 500_000)]
    corr = {("ESLT", "RHM"): 0.82, ("ESLT", "NVMI"): 0.15}
    cs = hedging.clusters(pos, corr)
    assert cs[0]["mv_ag"] == 2_000_000            # the two defence names are one bet
    assert len(cs) == 2


def test_effective_bets_falls_when_everything_correlates():
    pos = [_p("A", 1_000_000), _p("B", 1_000_000), _p("C", 1_000_000)]
    assert hedging.effective_bets(pos, {}) == 3.0
    linked = {("A", "B"): 0.9, ("B", "C"): 0.9}
    assert hedging.effective_bets(pos, linked) == 1.0


def test_index_hedge_is_too_coarse_for_a_small_book():
    pos = [_p("A", 3_000_000)]
    r = hedging.beta_hedge(pos, {"A": 1.0}, hedge_px_ag=250_000, contract_multiplier=100)
    assert not r["granular_enough"]
    assert "adds risk" in r["note"]


def test_expensive_hedge_is_rejected():
    r = hedging.hedge_economics(protected_ag=1_500_000, premium_ag=90_000, market_code="TASE")
    assert not r["worth_it"]
    cheap = hedging.hedge_economics(protected_ag=50_000_000, premium_ag=90_000, market_code="TASE")
    assert cheap["worth_it"]


def test_foreign_book_is_a_short_shekel_position():
    pos = [{"symbol": "NVDA", "mv_ag": 4_000_000, "market": "US"},
           {"symbol": "ESLT", "mv_ag": 1_000_000, "market": "TASE"}]
    r = hedging.currency_exposure(pos)
    assert r["foreign_pct"] == 0.8
    assert r["shekel_move_1pct_impact_ag"] == 40_000


# ---------- pre-model ingest ----------
from lib import ingest


def test_tracking_parameters_collapse_to_one_url():
    a = ingest.canonical("https://www.globes.co.il/news/1001551486?utm_source=x&fbclid=y")
    b = ingest.canonical("https://globes.co.il/news/1001551486/#comments")
    assert a == b
    # a real query parameter is content, not tracking, and must survive
    assert "did=1" in ingest.canonical("https://globes.co.il/a?did=1&utm_medium=rss")


def test_boilerplate_is_removed_before_any_model_sees_it():
    html = ("<nav>Home Sections Subscribe</nav><script>var ads=1</script>"
            "<article><p>Elbit reported record backlog.</p></article>"
            "<footer>Terms Privacy</footer>")
    t = ingest.strip_boilerplate(html)
    assert "Elbit reported record backlog." in t
    assert "Subscribe" not in t and "Terms" not in t and "ads" not in t


def test_one_wire_story_across_outlets_counts_once():
    base = ("The central bank left rates unchanged and signalled that further "
            "tightening remains possible later this year, officials said.")
    dd = ingest.Dedup()
    assert dd.add(base)
    assert not dd.add(base + " Reporting by staff.")     # same story, different outlet
    assert dd.add("Oil fell sharply as talks progressed toward reopening the strait.")


def test_irrelevant_articles_never_reach_a_context():
    r = ingest.relevance("A local football club appointed a new manager today.",
                         ["ESLT", "NVDA"], ["rate decision", "inflation"])
    assert not r["relevant"]


def test_pipeline_reports_what_it_removed():
    docs = [
        {"url": "https://a.com/1", "html": "<nav>menu</nav><p>ESLT posted a record backlog this quarter.</p>"},
        {"url": "https://b.com/1?utm_source=z", "html": "<p>ESLT posted a record backlog this quarter.</p>"},
        {"url": "https://c.com/1", "html": "<p>A cat was rescued from a tree.</p>"},
    ]
    r = ingest.prepare(docs, ["ESLT"], ["backlog"])
    assert len(r["documents"]) == 1
    assert len(r["dropped"]) == 2
    assert r["reduction"] > 0
