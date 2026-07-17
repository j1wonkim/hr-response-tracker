"""Run-report generation, shared across pipeline stages.

Each scraper/pipeline stage ends its run by producing a small report so a
human can sanity-check a run at a glance without reading the full dataset:
how many events came out the other end, what date range they span, how
they break down by country, and what (if anything) failed to parse. Reused
by future adapters -- pass any objects exposing `.published_at` (datetime
or None) and `.countries` (list[str]).

`feed_date_range` (optional) is the raw fetched feed's own date span --
distinct from `date_range`, which is the *final, filtered* events' span.
Callers that can cheaply compute it (see scrapers/hrw.py) should pass it
so cron frequency can be tuned against how far back each feed pull
actually reaches; see DECISIONS.md, "Redesign HRW crawl reliability".
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RunReport:
    source: str
    generated_at: str
    raw_items_seen: int
    events_found: int
    excluded_by_filter: int
    date_range: dict | None
    country_counts: dict
    skipped_count: int
    skipped: list = field(default_factory=list)
    duplicates_merged: int = 0
    feed_date_range: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    def summary_text(self) -> str:
        lines = [
            f"Run report -- {self.source}",
            f"Generated: {self.generated_at}",
            f"Raw items seen: {self.raw_items_seen}",
            f"Events found (final): {self.events_found}",
            f"Excluded by filter: {self.excluded_by_filter}",
            f"Duplicates merged: {self.duplicates_merged}",
        ]
        if self.date_range:
            lines.append(f"Date range: {self.date_range['earliest']} to {self.date_range['latest']}")
        else:
            lines.append("Date range: n/a (no dated events)")
        if self.feed_date_range:
            lines.append(
                f"Feed date span: {self.feed_date_range['earliest']} to {self.feed_date_range['latest']}"
            )
        else:
            lines.append("Feed date span: n/a")
        if self.country_counts:
            lines.append("Per-country counts:")
            for country, count in sorted(self.country_counts.items(), key=lambda kv: (-kv[1], kv[0])):
                lines.append(f"  {country}: {count}")
        else:
            lines.append("Per-country counts: none")
        lines.append(f"Skipped/unparseable items: {self.skipped_count}")
        for item in self.skipped:
            label = item.get("title") or item.get("guid") or "unknown"
            lines.append(f"  - {label}: {item.get('reason')}")
        return "\n".join(lines)


def compute_date_range(items: list[Any]) -> dict | None:
    """{'earliest': ..., 'latest': ...} over any objects exposing
    `.published_at`, or None if none are dated. Shared by build_run_report
    (for the final event list) and callers computing a raw feed's own
    date span (see scrapers/hrw.py)."""
    dated = [getattr(i, "published_at", None) for i in items]
    dated = [d for d in dated if d is not None]
    if not dated:
        return None
    return {"earliest": min(dated).isoformat(), "latest": max(dated).isoformat()}


def build_run_report(
    source: str,
    events: list[Any],
    skipped: list[dict],
    raw_items_seen: int,
    duplicates_merged: int = 0,
    feed_date_range: dict | None = None,
) -> RunReport:
    date_range = compute_date_range(events)

    counts: Counter = Counter()
    for event in events:
        counts.update(getattr(event, "countries", []))

    excluded_by_filter = raw_items_seen - len(events) - len(skipped) - duplicates_merged

    return RunReport(
        source=source,
        generated_at=datetime.now(timezone.utc).isoformat(),
        raw_items_seen=raw_items_seen,
        events_found=len(events),
        excluded_by_filter=excluded_by_filter,
        date_range=date_range,
        country_counts=dict(counts),
        skipped_count=len(skipped),
        skipped=skipped,
        duplicates_merged=duplicates_merged,
        feed_date_range=feed_date_range,
    )
