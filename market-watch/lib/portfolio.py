"""Portfolio state. Append-only trade log, integer agorot, atomic writes."""
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone

from .markets import market
from .money import MissingRate, price_trade, to_agorot

START_AG = 10_000_000       # 100,000 shekels
RED_FLAG_AG = 7_000_000     # 70,000 shekels
STATE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state", "portfolio.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def blank() -> dict:
    return {"v": 2, "mode": "PAPER", "cash_ag": START_AG,
            "rates": {"ILS": 1}, "positions": [], "trades": []}


def load(path: str = STATE) -> dict:
    if not os.path.exists(path):
        return blank()
    with open(path, encoding="utf-8") as fh:
        s = json.load(fh)
    if s.get("mode") != "PAPER":
        raise SystemExit("state file is not PAPER mode - refusing to load")
    return s


def save(state: dict, path: str = STATE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def find(state: dict, symbol: str, market_code: str):
    for p in state["positions"]:
        if p["symbol"] == symbol.upper() and p["market"] == market_code:
            return p
    return None


def value(state: dict) -> dict:
    """Mark to market. A position whose FX rate is missing is frozen at cost
    and reported, never silently revalued."""
    rows, stale = [], []
    for p in state["positions"]:
        try:
            mv = to_agorot(p["px"], p["market"], state["rates"]) * p["qty"]
        except MissingRate as e:
            mv, _ = p["cost_ag"], stale.append(f'{p["symbol"]}:{e}')
        rows.append({**p, "mv_ag": mv, "pl_ag": mv - p["cost_ag"],
                     "region": market(p["market"]).region,
                     "ccy": market(p["market"]).ccy})
    invested = sum(r["mv_ag"] for r in rows)
    equity = state["cash_ag"] + invested
    return {"rows": rows, "invested_ag": invested, "equity_ag": equity,
            "cash_pct": state["cash_ag"] / equity if equity else 1.0,
            "halted": equity < RED_FLAG_AG, "frozen": stale,
            "pl_ag": equity - START_AG}


def apply(state: dict, order: dict) -> dict:
    """Mutate a COPY of state with an executed order. Caller must have run
    risk_gates.evaluate() and obtained human confirmation first."""
    s = json.loads(json.dumps(state))
    q = price_trade(order["side"], order["qty"], order["px"], order["market"], s["rates"])
    pos = find(s, order["symbol"], order["market"])

    if order["side"] == "BUY":
        s["cash_ag"] -= q["net_ag"]
        if pos:
            pos["qty"] += order["qty"]
            pos["cost_ag"] += q["net_ag"]
            pos["px"] = order["px"]
        else:
            s["positions"].append({
                "id": uuid.uuid4().hex[:8], "symbol": order["symbol"].upper(),
                "name": order.get("name", ""), "issuer": order.get("issuer") or order["symbol"].upper(),
                "market": order["market"], "sector": order["sector"],
                "qty": order["qty"], "cost_ag": q["net_ag"], "px": order["px"],
                "px_at": _now(), "rate_at": q["rate"],
                "tp": order.get("tp", 0.175), "sl": order.get("sl", -0.10),
                "entry_at": _now()})
        realized = None
    else:
        if not pos or order["qty"] > pos["qty"]:
            raise ValueError("cannot sell more than held")
        cost_out = round(pos["cost_ag"] * order["qty"] / pos["qty"])
        realized = q["net_ag"] - cost_out
        s["cash_ag"] += q["net_ag"]
        if order["qty"] == pos["qty"]:
            s["positions"].remove(pos)
        else:
            pos["qty"] -= order["qty"]
            pos["cost_ag"] -= cost_out
            pos["px"] = order["px"]

    s["trades"].insert(0, {
        "id": uuid.uuid4().hex[:8], "at": _now(), **{k: order[k] for k in
        ("side", "symbol", "market", "sector", "qty", "px")},
        **q, "realized_ag": realized, "cash_after_ag": s["cash_ag"],
        "catalyst": order["catalyst"], "rationale": order["rationale"],
        "sources": order["sources"]})
    return s
