"""Shared polite-fetch helper, reused by every scraper (Amnesty, HRW, ...).

One place for the User-Agent string and the on-disk cache so "crawl once
daily, cache aggressively" (CLAUDE.md) is enforced consistently rather than
reimplemented per source.
"""

from __future__ import annotations

import time
from pathlib import Path

import requests

DEFAULT_USER_AGENT = (
    "hr-response-tracker/0.1 "
    "(+https://github.com/j1wonkim/hr-response-tracker)"
)

DEFAULT_CACHE_MAX_AGE_HOURS = 20


def fetch_raw(url: str, timeout: int = 15, user_agent: str = DEFAULT_USER_AGENT) -> str:
    response = requests.get(url, headers={"User-Agent": user_agent}, timeout=timeout)
    response.raise_for_status()
    return response.text


def fetch_raw_cached(
    cache_path: Path,
    url: str,
    max_age_hours: float = DEFAULT_CACHE_MAX_AGE_HOURS,
    **kwargs,
) -> str:
    """Read from a local cache file if it's fresh enough, otherwise fetch and
    refresh the cache."""
    if cache_path.exists():
        age_seconds = time.time() - cache_path.stat().st_mtime
        if age_seconds < max_age_hours * 3600:
            return cache_path.read_text(encoding="utf-8")

    raw = fetch_raw(url, **kwargs)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(raw, encoding="utf-8")
    return raw
