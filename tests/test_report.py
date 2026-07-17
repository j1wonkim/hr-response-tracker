from dataclasses import dataclass
from datetime import datetime, timezone

from scrapers.report import build_run_report, compute_date_range


@dataclass
class FakeEvent:
    published_at: datetime | None
    countries: list


def test_compute_date_range_returns_none_for_empty_list():
    assert compute_date_range([]) is None


def test_compute_date_range_ignores_undated_items():
    items = [
        FakeEvent(published_at=None, countries=[]),
        FakeEvent(published_at=datetime(2026, 7, 10, tzinfo=timezone.utc), countries=[]),
        FakeEvent(published_at=datetime(2026, 7, 16, tzinfo=timezone.utc), countries=[]),
    ]
    result = compute_date_range(items)
    assert result == {
        "earliest": datetime(2026, 7, 10, tzinfo=timezone.utc).isoformat(),
        "latest": datetime(2026, 7, 16, tzinfo=timezone.utc).isoformat(),
    }


def test_build_run_report_includes_feed_date_range_when_given():
    events = [FakeEvent(published_at=datetime(2026, 7, 16, tzinfo=timezone.utc), countries=["Libya"])]
    feed_span = {"earliest": "2026-07-01T00:00:00+00:00", "latest": "2026-07-16T00:00:00+00:00"}

    report = build_run_report(
        source="test",
        events=events,
        skipped=[],
        raw_items_seen=1,
        feed_date_range=feed_span,
    )

    assert report.feed_date_range == feed_span
    assert "Feed date span: 2026-07-01T00:00:00+00:00 to 2026-07-16T00:00:00+00:00" in report.summary_text()


def test_build_run_report_feed_date_range_defaults_to_none():
    report = build_run_report(source="test", events=[], skipped=[], raw_items_seen=0)

    assert report.feed_date_range is None
    assert "Feed date span: n/a" in report.summary_text()
