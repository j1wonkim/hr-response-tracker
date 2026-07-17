from pathlib import Path

import pytest

from scrapers.amnesty import REGION_NAMES, clean_html, parse_events

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "amnesty" / "feed_sample.xml"


@pytest.fixture
def events():
    raw_xml = FIXTURE_PATH.read_text(encoding="utf-8")
    return parse_events(raw_xml)


def test_parses_all_items(events):
    assert len(events) == 5


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
