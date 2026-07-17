"""Cross-source event deduplication (Amnesty + HRW, more as sources are added).

Two organizations often report on the same real-world incident within a
few days of each other. Left unmerged, that incident would produce two
rows in the event set, each separately eligible for event-statement
linking (stage 3) -- silently double-counting a single incident in the
response matrix.

This is a deterministic heuristic pass, NOT the LLM-verified
entity/embedding matching CLAUDE.md specifies for event-statement linking
(stage 3) -- no LLM infrastructure exists yet in this repo. Two events are
considered duplicates only if ALL of: they share at least one country,
their titles are similar (difflib ratio >= TITLE_SIMILARITY_THRESHOLD), and
they were published within DATE_WINDOW_DAYS of each other. Intentionally
conservative (favors under-merging over silently collapsing two distinct
events) until real cross-source duplicate examples are available to tune
against -- see DECISIONS.md.

Works on any event objects exposing .title, .published_at, .countries,
.source, .url, .id (both AmnestyEvent and HRWEvent qualify; no shared base
class required).
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Any

TITLE_SIMILARITY_THRESHOLD = 0.6
DATE_WINDOW_DAYS = 3


def _normalize_title(title: str) -> str:
    return " ".join(title.lower().split())


def _title_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _normalize_title(a), _normalize_title(b)).ratio()


def _is_duplicate_pair(a: Any, b: Any) -> tuple[bool, dict]:
    if a.published_at is None or b.published_at is None:
        return False, {}
    date_diff_days = abs((a.published_at - b.published_at).total_seconds()) / 86400
    if date_diff_days > DATE_WINDOW_DAYS:
        return False, {}
    shared_countries = sorted(set(a.countries) & set(b.countries))
    if not shared_countries:
        return False, {}
    similarity = _title_similarity(a.title, b.title)
    if similarity < TITLE_SIMILARITY_THRESHOLD:
        return False, {}
    return True, {
        "shared_countries": shared_countries,
        "title_similarity": round(similarity, 3),
        "date_diff_days": round(date_diff_days, 2),
    }


@dataclass
class DuplicateGroup:
    primary: Any
    duplicates: list[Any]
    matched_on: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "primary": {"source": self.primary.source, "id": self.primary.id, "url": self.primary.url, "title": self.primary.title},
            "duplicates": [{"source": d.source, "id": d.id, "url": d.url, "title": d.title} for d in self.duplicates],
            "matched_on": self.matched_on,
        }


@dataclass
class DedupResult:
    unique_events: list[Any]
    groups: list[DuplicateGroup]

    @property
    def duplicates_removed(self) -> int:
        return sum(len(g.duplicates) for g in self.groups)


def deduplicate_events(events: list[Any]) -> DedupResult:
    """Greedy clustering: for each not-yet-claimed event, pull in every
    later event that pairwise-matches it. Not a full transitive closure
    (if A~B and B~C but not A~C, C still joins A's cluster here) -- documented
    limitation, acceptable for a conservative first-pass heuristic.

    The earliest-published event in a cluster is kept as `primary`; the
    rest are recorded in `groups` (with what matched) but dropped from
    `unique_events`, so nothing is silently discarded -- callers wanting an
    audit trail can inspect `groups`.
    """
    unique: list[Any] = []
    groups: list[DuplicateGroup] = []
    claimed: set[int] = set()

    for i, event in enumerate(events):
        if i in claimed:
            continue
        cluster_indices = [i]
        matched_on: list[dict] = []
        for j in range(i + 1, len(events)):
            if j in claimed:
                continue
            is_dup, detail = _is_duplicate_pair(event, events[j])
            if is_dup:
                cluster_indices.append(j)
                matched_on.append(detail)

        if len(cluster_indices) > 1:
            cluster = sorted((events[k] for k in cluster_indices), key=lambda e: e.published_at)
            primary, duplicates = cluster[0], cluster[1:]
            groups.append(DuplicateGroup(primary=primary, duplicates=duplicates, matched_on=matched_on))
            unique.append(primary)
        else:
            unique.append(event)
        claimed.update(cluster_indices)

    return DedupResult(unique_events=unique, groups=groups)
