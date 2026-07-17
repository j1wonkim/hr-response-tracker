"""Human Rights Watch event ingestion -- second source alongside Amnesty.

Added because Amnesty's ingestion (scrapers/amnesty.py) can structurally
reach almost none of Amnesty's own Action/Urgent Action content (see
DECISIONS.md, 2026-07-16). HRW has no equivalent gap: everything is one
content system, reachable in two polite requests per new item.

Two-phase ingestion, because HRW's RSS feed (https://www.hrw.org/rss/news)
carries only title/link/pubDate/guid -- no country/topic/news-type taxonomy,
unlike Amnesty's feed. That taxonomy only exists on the article page itself
(as clean, article-scoped tags -- verified against the live site on
2026-07-16, no cross-content noise the way Amnesty's article pages had):

  1. parse_feed_index() -- pure parse of the RSS feed into bare index items
     (title, url, published_at, guid).
  2. parse_article_page() -- pure parse of one article's HTML into a full
     HRWEvent (news type, country/region tags, topics, body text).
  3. fetch_events() -- network-touching orchestration: fetch the feed, then
     fetch+parse each item's article page, tolerating per-item failures.

Ingestion is narrowed to news type "News Release", "Statement", or
"Dispatches" (see NEWS_TYPE_INCLUDE) -- all three are dated pieces tied to
a specific incident, unlike Report/Background Briefing/UPR/Fact Sheet,
which document ongoing practices. Same rationale as Amnesty's Action/
Urgent Action filter; see DECISIONS.md. This taxonomy filter is not the
only scope check: it excludes by HRW's own news-type tag, but doesn't
distinguish content format -- a documentary-premiere announcement can
still be tagged "News Release" and pass through here. Excluding that kind
of item is scrapers/classify.py's job (the discrete-incident check), not
this filter's.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

from bs4 import BeautifulSoup

from scrapers.http import fetch_raw_cached

FEED_URL = "https://www.hrw.org/rss/news"

# HRW's own top-level region groupings, as observed in the /news filter
# facets on 2026-07-16. A "Region / Country" tag matching one of these is a
# region, not a country -- same reasoning as Amnesty's REGION_NAMES.
REGION_NAMES = {
    "Africa",
    "Americas",
    "Asia",
    "Europe/Central Asia",
    "Middle East/North Africa",
    "United States",
    "Global",
}

# Only these news types are discrete, datable events -- see DECISIONS.md.
# Excludes Report, Background Briefing, Fact Sheet, UPR, Journal Article,
# etc., which document ongoing practices rather than a single dated event.
# Note: this taxonomy filter does NOT screen out multimedia-format content
# (e.g. a documentary premiere announcement) -- HRW doesn't tag those
# distinctly, so they can pass this filter under a legitimate news type.
# That's handled downstream by scrapers/classify.py's discrete-incident
# check, not here -- see DECISIONS.md.
NEWS_TYPE_INCLUDE = {"News Release", "Statement", "Dispatches"}

# Elements that pollute extracted body text (share-button rows, tooltips'
# raw markup already handled by get_text) but aren't part of the article.
_BODY_NOISE_SELECTORS = ["[class*='minimal-share']", "[class*='ms-icon']"]


@dataclass
class HRWEvent:
    id: str
    title: str
    url: str
    published_at: datetime | None
    news_type: str
    countries: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    summary: str = ""
    body: str = ""
    source: str = "hrw"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "news_type": self.news_type,
            "countries": self.countries,
            "regions": self.regions,
            "topics": self.topics,
            "summary": self.summary,
            "body": self.body,
        }


@dataclass
class IndexItem:
    guid: str
    title: str
    url: str
    published_at: datetime | None


@dataclass
class IndexParseResult:
    items: list[IndexItem]
    skipped: list[dict]
    raw_items_seen: int


def parse_feed_index(raw_xml: str) -> IndexParseResult:
    """Pure parse of the RSS feed into bare index items -- no taxonomy, that
    only exists on the article page (see fetch_events)."""
    root = ET.fromstring(raw_xml)
    raw_items = root.findall(".//item")
    items: list[IndexItem] = []
    skipped: list[dict] = []
    for raw in raw_items:
        title = (raw.findtext("title") or "").strip()
        url = (raw.findtext("link") or "").strip()
        guid = (raw.findtext("guid") or "").strip() or url
        try:
            pub_date_raw = raw.findtext("pubDate")
            published_at = parsedate_to_datetime(pub_date_raw) if pub_date_raw else None
            items.append(IndexItem(guid=guid, title=title, url=url, published_at=published_at))
        except Exception as exc:
            skipped.append({"source": "hrw", "title": title or None, "guid": guid or None, "reason": f"{type(exc).__name__}: {exc}"})
    return IndexParseResult(items=items, skipped=skipped, raw_items_seen=len(raw_items))


def _tag_block_values(soup: BeautifulSoup, label: str) -> list[str]:
    """Read one of the article's own "Region / Country" / "Topic" tag-block
    sections by its heading text, not just by CSS class (the same
    `tag-block__region-link` class is reused for both sections)."""
    for block in soup.select(".tag-block"):
        title_el = block.select_one(".tag-block__region-title")
        if title_el and title_el.get_text(strip=True) == label:
            return [a.get_text(strip=True) for a in block.select(".tag-block__region-link")]
    return []


def parse_article_page(html: str, url: str, fallback: IndexItem | None = None) -> HRWEvent:
    """Pure parse of one HRW article page. `fallback` supplies title/date/
    guid from the RSS index if the page's own markup is missing them."""
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one(".news-header__title")
    title = title_el.get_text(strip=True) if title_el else (fallback.title if fallback else "")

    flag_el = soup.select_one(".news-header__flag")
    news_type = flag_el.get_text(strip=True) if flag_el else ""

    date_el = soup.select_one(".news-header__dateline-date")
    published_at = None
    if date_el and date_el.get("datetime"):
        published_at = datetime.fromisoformat(date_el["datetime"])
    elif fallback:
        published_at = fallback.published_at

    locations = _tag_block_values(soup, "Region / Country")
    countries = [name for name in locations if name not in REGION_NAMES]
    regions = [name for name in locations if name in REGION_NAMES]
    topics = _tag_block_values(soup, "Topic")

    subtitle_el = soup.select_one(".news-header__subtitle")
    summary = subtitle_el.get_text(strip=True) if subtitle_el else ""

    content_el = soup.select_one("article") or soup
    for noise in content_el.select(", ".join(_BODY_NOISE_SELECTORS)):
        noise.decompose()
    paragraphs = [
        p.get_text(strip=True)
        for p in content_el.find_all("p")
        if p.get_text(strip=True) and "news-header__subtitle" not in p.get("class", [])
    ]
    body = "\n\n".join(paragraphs)

    guid = fallback.guid if fallback else url

    return HRWEvent(
        id=guid,
        title=title,
        url=url,
        published_at=published_at,
        news_type=news_type,
        countries=countries,
        regions=regions,
        topics=topics,
        summary=summary or (paragraphs[0] if paragraphs else ""),
        body=body,
    )


@dataclass
class FetchResult:
    events: list[HRWEvent]
    skipped: list[dict]
    raw_items_seen: int


def fetch_events(
    cache_dir: Path,
    feed_max_age_hours: float = 20,
    article_max_age_hours: float = 24 * 7,
) -> FetchResult:
    """Network-touching orchestration: fetch the feed, then fetch+parse each
    item's article page. A single article failing to fetch/parse is
    recorded as skipped, not fatal to the run."""
    index = parse_feed_index(
        fetch_raw_cached(cache_dir / "feed.xml", url=FEED_URL, max_age_hours=feed_max_age_hours)
    )
    events: list[HRWEvent] = []
    skipped: list[dict] = list(index.skipped)

    for item in index.items:
        try:
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", item.url).strip("-")[-120:]
            html = fetch_raw_cached(
                cache_dir / f"article-{slug}.html",
                url=item.url,
                max_age_hours=article_max_age_hours,
            )
            events.append(parse_article_page(html, item.url, fallback=item))
        except Exception as exc:
            skipped.append({"source": "hrw", "title": item.title or None, "guid": item.guid or None, "reason": f"{type(exc).__name__}: {exc}"})

    return FetchResult(events=events, skipped=skipped, raw_items_seen=index.raw_items_seen)


def filter_by_news_type(events: list[HRWEvent], include: set[str] = NEWS_TYPE_INCLUDE) -> list[HRWEvent]:
    """Keep only events tagged with one of the given news types."""
    return [e for e in events if e.news_type in include]


def filter_by_start_date(events: list[HRWEvent], start_date: date) -> list[HRWEvent]:
    """Keep only events published on or after start_date. Bounds *initial
    ingestion* only -- this is not a retention policy, and events already
    ingested before this filter existed (or from a prior config value) are
    never re-checked or dropped by re-running it. Events with no known
    published_at are excluded rather than assumed in-range, since there's
    nothing to compare. See DECISIONS.md, "Bound initial HRW ingestion
    with a config-driven ingest_start_date"."""
    return [e for e in events if e.published_at is not None and e.published_at.date() >= start_date]


if __name__ == "__main__":
    from scrapers.config import load_pipeline_config
    from scrapers.report import build_run_report

    config = load_pipeline_config()
    result = fetch_events(Path(".cache/hrw"))
    events = filter_by_news_type(result.events)
    events = filter_by_start_date(events, config.ingest_start_date)

    out_path = Path("data/hrw_events.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([e.to_dict() for e in events], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {len(events)} events to {out_path}")

    report = build_run_report(
        source=(
            "scrapers.hrw (news_type in News Release, Statement; "
            f"ingest_start_date={config.ingest_start_date.isoformat()})"
        ),
        events=events,
        skipped=result.skipped,
        raw_items_seen=result.raw_items_seen,
    )
    report_path = Path("data/hrw_run_report.json")
    report_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print(report.summary_text())
