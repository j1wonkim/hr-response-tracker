from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from scrapers.coverage import check_coverage_overlap, open_coverage_gap_issue


@dataclass
class FakeIndexItem:
    published_at: datetime | None


def test_check_coverage_overlap_no_gap_when_feed_reaches_last_stored_event():
    feed_items = [
        FakeIndexItem(datetime(2026, 7, 10, tzinfo=timezone.utc)),
        FakeIndexItem(datetime(2026, 7, 16, tzinfo=timezone.utc)),
    ]
    stored_events = [{"published_at": "2026-07-12T00:00:00+00:00"}]

    result = check_coverage_overlap(feed_items, stored_events)

    assert result.gap_detected is False
    assert result.oldest_fetched == datetime(2026, 7, 10, tzinfo=timezone.utc)
    assert result.newest_stored == datetime(2026, 7, 12, tzinfo=timezone.utc)


def test_check_coverage_overlap_detects_gap_when_feed_starts_after_last_stored_event():
    feed_items = [
        FakeIndexItem(datetime(2026, 7, 15, tzinfo=timezone.utc)),
        FakeIndexItem(datetime(2026, 7, 16, tzinfo=timezone.utc)),
    ]
    stored_events = [{"published_at": "2026-07-10T00:00:00+00:00"}]

    result = check_coverage_overlap(feed_items, stored_events)

    assert result.gap_detected is True
    assert "Coverage gap" in result.message


def test_check_coverage_overlap_no_gap_on_first_run_with_no_stored_events():
    feed_items = [FakeIndexItem(datetime(2026, 7, 16, tzinfo=timezone.utc))]

    result = check_coverage_overlap(feed_items, stored_events=[])

    assert result.gap_detected is False
    assert result.newest_stored is None


def test_check_coverage_overlap_ignores_items_with_no_date():
    feed_items = [FakeIndexItem(None), FakeIndexItem(datetime(2026, 7, 16, tzinfo=timezone.utc))]
    stored_events = [{"published_at": None}, {"published_at": "2026-07-10T00:00:00+00:00"}]

    result = check_coverage_overlap(feed_items, stored_events)

    assert result.oldest_fetched == datetime(2026, 7, 16, tzinfo=timezone.utc)
    assert result.newest_stored == datetime(2026, 7, 10, tzinfo=timezone.utc)


def test_open_coverage_gap_issue_returns_none_when_no_gap():
    result = check_coverage_overlap(
        [FakeIndexItem(datetime(2026, 7, 10, tzinfo=timezone.utc))],
        [{"published_at": "2026-07-12T00:00:00+00:00"}],
    )
    assert open_coverage_gap_issue(result) is None


def test_open_coverage_gap_issue_skips_without_github_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = check_coverage_overlap(
        [FakeIndexItem(datetime(2026, 7, 15, tzinfo=timezone.utc))],
        [{"published_at": "2026-07-10T00:00:00+00:00"}],
    )

    assert open_coverage_gap_issue(result) is None


def test_open_coverage_gap_issue_files_issue_when_gap_and_token_present(monkeypatch):
    import scrapers.coverage as coverage

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "someone/their-fork")

    class FakeGetResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return []  # no existing open issues

    class FakePostResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"html_url": "https://github.com/someone/their-fork/issues/1"}

    calls = []

    def fake_get(url, **kwargs):
        calls.append(("GET", url, kwargs))
        return FakeGetResponse()

    def fake_post(url, **kwargs):
        calls.append(("POST", url, kwargs))
        return FakePostResponse()

    monkeypatch.setattr(coverage.requests, "get", fake_get)
    monkeypatch.setattr(coverage.requests, "post", fake_post)

    result = check_coverage_overlap(
        [FakeIndexItem(datetime(2026, 7, 15, tzinfo=timezone.utc))],
        [{"published_at": "2026-07-10T00:00:00+00:00"}],
    )

    issue_url = open_coverage_gap_issue(result)

    assert issue_url == "https://github.com/someone/their-fork/issues/1"
    assert calls[0][0] == "GET"
    assert "someone/their-fork" in calls[0][1]
    assert calls[1][0] == "POST"
    assert "someone/their-fork" in calls[1][1]


def test_open_coverage_gap_issue_skips_when_one_already_open(monkeypatch):
    import scrapers.coverage as coverage

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    class FakeGetResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return [{"number": 42}]  # an open coverage-gap issue already exists

    post_calls = []

    monkeypatch.setattr(coverage.requests, "get", lambda url, **kwargs: FakeGetResponse())
    monkeypatch.setattr(coverage.requests, "post", lambda url, **kwargs: post_calls.append(url))

    result = check_coverage_overlap(
        [FakeIndexItem(datetime(2026, 7, 15, tzinfo=timezone.utc))],
        [{"published_at": "2026-07-10T00:00:00+00:00"}],
    )

    assert open_coverage_gap_issue(result) is None
    assert post_calls == []
