from datetime import datetime, timedelta, timezone

from scrapers.amnesty import AmnestyEvent
from scrapers.dedup import DATE_WINDOW_DAYS, TITLE_SIMILARITY_THRESHOLD, deduplicate_events
from scrapers.hrw import HRWEvent


def _amnesty(id_, title, published_at, countries):
    return AmnestyEvent(id=id_, title=title, url=f"https://amnesty.org/{id_}", published_at=published_at, countries=countries)


def _hrw(id_, title, published_at, countries):
    return HRWEvent(id=id_, title=title, url=f"https://hrw.org/{id_}", published_at=published_at, news_type="News Release", countries=countries)


NOW = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)


def test_cross_source_duplicate_is_merged():
    a = _amnesty("a1", "Libya: ICC Greenlights First Case to Move to Trial", NOW, ["Libya"])
    b = _hrw("h1", "Libya: ICC Greenlights First Case to Move to Trial", NOW + timedelta(days=1), ["Libya"])

    result = deduplicate_events([a, b])

    assert len(result.unique_events) == 1
    assert result.duplicates_removed == 1
    assert len(result.groups) == 1
    # earliest-published kept as primary
    assert result.unique_events[0].id == "a1"
    assert result.groups[0].duplicates[0].id == "h1"
    assert result.groups[0].matched_on[0]["shared_countries"] == ["Libya"]


def test_different_countries_not_merged():
    a = _amnesty("a1", "Government Cracks Down on Protesters", NOW, ["Egypt"])
    b = _hrw("h1", "Government Cracks Down on Protesters", NOW, ["Sudan"])

    result = deduplicate_events([a, b])

    assert len(result.unique_events) == 2
    assert result.duplicates_removed == 0


def test_dissimilar_titles_not_merged():
    a = _amnesty("a1", "Libya: ICC Greenlights First Case to Move to Trial", NOW, ["Libya"])
    b = _hrw("h1", "Tunisia: Migration Deal Worsening Human Rights Violations", NOW, ["Libya"])

    result = deduplicate_events([a, b])

    assert len(result.unique_events) == 2
    assert result.duplicates_removed == 0


def test_outside_date_window_not_merged():
    a = _amnesty("a1", "Libya: ICC Greenlights First Case to Move to Trial", NOW, ["Libya"])
    b = _hrw("h1", "Libya: ICC Greenlights First Case to Move to Trial", NOW + timedelta(days=DATE_WINDOW_DAYS + 1), ["Libya"])

    result = deduplicate_events([a, b])

    assert len(result.unique_events) == 2
    assert result.duplicates_removed == 0


def test_events_with_no_published_at_are_never_merged():
    a = _amnesty("a1", "Libya: ICC Greenlights First Case to Move to Trial", None, ["Libya"])
    b = _hrw("h1", "Libya: ICC Greenlights First Case to Move to Trial", None, ["Libya"])

    result = deduplicate_events([a, b])

    assert len(result.unique_events) == 2
    assert result.duplicates_removed == 0


def test_three_way_cluster_keeps_one_primary():
    a = _amnesty("a1", "Uganda: Military Seizing Government Critics", NOW, ["Uganda"])
    b = _hrw("h1", "Uganda: Military Seizing Government Critics", NOW + timedelta(hours=6), ["Uganda"])
    c = _amnesty("a2", "Uganda: Military Seizing Government Critics", NOW + timedelta(days=1), ["Uganda"])

    result = deduplicate_events([a, b, c])

    assert len(result.unique_events) == 1
    assert result.duplicates_removed == 2
    assert result.unique_events[0].id == "a1"


def test_unrelated_events_all_kept():
    a = _amnesty("a1", "Libya: ICC Greenlights First Case to Move to Trial", NOW, ["Libya"])
    b = _hrw("h1", "Peru: Veto Military Justice Bill", NOW, ["Peru"])
    c = _amnesty("a2", "Bangladesh: Landslides Deadly for Rohingya Refugees", NOW, ["Bangladesh"])

    result = deduplicate_events([a, b, c])

    assert len(result.unique_events) == 3
    assert result.duplicates_removed == 0
    assert result.groups == []


def test_title_similarity_threshold_is_the_documented_value():
    # sanity check that the module constant matches what the docstring claims
    assert TITLE_SIMILARITY_THRESHOLD == 0.6


def test_empty_event_list():
    result = deduplicate_events([])
    assert result.unique_events == []
    assert result.groups == []
    assert result.duplicates_removed == 0
