from pathlib import Path

from scrapers.mofa import parse_feed

FIXTURES = Path(__file__).parent / "fixtures" / "mofa"


def test_parse_press_releases_feed():
    raw_xml = (FIXTURES / "feed_press_releases.xml").read_text(encoding="utf-8")

    result = parse_feed(raw_xml, board="press_releases")

    assert result.raw_items_seen == 3
    assert len(result.statements) == 3
    assert result.skipped == []

    first = result.statements[0]
    assert first.board == "press_releases"
    assert first.source == "mofa"
    assert first.countries == ["South Korea"]
    assert first.title == "Korean Government Provides Humanitarian Assistance to Venezuela Following Earthquake"
    assert first.url == "http://www.mofa.go.kr/www/brd/m_5676/view.do?seq=323320"
    assert first.id == first.url
    assert first.published_at is not None
    assert first.published_at.year == 2026
    assert first.published_at.month == 6
    assert first.published_at.day == 26
    assert "USD5 million in humanitarian assistance" in first.full_text


def test_parse_press_briefings_feed():
    raw_xml = (FIXTURES / "feed_press_briefings.xml").read_text(encoding="utf-8")

    result = parse_feed(raw_xml, board="press_briefings")

    assert result.raw_items_seen == 3
    assert len(result.statements) == 3

    first = result.statements[0]
    assert first.board == "press_briefings"
    assert first.title == "Spokesperson's Press Briefing (July 14, 2026)"
    # A whole multi-topic briefing transcript is one statement, not split
    # per topic -- that's stage 3's (linking) job, not ingestion's.
    assert "ASEAN-related Foreign Ministers" in first.full_text
    assert "Mongolia" not in first.full_text


def test_parse_feed_skips_item_with_no_link():
    raw_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
      <channel>
        <item>
          <title>Missing link</title>
          <content:encoded>Some text.</content:encoded>
          <pubDate>Mon, 06 Jul 2026 21:57:47 GMT</pubDate>
        </item>
        <item>
          <title>Valid item</title>
          <link>http://www.mofa.go.kr/www/brd/m_5676/view.do?seq=1</link>
          <content:encoded>Other text.</content:encoded>
          <pubDate>Mon, 06 Jul 2026 21:57:47 GMT</pubDate>
        </item>
      </channel>
    </rss>"""

    result = parse_feed(raw_xml, board="press_releases")

    assert result.raw_items_seen == 2
    assert len(result.statements) == 1
    assert result.statements[0].title == "Valid item"
    assert len(result.skipped) == 1
    assert result.skipped[0]["title"] == "Missing link"


def test_parse_feed_handles_missing_pubdate():
    raw_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
      <channel>
        <item>
          <title>No date</title>
          <link>http://www.mofa.go.kr/www/brd/m_5676/view.do?seq=2</link>
          <content:encoded>Text.</content:encoded>
        </item>
      </channel>
    </rss>"""

    result = parse_feed(raw_xml, board="press_releases")

    assert len(result.statements) == 1
    assert result.statements[0].published_at is None
