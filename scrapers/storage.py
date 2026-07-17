"""Persistent-state helpers for the ingestion pipeline.

The repo's committed data/events.json is this pipeline's durable state --
not the local, gitignored .cache/ directory, which is disposable scratch
space for polite re-fetching within a TTL window, not a record of what's
already been ingested. See DECISIONS.md, "Dedupe against committed data
instead of a post-hoc ingest_start_date filter".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_EVENTS_PATH = Path("data/events.json")


def load_committed_events(path: Path = DEFAULT_EVENTS_PATH) -> list[dict]:
    """Read already-committed events (raw dicts) from data/events.json.
    Returns [] if the file doesn't exist yet -- the first run has nothing
    committed, not an error."""
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_known_urls(path: Path = DEFAULT_EVENTS_PATH) -> set[str]:
    """URLs of already-committed events, for filter_new_events()."""
    return {e["url"] for e in load_committed_events(path) if e.get("url")}


def filter_new_events(events: list[Any], known_urls: set[str]) -> list[Any]:
    """Keep only events whose URL isn't already committed. Keyed on URL,
    not title/date, because URL is the one field HRW guarantees is stable
    and unique per article."""
    return [e for e in events if e.url not in known_urls]
