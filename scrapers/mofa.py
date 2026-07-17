"""South Korea Ministry of Foreign Affairs (MOFA) response monitoring --
the first ministry-side adapter (CLAUDE.md stage 2).

Two RSS feeds, not one: MOFA's broadest, most-relevant-looking board
("Ministry News", m_5674) has no RSS feed at all, so this adapter crawls
the two sibling boards that do -- Press Releases (m_5676) and Press
Briefings (m_5679) -- rather than HTML-scrape a listing page with no feed
and no stability guarantee. See "South Korea MFA: use Press Releases +
Press Briefings via RSS, not Ministry News" in DECISIONS.md.

Unlike scrapers/hrw.py, this is single-phase: each feed's <content:encoded>
already carries the full statement text (a press release's full body, or
an entire day's spokesperson briefing transcript -- MOFA does not split
multi-topic briefings into separate feed items), so there's no second
article-page fetch. Every feed item becomes one MinistryStatement; per
CLAUDE.md stage 2, storage is date/source/full text/URL -- figuring out
which specific event(s) a multi-topic briefing actually addresses is
stage 3's job (linking), not ingestion's.

Confirmed live on 2026-07-17: robots.txt allows crawling both boards for
this project's User-Agent, and both feeds serve `Content-Type:
application/rss+xml` with no charset param -- `requests`' apparent_encoding
still correctly detects UTF-8 (verified against real curly-quote and
Korean-language content), so no special decoding is needed here.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

from scrapers.http import fetch_raw_cached

CONTENT_ENCODED_TAG = "{http://purl.org/rss/1.0/modules/content/}encoded"

# board id -> RSS feed URL. Both confirmed live and robots.txt-permitted
# on 2026-07-17.
FEEDS = {
    "press_releases": "http://www.mofa.go.kr/www/brd/rss.do?brdId=302",
    "press_briefings": "http://www.mofa.go.kr/www/brd/rss.do?brdId=303",
}


@dataclass
class MinistryStatement:
    id: str
    title: str
    url: str
    published_at: datetime | None
    board: str
    full_text: str
    source: str = "mofa"
    # Note: unlike HRWEvent.countries (the target/victim country of a
    # violation), this is the *responding* country the statement is
    # attributed to -- always South Korea for this adapter. Still exposed
    # as `countries` so scrapers/report.py's build_run_report() can reuse
    # its per-country tally as-is once more ministry adapters exist.
    countries: list[str] = field(default_factory=lambda: ["South Korea"])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "board": self.board,
            "title": self.title,
            "url": self.url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "countries": self.countries,
            "full_text": self.full_text,
        }


@dataclass
class ParseResult:
    statements: list[MinistryStatement]
    skipped: list[dict]
    raw_items_seen: int


def parse_feed(raw_xml: str, board: str) -> ParseResult:
    """Pure parse of one MOFA RSS feed into MinistryStatements. No
    article-page fetch needed -- content:encoded already carries the full
    text."""
    root = ET.fromstring(raw_xml)
    raw_items = root.findall(".//item")
    statements: list[MinistryStatement] = []
    skipped: list[dict] = []
    for raw in raw_items:
        title = (raw.findtext("title") or "").strip()
        url = (raw.findtext("link") or "").strip()
        full_text = (raw.findtext(CONTENT_ENCODED_TAG) or "").strip()
        try:
            if not url:
                raise ValueError("item has no <link>")
            pub_date_raw = raw.findtext("pubDate")
            published_at = parsedate_to_datetime(pub_date_raw) if pub_date_raw else None
            statements.append(
                MinistryStatement(
                    id=url,
                    title=title,
                    url=url,
                    published_at=published_at,
                    board=board,
                    full_text=full_text,
                )
            )
        except Exception as exc:
            skipped.append(
                {
                    "source": "mofa",
                    "title": title or None,
                    "guid": url or None,
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )
    return ParseResult(statements=statements, skipped=skipped, raw_items_seen=len(raw_items))


@dataclass
class FetchResult:
    statements: list[MinistryStatement]
    skipped: list[dict]
    raw_items_seen: int


def fetch_statements(cache_dir: Path, feed_max_age_hours: float = 20) -> FetchResult:
    """Network-touching orchestration: fetch + parse both feeds, tolerating
    one feed failing without losing the other."""
    statements: list[MinistryStatement] = []
    skipped: list[dict] = []
    raw_items_seen = 0
    for board, url in FEEDS.items():
        try:
            raw_xml = fetch_raw_cached(
                cache_dir / f"feed_{board}.xml", url=url, max_age_hours=feed_max_age_hours
            )
            result = parse_feed(raw_xml, board=board)
            statements.extend(result.statements)
            skipped.extend(result.skipped)
            raw_items_seen += result.raw_items_seen
        except Exception as exc:
            skipped.append(
                {
                    "source": "mofa",
                    "title": None,
                    "guid": None,
                    "reason": f"{type(exc).__name__}: {exc} (board={board})",
                }
            )
    return FetchResult(statements=statements, skipped=skipped, raw_items_seen=raw_items_seen)


if __name__ == "__main__":
    from scrapers.report import build_run_report

    result = fetch_statements(Path(".cache/mofa"))

    out_path = Path("data/mofa_statements.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([s.to_dict() for s in result.statements], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {len(result.statements)} statements to {out_path}")

    report = build_run_report(
        source="scrapers.mofa (press_releases + press_briefings, RSS)",
        events=result.statements,
        skipped=result.skipped,
        raw_items_seen=result.raw_items_seen,
    )
    report_path = Path("data/mofa_run_report.json")
    report_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print(report.summary_text())
