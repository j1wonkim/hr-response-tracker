from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from scrapers.hrw import (
    NEWS_TYPE_INCLUDE,
    REGION_NAMES,
    HRWEvent,
    filter_by_news_type,
    filter_by_start_date,
    parse_article_page,
    parse_feed_index,
)

FIXTURES = Path(__file__).parent / "fixtures" / "hrw"


@pytest.fixture
def index():
    raw_xml = (FIXTURES / "feed_sample.xml").read_text(encoding="utf-8")
    return parse_feed_index(raw_xml)


def test_index_parses_well_formed_items_and_skips_malformed(index):
    # 4 items in the fixture, 1 has a malformed pubDate and is skipped
    assert index.raw_items_seen == 4
    assert len(index.items) == 3
    assert len(index.skipped) == 1
    assert index.skipped[0]["title"] == "Fixture: item with malformed pubDate for skip testing"


def test_index_basic_fields(index):
    libya = next(i for i in index.items if "Libya" in i.title)
    assert libya.url == "https://www.hrw.org/news/2026/07/16/libya-icc-greenlights-first-case-to-move-to-trial"
    assert libya.guid == libya.url
    assert libya.published_at is not None
    assert libya.published_at.year == 2026


def test_parse_article_page_news_release(index):
    libya = next(i for i in index.items if "Libya" in i.title)
    html = (FIXTURES / "article_libya.html").read_text(encoding="utf-8")
    event = parse_article_page(html, libya.url, fallback=libya)

    assert event.title == "Libya: ICC Greenlights First Case to Move to Trial"
    assert event.news_type == "News Release"
    assert event.countries == ["Libya"]
    assert event.regions == []
    assert set(event.topics) == {"International Criminal Court", "International Justice"}
    assert event.published_at.year == 2026
    assert event.published_at.month == 7
    assert event.published_at.day == 16
    assert event.summary == "Libyan Authorities Should Surrender Other Suspects to the Court"
    # share-button paragraph must not leak into body text
    assert "Share this via Facebook" not in event.body
    assert "El Hishri" in event.body


def test_parse_article_page_splits_countries_and_regions(index):
    sudan = next(i for i in index.items if "Sudan" in i.title)
    html = (FIXTURES / "article_statement.html").read_text(encoding="utf-8")
    event = parse_article_page(html, sudan.url, fallback=sudan)

    assert event.news_type == "Statement"
    assert set(event.countries) == {"Sudan", "Chad"}
    assert event.regions == ["Africa"]
    for name in event.regions:
        assert name in REGION_NAMES


def test_parse_article_page_report_type(index):
    ukraine = next(i for i in index.items if "Ukraine" in i.title)
    html = (FIXTURES / "article_report.html").read_text(encoding="utf-8")
    event = parse_article_page(html, ukraine.url, fallback=ukraine)
    assert event.news_type == "Report"


def test_filter_by_news_type_keeps_only_news_release_and_statement(index):
    events = []
    for title_fragment, fixture in [("Libya", "article_libya.html"), ("Sudan", "article_statement.html"), ("Ukraine", "article_report.html")]:
        item = next(i for i in index.items if title_fragment in i.title)
        html = (FIXTURES / fixture).read_text(encoding="utf-8")
        events.append(parse_article_page(html, item.url, fallback=item))

    filtered = filter_by_news_type(events)
    types = {e.news_type for e in filtered}
    assert types == {"News Release", "Statement"}
    assert "Report" not in types
    assert set(NEWS_TYPE_INCLUDE) == {"News Release", "Statement"}


def _make_event(published_at):
    return HRWEvent(
        id="id",
        title="title",
        url="https://www.hrw.org/news/x",
        published_at=published_at,
        news_type="News Release",
    )


def test_filter_by_start_date_keeps_on_or_after_and_drops_before():
    events = [
        _make_event(datetime(2025, 12, 31, tzinfo=timezone.utc)),  # before
        _make_event(datetime(2026, 1, 1, tzinfo=timezone.utc)),  # on the boundary
        _make_event(datetime(2026, 7, 16, tzinfo=timezone.utc)),  # after
    ]

    filtered = filter_by_start_date(events, date(2026, 1, 1))

    assert len(filtered) == 2
    assert all(e.published_at.date() >= date(2026, 1, 1) for e in filtered)


def test_filter_by_start_date_drops_events_with_no_published_at():
    events = [_make_event(None), _make_event(datetime(2026, 7, 16, tzinfo=timezone.utc))]

    filtered = filter_by_start_date(events, date(2026, 1, 1))

    assert len(filtered) == 1
    assert filtered[0].published_at is not None


def test_parse_article_page_falls_back_to_index_fields_when_markup_missing():
    from scrapers.hrw import IndexItem
    from datetime import datetime, timezone

    fallback = IndexItem(
        guid="https://www.hrw.org/news/2026/01/01/minimal",
        title="Fallback Title",
        url="https://www.hrw.org/news/2026/01/01/minimal",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    event = parse_article_page("<html><body><article></article></body></html>", fallback.url, fallback=fallback)
    assert event.title == "Fallback Title"
    assert event.published_at == fallback.published_at
    assert event.news_type == ""
    assert event.countries == []
    assert event.regions == []
