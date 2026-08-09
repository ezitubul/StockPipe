"""Market registry. Single source of truth for quote units, currency and sessions.

Two things kill paper-trading simulators and both live here:
  * quote divisor   - TASE quotes in agorot, LSE in pence. div=100 for both.
  * conversion legs - a non-USD foreign leg routes ILS->USD->X, so the FX fee
                      is charged twice in one direction, four times round trip.
All session times are ISRAEL local (Asia/Jerusalem), 24h.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Market:
    code: str
    name: str
    ccy: str
    div: int          # quote divisor -> major currency unit
    unit: str
    open: str         # Israel local
    close: str
    region: str
    lot: int = 1

    @property
    def legs(self) -> int:
        if self.ccy == "ILS":
            return 0
        return 1 if self.ccy == "USD" else 2


MARKETS = {
    m.code: m for m in [
        Market("TASE",  "תל אביב",   "ILS", 100, "אג'", "10:00", "17:35", "ישראל"),
        Market("US",    "ניו יורק",  "USD", 1,   "$",   "16:30", "23:00", "צפון אמריקה"),
        Market("LSE",   "לונדון",    "GBP", 100, "פני", "10:00", "17:30", "אירופה"),
        Market("XETRA", "פרנקפורט",  "EUR", 1,   "€",   "10:00", "18:30", "אירופה"),
        Market("EURO",  "פריז/אמס",  "EUR", 1,   "€",   "10:00", "18:30", "אירופה"),
        Market("SIX",   "ציריך",     "CHF", 1,   "Fr",  "10:00", "18:20", "אירופה"),
        Market("TSE",   "טוקיו",     "JPY", 1,   "¥",   "03:00", "09:00", "אסיה־פסיפיק", lot=100),
        Market("HKEX",  "הונג קונג", "HKD", 1,   "HK$", "04:30", "11:00", "אסיה־פסיפיק", lot=100),
        Market("NSE",   "מומבאי",    "INR", 1,   "₹",   "06:15", "12:30", "אסיה־פסיפיק"),
        Market("ASX",   "סידני",     "AUD", 1,   "A$",  "03:00", "09:00", "אסיה־פסיפיק"),
    ]
}

CURRENCIES = sorted({m.ccy for m in MARKETS.values()})


def market(code: str) -> Market:
    try:
        return MARKETS[code]
    except KeyError:
        raise ValueError(f"unknown market {code!r}; known: {sorted(MARKETS)}")
