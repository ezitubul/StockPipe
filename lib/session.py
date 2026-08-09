"""Deterministic session clock. A trade into a closed market is not a trade."""
from datetime import datetime, time
from zoneinfo import ZoneInfo

from .markets import MARKETS, market

IL = ZoneInfo("Asia/Jerusalem")


def _t(hhmm: str) -> time:
    h, m = hhmm.split(":")
    return time(int(h), int(m))


def now_il() -> datetime:
    return datetime.now(IL)


def is_open(code: str, when: datetime | None = None) -> bool:
    """Weekday sessions only. Local market holidays are NOT modelled -
    the scout must confirm the venue actually traded."""
    m = market(code)
    when = when or now_il()
    if when.weekday() >= 5:          # 5=Sat, 6=Sun
        return False
    return _t(m.open) <= when.time() <= _t(m.close)


def open_markets(when: datetime | None = None) -> list[str]:
    return [c for c in MARKETS if is_open(c, when)]


def overlap_window(when: datetime | None = None) -> bool:
    """16:30-17:35 IL: Tel Aviv and Europe still open, New York opening.
    The only moment of the day when a cross-market decision is executable."""
    when = when or now_il()
    return when.weekday() < 5 and _t("16:30") <= when.time() <= _t("17:35")
