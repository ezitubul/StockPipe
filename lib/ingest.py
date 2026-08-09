"""Pre-model ingest. Everything here runs before a token is spent.

The honest position: fetching a page is external, but reading it is not. Search
results and page bodies land inside a model's context window, and summarising
them is a model doing summarisation. What this module does is shrink and filter
that input deterministically first, so the model sees the smallest set of
already-relevant, already-deduplicated text that still answers the question.

Standard library only, deliberately: this code handles hostile input from the
open web, and every dependency added here is a supply-chain surface facing it.
"""
import hashlib
import json
import os
import re
import time
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DROP_PARAMS = re.compile(r"^(utm_|fbclid|gclid|mc_|ref|ref_src|igshid|si$|s$)")
DROP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "form",
             "noscript", "svg", "iframe", "button", "figure"}
SHINGLE = 4


# ------------------------------------------------------------ canonical URL
def canonical(url: str) -> str:
    """Same article, five tracking suffixes, one cache entry."""
    p = urlsplit(url.strip())
    host = p.netloc.lower().removeprefix("www.")
    q = urlencode([(k, v) for k, v in parse_qsl(p.query) if not DROP_PARAMS.match(k)])
    path = p.path.rstrip("/") or "/"
    return urlunsplit((p.scheme or "https", host, path, q, ""))


# --------------------------------------------------------------- text only
class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP_TAGS:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in DROP_TAGS and self.skip:
            self.skip -= 1

    def handle_data(self, d):
        if not self.skip and d.strip():
            self.out.append(d.strip())


def strip_boilerplate(html: str) -> str:
    """Navigation, scripts, cookie banners and related-article rails are pure
    cost - they carry no signal and they are most of the byte count."""
    p = _Text()
    try:
        p.feed(html)
    except Exception:
        return re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", " ".join(p.out)).strip()


# --------------------------------------------------------------- near-dupes
def _shingles(text: str) -> list[str]:
    w = re.findall(r"\w+", text.lower())
    return [" ".join(w[i:i + SHINGLE]) for i in range(max(1, len(w) - SHINGLE + 1))]


def simhash(text: str, bits: int = 64) -> int:
    """Stable across processes - hashlib, not the built-in hash()."""
    v = [0] * bits
    for sh in _shingles(text):
        h = int.from_bytes(hashlib.blake2b(sh.encode(), digest_size=8).digest(), "big")
        for i in range(bits):
            v[i] += 1 if (h >> i) & 1 else -1
    return sum(1 << i for i in range(bits) if v[i] > 0)


def distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


class Dedup:
    """One wire story reprinted by five outlets is one story. Sending all five
    into a context costs five times as much and tells the model nothing extra -
    worse, repetition reads as corroboration when it is a single source.

    Shingle Jaccard rather than simhash. Simhash exists to make comparison O(1)
    across millions of documents; a scan handles a few dozen, where exact set
    overlap is both cheap and materially more accurate on short text. Simhash is
    kept above for the cross-session seen-set, where storing full shingle sets
    would not be worth the disk.
    """

    def __init__(self, threshold: float = 0.55):
        self.threshold, self.seen = threshold, []

    def add(self, text: str) -> bool:
        sh = set(_shingles(text))
        if any(jaccard(sh, s) >= self.threshold for s in self.seen):
            return False
        self.seen.append(sh)
        return True


# ------------------------------------------------------------- relevance
def relevance(text: str, universe: list[str], keywords: list[str]) -> dict:
    """An article mentioning nothing in the universe and no macro keyword does
    not need a model to determine that it is irrelevant."""
    low = text.lower()
    syms = [s for s in universe if re.search(rf"\b{re.escape(s.lower())}\b", low)]
    kws = [k for k in keywords if k.lower() in low]
    return {"symbols": syms, "keywords": kws, "relevant": bool(syms or kws)}


# ----------------------------------------------------------------- caching
class Cache:
    """The 13:00 and 17:00 scans fetch many of the same pages. Refetching is
    cheap; re-summarising is not."""

    def __init__(self, root: str, ttl_s: int = 3600):
        self.root, self.ttl = root, ttl_s
        os.makedirs(root, exist_ok=True)

    def _path(self, url: str) -> str:
        return os.path.join(self.root, hashlib.sha256(canonical(url).encode()).hexdigest()[:24] + ".json")

    def get(self, url: str):
        p = self._path(url)
        if not os.path.exists(p) or time.time() - os.path.getmtime(p) > self.ttl:
            return None
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)

    def put(self, url: str, payload: dict) -> None:
        with open(self._path(url), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)


# ------------------------------------------------------------------ pipeline
def estimate_tokens(text: str) -> int:
    return len(text) // 4


def log_run(stats: dict, path: str) -> dict:
    """Append one scan's accounting and return the running total.

    The reduction ratio depends entirely on the corpus - how much wire
    syndication a given day carries, how targeted the searches were, whether the
    fetch path delivers raw HTML or already-stripped text. A single run tells
    you almost nothing. This exists so the number quoted after a month is
    measured rather than assumed.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            rows = [json.loads(l) for l in fh if l.strip()]
    row = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           **{k: stats[k] for k in ("tokens_before", "tokens_after")},
           "docs_in": len(stats["documents"]) + len(stats["dropped"]),
           "docs_kept": len(stats["documents"]),
           "dropped_duplicate": sum(1 for d in stats["dropped"] if "duplicate" in d["why"]),
           "dropped_irrelevant": sum(1 for d in stats["dropped"] if "match" in d["why"])}
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    rows.append(row)
    before = sum(r["tokens_before"] for r in rows)
    after = sum(r["tokens_after"] for r in rows)
    return {"runs": len(rows), "cumulative_tokens_before": before,
            "cumulative_tokens_after": after,
            "cumulative_reduction": round(1 - after / before, 3) if before else 0.0,
            "note": "single runs vary widely; trust this only after ~20 scans"}


def prepare(docs: list[dict], universe: list[str], keywords: list[str],
            max_chars: int = 4000) -> dict:
    """docs: [{"url","html" or "text"}]. Returns what the model should see and
    an accounting of what was removed before it cost anything.

    Order matters: strip first so dedup compares article text rather than
    identical navigation chrome, then filter, then truncate.
    """
    raw = kept = 0
    dd, out, dropped = Dedup(), [], []
    for d in docs:
        body = d.get("text") or strip_boilerplate(d.get("html", ""))
        raw += estimate_tokens(d.get("html") or d.get("text") or "")
        rel = relevance(body, universe, keywords)
        if not rel["relevant"]:
            dropped.append({"url": d["url"], "why": "no symbol or keyword match"})
            continue
        if not dd.add(body):
            dropped.append({"url": d["url"], "why": "near-duplicate of an earlier item"})
            continue
        body = body[:max_chars]
        kept += estimate_tokens(body)
        out.append({"url": canonical(d["url"]), "text": body, **rel})
    return {"documents": out, "dropped": dropped,
            "tokens_before": raw, "tokens_after": kept,
            "reduction": round(1 - kept / raw, 3) if raw else 0.0}
