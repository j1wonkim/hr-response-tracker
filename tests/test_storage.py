from dataclasses import dataclass

from scrapers.storage import filter_new_events, load_committed_events, load_known_urls


@dataclass
class FakeEvent:
    url: str


def test_load_committed_events_returns_empty_list_when_file_missing(tmp_path):
    missing = tmp_path / "events.json"
    assert load_committed_events(missing) == []


def test_load_committed_events_reads_existing_file(tmp_path):
    path = tmp_path / "events.json"
    path.write_text('[{"url": "https://a"}, {"url": "https://b"}]', encoding="utf-8")

    events = load_committed_events(path)

    assert events == [{"url": "https://a"}, {"url": "https://b"}]


def test_load_known_urls_extracts_url_set(tmp_path):
    path = tmp_path / "events.json"
    path.write_text('[{"url": "https://a"}, {"url": "https://b"}]', encoding="utf-8")

    assert load_known_urls(path) == {"https://a", "https://b"}


def test_load_known_urls_empty_when_file_missing(tmp_path):
    assert load_known_urls(tmp_path / "nope.json") == set()


def test_filter_new_events_drops_already_committed_urls():
    events = [FakeEvent(url="https://a"), FakeEvent(url="https://b"), FakeEvent(url="https://c")]

    filtered = filter_new_events(events, known_urls={"https://a", "https://c"})

    assert [e.url for e in filtered] == ["https://b"]


def test_filter_new_events_keeps_all_when_nothing_known():
    events = [FakeEvent(url="https://a"), FakeEvent(url="https://b")]

    filtered = filter_new_events(events, known_urls=set())

    assert filtered == events
