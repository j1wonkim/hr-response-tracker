"""Amnesty International event ingestion (pipeline stage 1, ingestion half only).

Fetches and parses Amnesty's global RSS feed (https://www.amnesty.org/en/feed/),
which covers /latest/news/ content and carries Amnesty's own structured
taxonomy (country/region, topic, content-type, resource-type) as custom
<amn:*> elements alongside the standard RSS fields. Using the feed instead of
scraping the HTML listing page means one polite request returns everything
needed, with cleaner data than guessing at CSS selectors.

Scope note: this module only extracts what's structurally present in the
feed (date, title, url, summary/body text, country/region tags). It does
NOT determine the perpetrating actor or filter to state-perpetrated
violations -- CLAUDE.md assigns that to a separate LLM classification call,
which is a later pipeline stage, not raw ingestion. Similarly, Amnesty's
feed does not distinguish "country" from "region" tags in <amn:countries>;
this module splits them using a small hardcoded list of Amnesty's known
region/subregion names (REGION_NAMES below), derived from the site's own
taxonomy as observed on 2026-07-16. Extend that list if Amnesty adds new
regions.
"""

from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

FEED_URL = "https://www.amnesty.org/en/feed/"

DEFAULT_USER_AGENT = (
    "hr-response-tracker/0.1 "
    "(+https://github.com/j1wonkim/hr-response-tracker)"
)

DEFAULT_CACHE_MAX_AGE_HOURS = 20

NAMESPACES = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "amn": "https://www.amnesty.org/en/",
}

# Amnesty's own continent/subregion taxonomy terms, as observed in
# <amn:countries> entries and the news-page country filter facets. Entries in
# <amn:countries> that match this list are regions, not countries.
REGION_NAMES = {
    "Africa",
    "Americas",
    "Asia and the Pacific",
    "Europe and Central Asia",
    "Middle East and North Africa",
    "East Africa, the Horn and Great Lakes",
    "Southern Africa",
    "West and Central Africa",
    "Central America and the Caribbean",
    "North America",
    "East Asia",
    "South Asia",
    "South-East Asia and the Pacific",
    "Eastern Europe and Central Asia",
    "North Africa",
}

_WP_EXCERPT_BOILERPLATE = re.compile(r"appeared first on", re.IGNORECASE)


@dataclass
class AmnestyEvent:
    id: str
    title: str
    url: str
    published_at: datetime | None
    countries: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    content_types: list[str] = field(default_factory=list)
    resource_types: list[str] = field(default_factory=list)
    summary: str = ""
    body: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "countries": self.countries,
            "regions": self.regions,
            "topics": self.topics,
            "content_types": self.content_types,
            "resource_types": self.resource_types,
            "summary": self.summary,
            "body": self.body,
        }


def clean_html(html_text: str) -> str:
    """Strip tags/entities from a feed HTML snippet and drop the trailing
    WordPress "The post X appeared first on Amnesty International." excerpt
    boilerplate, if present."""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    paragraphs = soup.find_all("p")
    if paragraphs and _WP_EXCERPT_BOILERPLATE.search(paragraphs[-1].get_text()):
        paragraphs[-1].decompose()
    text = soup.get_text(separator="\n\n").strip()
    return re.sub(r"\n{3,}", "\n\n", text)


def _names(item: ET.Element, path: str) -> list[str]:
    return [el.get("name", "").strip() for el in item.findall(path, NAMESPACES) if el.get("name")]


def _parse_item(item: ET.Element) -> AmnestyEvent:
    title = (item.findtext("title") or "").strip()
    url = (item.findtext("link") or "").strip()
    guid = (item.findtext("guid") or "").strip() or url

    pub_date_raw = item.findtext("pubDate")
    published_at = parsedate_to_datetime(pub_date_raw) if pub_date_raw else None

    locations = _names(item, "amn:countries/amn:id")
    countries = [name for name in locations if name not in REGION_NAMES]
    regions = [name for name in locations if name in REGION_NAMES]

    summary = clean_html(item.findtext("description") or "")
    body = clean_html(item.findtext("content:encoded", namespaces=NAMESPACES) or "") or summary

    return AmnestyEvent(
        id=guid,
        title=title,
        url=url,
        published_at=published_at,
        countries=countries,
        regions=regions,
        topics=_names(item, "amn:topics/amn:id"),
        content_types=_names(item, "amn:content-types/amn:id"),
        resource_types=_names(item, "amn:resource-types/amn:id"),
        summary=summary,
        body=body,
    )


def parse_events(raw_xml: str) -> list[AmnestyEvent]:
    """Pure parsing function -- takes raw RSS XML, returns events. No network
    calls, so it's the function fixture-based tests exercise."""
    root = ET.fromstring(raw_xml)
    return [_parse_item(item) for item in root.findall(".//item")]


def fetch_raw(url: str = FEED_URL, timeout: int = 15, user_agent: str = DEFAULT_USER_AGENT) -> str:
    response = requests.get(url, headers={"User-Agent": user_agent}, timeout=timeout)
    response.raise_for_status()
    return response.text


def fetch_raw_cached(
    cache_path: Path,
    url: str = FEED_URL,
    max_age_hours: float = DEFAULT_CACHE_MAX_AGE_HOURS,
    **kwargs,
) -> str:
    """Read from a local cache file if it's fresh enough, otherwise fetch and
    refresh the cache. Keeps the pipeline to one request per day per the
    "crawl once daily, cache aggressively" requirement."""
    if cache_path.exists():
        age_seconds = time.time() - cache_path.stat().st_mtime
        if age_seconds < max_age_hours * 3600:
            return cache_path.read_text(encoding="utf-8")

    raw = fetch_raw(url, **kwargs)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(raw, encoding="utf-8")
    return raw


if __name__ == "__main__":
    events = parse_events(fetch_raw_cached(Path(".cache/amnesty_feed.xml")))
    out_path = Path("data/amnesty_events.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([e.to_dict() for e in events], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {len(events)} events to {out_path}")
