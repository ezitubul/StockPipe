#!/usr/bin/env python3
"""mw - deterministic CLI. Every number the agents quote comes from here.

  mw.py status
  mw.py clock
  mw.py rates --set USD=3.01 --set GBP=4.05
  mw.py quote  --side BUY --symbol ESLT --market TASE --qty 4 --px 300000
  mw.py gates  --order order.json
  mw.py apply  --order order.json --confirm
"""
import argparse
import json
import sys

from lib import hedging, ingest, money, performance, portfolio, risk_gates, session, withdrawal
from lib.markets import MARKETS


def _out(obj):
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=2)
    print()


def cmd_status(a):
    s = portfolio.load()
    v = portfolio.value(s)
    _out({"mode": s["mode"], "equity": money.ils(v["equity_ag"]),
          "cash": money.ils(s["cash_ag"]), "cash_pct": round(v["cash_pct"], 4),
          "pl": money.ils(v["pl_ag"]), "halted": v["halted"],
          "frozen_no_rate": v["frozen"],
          "positions": [{"symbol": r["symbol"], "market": r["market"],
                         "issuer": r["issuer"], "qty": r["qty"],
                         "mv": money.ils(r["mv_ag"]),
                         "pl_pct": round(r["pl_ag"] / r["cost_ag"], 4) if r["cost_ag"] else 0,
                         "weight": round(r["mv_ag"] / v["equity_ag"], 4),
                         "stale_px_at": r["px_at"]} for r in v["rows"]],
          "missing_rates": sorted({m.ccy for m in MARKETS.values()
                                   if not s["rates"].get(m.ccy)})})


def cmd_clock(a):
    """--require lets a CI job abort cheaply when the venue is shut.

    GitHub Actions cron is UTC only, so a fixed schedule drifts by an hour
    across Israeli DST. Schedule generously in UTC and let this guard decide.
    """
    open_now = session.open_markets()
    _out({"now_il": session.now_il().isoformat(timespec="minutes"),
          "open": open_now, "overlap_window": session.overlap_window(),
          "required": a.require, "proceed": not a.require or bool(set(a.require) & set(open_now))})
    if a.require and not (set(a.require) & set(open_now)):
        sys.exit(3)


def cmd_rates(a):
    s = portfolio.load()
    for pair in a.set or []:
        k, v = pair.split("=")
        s["rates"][k.upper()] = float(v)
    portfolio.save(s)
    _out(s["rates"])


def cmd_quote(a):
    s = portfolio.load()
    _out(money.price_trade(a.side, a.qty, a.px, a.market, s["rates"]))


def cmd_perf(a):
    s = portfolio.load()
    out = {"realised": performance.realised(s), **performance.drawdown(s)}
    if a.target:
        out["feasibility"] = performance.feasibility(s, int(round(a.target * 100)))
    _out(out)


def cmd_withdraw(a):
    """Recommended withdrawal. Reads the equity series from the trade log."""
    s = portfolio.load()
    series = [portfolio.START_AG] + [t["cash_after_ag"] for t in reversed(s["trades"])]
    hwm = max(series + [s["cash_ag"]])
    _out(withdrawal.policy(portfolio.value(s)["equity_ag"], hwm, series,
                           floor_ag=a.floor * 100 if a.floor else portfolio.RED_FLAG_AG,
                           profit_share=a.share))


def cmd_risk(a):
    s = portfolio.load()
    rows = portfolio.value(s)["rows"]
    corr = {}
    for pair in a.corr or []:
        k, v = pair.split("=")
        x, y = k.split(",")
        corr[(x.upper(), y.upper())] = float(v)
    _out({"clusters": hedging.clusters(rows, corr),
          "effective_bets": hedging.effective_bets(rows, corr),
          "currency": hedging.currency_exposure(rows)})


def cmd_ingest(a):
    """Deterministic pre-model pass. Reads [{"url","html"|"text"}] on stdin and
    emits only what is worth spending a context window on."""
    docs = json.load(sys.stdin)
    stats = ingest.prepare(docs, a.symbol or [], a.keyword or [], a.max_chars)
    if not a.no_log:
        stats["cumulative"] = ingest.log_run(stats, "state/ingest-log.jsonl")
    _out(stats)


def _order(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def cmd_gates(a):
    s = portfolio.load()
    ok, gates, q = risk_gates.evaluate(s, _order(a.order))
    _out({"passed": ok, "gates": gates, "quote": q})
    sys.exit(0 if ok else 1)


def cmd_apply(a):
    """Human confirmation is structural: without --confirm nothing is written."""
    s = portfolio.load()
    o = _order(a.order)
    ok, gates, q = risk_gates.evaluate(s, o)
    if not ok:
        _out({"applied": False, "reason": "gates failed",
              "failed": [g for g in gates if not g["ok"]]})
        sys.exit(1)
    if a.agent and s.get("mode") != "PAPER":
        _out({"applied": False, "reason": "agent authorisation exists only in PAPER mode"})
        sys.exit(3)
    if not (a.confirm or a.agent):
        _out({"applied": False, "reason": "awaiting human confirmation",
              "quote": q})
        sys.exit(2)
    portfolio.save(portfolio.apply(s, o))
    _out({"applied": True, "quote": q})


P = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
SUB = P.add_subparsers(required=True)
SUB.add_parser("status").set_defaults(fn=cmd_status)
ck = SUB.add_parser("clock")
ck.add_argument("--require", action="append", help="exit 3 unless one of these markets is open")
ck.set_defaults(fn=cmd_clock)
r = SUB.add_parser("rates"); r.add_argument("--set", action="append"); r.set_defaults(fn=cmd_rates)
q = SUB.add_parser("quote")
for f, t in [("--side", str), ("--symbol", str), ("--market", str), ("--qty", int), ("--px", float)]:
    q.add_argument(f, type=t, required=True)
q.set_defaults(fn=cmd_quote)
ig = SUB.add_parser("ingest")
ig.add_argument("--symbol", action="append")
ig.add_argument("--keyword", action="append")
ig.add_argument("--max-chars", type=int, default=4000, dest="max_chars")
ig.add_argument("--no-log", action="store_true")
ig.set_defaults(fn=cmd_ingest)
wd = SUB.add_parser("withdraw")
wd.add_argument("--floor", type=float, help="capital floor in shekels")
wd.add_argument("--share", type=float, default=withdrawal.PROFIT_SHARE)
wd.set_defaults(fn=cmd_withdraw)
rk = SUB.add_parser("risk")
rk.add_argument("--corr", action="append", metavar="A,B=0.8")
rk.set_defaults(fn=cmd_risk)
pf = SUB.add_parser("perf")
pf.add_argument("--target", type=float, help="monthly withdrawal target in shekels")
pf.set_defaults(fn=cmd_perf)
g = SUB.add_parser("gates"); g.add_argument("--order", required=True); g.set_defaults(fn=cmd_gates)
ap = SUB.add_parser("apply"); ap.add_argument("--order", required=True)
ap.add_argument("--confirm", action="store_true", help="human authorisation")
ap.add_argument("--agent", action="store_true", help="autonomous authorisation; PAPER only")
ap.set_defaults(fn=cmd_apply)

if __name__ == "__main__":
    a = P.parse_args()
    a.fn(a)
