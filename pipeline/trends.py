"""Find a fresh, current 3D printing topic from free RSS feeds (no API keys).

Google News RSS is the main source because it is searchable by topic. Google Trends'
"trending now" RSS covers every subject, so it only contributes entries that mention
3D printing. Every function returns [] on failure so the caller can fall back to the topic bank."""
import random
import re
import urllib.parse
import xml.etree.ElementTree as ET

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; trend-fetch)"}
NEWS_URL = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
TRENDS_URL = "https://trends.google.com/trending/rss?geo={geo}"
QUERIES = [
    "3D printing when:2d",
    "3D printer news when:2d",
    "filament OR resin 3D printing when:3d",
    "multicolor OR multi-material 3D printer when:3d",
]
KEYWORDS = re.compile(
    r"3d[ -]?print|filament|resin print|\bfdm\b|slicer|nozzle|additive manufacturing", re.I)
MAX_TITLE = 120
# Keep the feed positive and on-format: no crime/harm stories, no sales posts or product reviews,
# no brand-focused headlines (scripts may not name brands), no entertainment items.
BLOCKED = re.compile(
    r"firearm|\bguns?\b|ghost gun|weapon|rifle|pistol|\bammo|suppressor|explosive|bomb|"
    r"fentanyl|\bdrugs?\b|narcotic|seiz|arrest|charged|police|\bcops?\b|crime|criminal|illegal|"
    r"lawsuit|\bsued?\b|recall|fire hazard|\bfires?\b|burn(?:s|ed)?\b|toxic|\bfumes?\b|"
    r"injur|\bdead\b|death|\bkill|murder|shoot|terror|war\b|military|"
    r"\bdeals?\b|\bsale\b|discount|coupon|black friday|prime day|cheapest|as low as|\$\d|"
    r"\breview\b|vs\.?\s|hands-on|unboxing|\bbuy\b|where to|best \d|top \d|"
    r"bambu|prusa|creality|anycubic|elegoo|snapmaker|flashforge|sovol|qidi|formlabs|stratasys|"
    r"makerbot|ultimaker|raise3d|thingiverse|printables|makerworld|"
    r"\btv\b|series|season|episode|movie|film|netflix|costume|cosplay|earrings|jewel|fashion|"
    r"stock|shares|invests?|funding|acquires?|acquisition|"
    r"fallen|memorial|honou?red|tribute|market|forecast|news briefs|rivian|\bford\b|\bgm\b", re.I)


def _clean(title):
    title = re.sub(r"\s+-\s+[^-]{2,40}$", "", title)  # drop the " - Publisher" suffix
    title = re.sub(r"\s+", " ", title).strip()
    return title[:MAX_TITLE]


def _items(url, timeout=20):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return ET.fromstring(r.content).iter("item")


def _news(query):
    url = NEWS_URL.format(q=urllib.parse.quote_plus(query))
    return [_clean(i.findtext("title") or "") for i in _items(url)]


def _trending(geo="US"):
    out = []
    for item in _items(TRENDS_URL.format(geo=geo)):
        texts = [item.findtext("title") or ""] + [
            t.text or "" for t in item.iter() if t.tag.endswith("news_item_title")]
        if any(KEYWORDS.search(t) for t in texts):
            out.append(_clean(item.findtext("title") or ""))
    return out


def candidates():
    """Relevant headlines, de-duplicated, from every source that responds."""
    found, seen = [], set()
    for source in [_trending] + [lambda q=q: _news(q) for q in QUERIES]:
        try:
            titles = source()
        except Exception as exc:
            print(f"[trends] source failed: {type(exc).__name__}: {exc}")
            continue
        for t in titles:
            key = re.sub(r"\W+", " ", t.lower()).strip()
            if t and key not in seen and KEYWORDS.search(t) and not BLOCKED.search(t):
                seen.add(key)
                found.append(t)
    return found


def pick(used_trends, rng=random):
    """A random unused headline, or None when nothing fresh is available."""
    used = {re.sub(r"\W+", " ", u.lower()).strip() for u in used_trends if u}
    fresh = [t for t in candidates() if re.sub(r"\W+", " ", t.lower()).strip() not in used]
    print(f"[trends] {len(fresh)} fresh candidates")
    return rng.choice(fresh) if fresh else None
