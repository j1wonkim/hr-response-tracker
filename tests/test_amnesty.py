from pathlib import Path

import pytest

from scrapers.amnesty import (
    REGION_NAMES,
    RESOURCE_TYPE_INCLUDE,
    clean_html,
    filter_by_resource_type,
    parse_events,
    parse_feed,
)
from scrapers.report import build_run_report

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "amnesty" / "feed_sample.xml"
RAW_XML = FIXTURE_PATH.read_text(encoding="utf-8")


@pytest.fixture
def events():
    return parse_events(RAW_XML)


def test_parses_all_well_formed_items(events):
    # 7 items in the fixture, 1 has a malformed pubDate and is skipped
    assert len(events) == 6


def test_basic_fields(events):
    myanmar = next(e for e in events if "Myanmar" in e.title)
    assert myanmar.url == (
        "https://www.amnesty.org/en/latest/news/2026/07/"
        "myanmar-reported-sea-tragedies-highlight-desperate-choices-facing-rohingya/"
    )
    assert myanmar.id == "https://www.amnesty.org/en/?p=240715"
    assert myanmar.published_at is not None
    assert myanmar.published_at.year == 2026
    assert myanmar.published_at.month == 7
    assert myanmar.published_at.day == 16


def test_countries_and_regions_are_split(events):
    myanmar = next(e for e in events if "Myanmar" in e.title)
    assert set(myanmar.countries) == {"Bangladesh", "Myanmar"}
    assert set(myanmar.regions) == {
        "Asia and the Pacific",
        "South Asia",
        "South-East Asia and the Pacific",
    }
    # sanity: every region name used in the fixture is actually in REGION_NAMES
    for name in myanmar.regions:
        assert name in REGION_NAMES


def test_event_with_only_region_level_tags_has_no_countries(events):
    african_court = next(e for e in events if "African Court" in e.title)
    assert african_court.countries == []
    assert set(african_court.regions) == {
        "Africa",
        "East Africa, the Horn and Great Lakes",
        "Southern Africa",
        "West and Central Africa",
    }


def test_multiple_content_types(events):
    el_salvador = next(e for e in events if "El Salvador" in e.title)
    assert set(el_salvador.content_types) == {"News", "Press Release"}


def test_missing_resource_types_defaults_to_empty_list(events):
    myanmar = next(e for e in events if "Myanmar" in e.title)
    assert myanmar.resource_types == []


def test_summary_strips_wp_boilerplate_and_html_tags(events):
    myanmar = next(e for e in events if "Myanmar" in e.title)
    assert "<p>" not in myanmar.summary
    assert "appeared first on" not in myanmar.summary
    assert "Rohingya" in myanmar.summary


def test_body_falls_back_to_summary_when_no_content_encoded(events):
    fixture_item = next(e for e in events if e.title.startswith("Fixture:"))
    assert fixture_item.body == fixture_item.summary
    assert fixture_item.countries == []
    assert fixture_item.regions == []
    assert fixture_item.topics == []
    assert fixture_item.content_types == ["News"]


def test_clean_html_keeps_paragraph_without_boilerplate():
    text = clean_html("<p>Just a plain paragraph.</p>")
    assert text == "Just a plain paragraph."


def test_clean_html_drops_trailing_wp_excerpt_paragraph():
    html = (
        "<p>Real content here.</p>"
        '<p>The post <a href="#">Title</a> appeared first on '
        '<a href="#">Amnesty International</a>.</p>'
    )
    text = clean_html(html)
    assert "Real content here." in text
    assert "appeared first on" not in text


def test_clean_html_empty_input():
    assert clean_html("") == ""


def test_parse_events_empty_feed():
    empty_rss = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel><title>Empty</title></channel></rss>'
    )
    assert parse_events(empty_rss) == []


def test_parse_feed_skips_malformed_item_instead_of_raising():
    result = parse_feed(RAW_XML)
    assert result.raw_items_seen == 7
    assert len(result.events) == 6
    assert len(result.skipped) == 1
    skipped = result.skipped[0]
    assert skipped["title"] == "Fixture: item with malformed pubDate for skip testing"
    assert "pubDate" not in skipped["reason"]  # sanity: reason is the exception, not a literal
    assert skipped["reason"]  # non-empty


def test_filter_by_resource_type_keeps_only_action_and_urgent_action(events):
    filtered = filter_by_resource_type(events)
    assert len(filtered) == 1
    assert filtered[0].title.startswith("Egypt: Further Information")
    assert set(filtered[0].resource_types) & RESOURCE_TYPE_INCLUDE


def test_filter_by_resource_type_excludes_press_release_and_untagged(events):
    filtered = filter_by_resource_type(events)
    titles = {e.title for e in filtered}
    assert not any("El Salvador" in t for t in titles)  # Press Release
    assert not any("Myanmar" in t for t in titles)  # no resource-types at all


def test_build_run_report_counts_and_date_range(events):
    filtered = filter_by_resource_type(events)
    report = build_run_report(
        source="test",
        events=filtered,
        skipped=[{"title": "x", "guid": None, "reason": "boom"}],
        raw_items_seen=7,
    )
    assert report.events_found == 1
    assert report.raw_items_seen == 7
    assert report.skipped_count == 1
    assert report.country_counts == {"Egypt": 1}
    assert report.date_range == {
        "earliest": filtered[0].published_at.isoformat(),
        "latest": filtered[0].published_at.isoformat(),
    }
    # events_found + skipped + excluded_by_filter should account for every raw item
    assert report.events_found + report.skipped_count + report.excluded_by_filter == 7


def test_build_run_report_handles_no_events():
    report = build_run_report(source="test", events=[], skipped=[], raw_items_seen=0)
    assert report.events_found == 0
    assert report.date_range is None
    assert report.country_counts == {}
    assert "Date range: n/a" in report.summary_text()
