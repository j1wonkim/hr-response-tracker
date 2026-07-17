"""Crawl-coverage overlap check.

scrapers/hrw.py fetches a single, un-paginated RSS response each run --
there is no backward crawl and no persistent cursor (see DECISIONS.md,
"Redesign HRW crawl reliability"). The only thing standing between "daily
crawl" and "silently missed events" is HRW's feed staying wide enough to
always overlap with our last successful crawl. This module checks that
assumption after every run and, if it ever breaks, opens a GitHub issue
rather than silently trusting it.

Known limitation, logged deliberately rather than fixed speculatively:
this check compares against the newest *committed* (i.e. classified/
passing) event, not a raw crawl log of every URL ever seen. An event HRW
published but that failed classification doesn't count as "coverage" --
which biases the check toward firing too eagerly, not toward silently
missing a real gap, but it does mean the check has never actually fired
in practice yet. Treat the underlying risk (a gap between two crawls
wider than HRW's feed window) as a known limitation until this check
actually fires once and that firing is verified against real evidence of
a gap.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

DEFAULT_REPO = "j1wonkim/hr-response-tracker"
COVERAGE_GAP_LABEL = "coverage-gap"


@dataclass
class CoverageCheckResult:
    gap_detected: bool
    oldest_fetched: datetime | None
    newest_stored: datetime | None
    message: str


def check_coverage_overlap(
    feed_items: list[Any], stored_events: list[dict]
) -> CoverageCheckResult:
    """Compares the oldest item in this run's raw feed fetch (before any
    filtering) against the newest already-committed event. If the feed's
    oldest item is newer than our newest stored event, the feed's rolling
    window has moved past what we last captured -- there's a real chance
    items published in between were never seen by any crawl."""
    fetched_dates = [i.published_at for i in feed_items if i.published_at is not None]
    stored_dates = [
        datetime.fromisoformat(e["published_at"])
        for e in stored_events
        if e.get("published_at")
    ]

    if not fetched_dates or not stored_dates:
        return CoverageCheckResult(
            gap_detected=False,
            oldest_fetched=min(fetched_dates) if fetched_dates else None,
            newest_stored=max(stored_dates) if stored_dates else None,
            message="Not enough data to check overlap (first run, or an empty feed/store).",
        )

    oldest_fetched = min(fetched_dates)
    newest_stored = max(stored_dates)
    gap = oldest_fetched > newest_stored

    message = (
        f"Coverage gap: this run's oldest feed item ({oldest_fetched.isoformat()}) "
        f"is newer than the newest stored event ({newest_stored.isoformat()}) -- "
        "items published in between may have been missed."
        if gap
        else (
            f"No coverage gap: this run's oldest feed item ({oldest_fetched.isoformat()}) "
            f"overlaps with the newest stored event ({newest_stored.isoformat()})."
        )
    )
    return CoverageCheckResult(
        gap_detected=gap, oldest_fetched=oldest_fetched, newest_stored=newest_stored, message=message
    )


def _has_open_coverage_gap_issue(token: str, repo: str) -> bool:
    response = requests.get(
        f"https://api.github.com/repos/{repo}/issues",
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
        params={"labels": COVERAGE_GAP_LABEL, "state": "open"},
        timeout=15,
    )
    response.raise_for_status()
    return len(response.json()) > 0


def open_coverage_gap_issue(result: CoverageCheckResult) -> str | None:
    """Opens a GitHub issue via the REST API if a coverage gap was
    detected and a GITHUB_TOKEN is available. Mirrors
    scrapers/classify.py's MissingCredentialsError pattern: no token means
    a loud skip, not a silent no-op or a hard failure, so `docker run`
    still works out of the box without GitHub credentials. Skips filing a
    duplicate if a coverage-gap issue is already open, so a persistent gap
    doesn't file a new issue every single day.

    Repo is read from GITHUB_REPOSITORY (the env var GitHub Actions sets
    automatically to the running repo's own owner/name) so a fork's
    automated runs file issues on the fork, not on this project's repo."""
    if not result.gap_detected:
        return None

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print(f"COVERAGE GAP ISSUE NOT FILED: GITHUB_TOKEN is not set. {result.message}")
        return None

    repo = os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO)

    if _has_open_coverage_gap_issue(token, repo):
        print(f"COVERAGE GAP ISSUE NOT FILED: an open '{COVERAGE_GAP_LABEL}' issue already exists. {result.message}")
        return None

    response = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
        json={
            "title": f"Possible HRW crawl coverage gap detected ({datetime.now(timezone.utc).date().isoformat()})",
            "body": (
                f"{result.message}\n\n"
                "Automated coverage check (scrapers/coverage.py), run after event "
                "ingestion, found that this run's fetched feed no longer overlaps "
                "with the newest previously committed event. This can mean HRW "
                "published more items than one feed pull captures between two "
                "crawls, or a crawl was skipped/delayed longer than expected. See "
                "DECISIONS.md, \"Redesign HRW crawl reliability\" for context and "
                "known limitations of this check."
            ),
            "labels": [COVERAGE_GAP_LABEL, "automated"],
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json().get("html_url")
