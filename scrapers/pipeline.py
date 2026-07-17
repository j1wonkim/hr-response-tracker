"""Combined event-ingestion pipeline: Amnesty + HRW, filtered, deduplicated,
reported as one run.

This is the "run everything and tell me what happened" entrypoint --
individual sources can still be run standalone via `python -m
scrapers.amnesty` / `python -m scrapers.hrw` for debugging one source in
isolation.
"""

from __future__ import annotations

import json
from pathlib import Path

from scrapers.amnesty import FEED_URL as AMNESTY_FEED_URL
from scrapers.amnesty import filter_by_resource_type, parse_feed
from scrapers.dedup import deduplicate_events
from scrapers.hrw import fetch_events as fetch_hrw_events
from scrapers.hrw import filter_by_news_type
from scrapers.http import fetch_raw_cached
from scrapers.report import build_run_report


def run() -> dict:
    amnesty_result = parse_feed(fetch_raw_cached(Path(".cache/amnesty_feed.xml"), url=AMNESTY_FEED_URL))
    amnesty_events = filter_by_resource_type(amnesty_result.events)

    hrw_result = fetch_hrw_events(Path(".cache/hrw"))
    hrw_events = filter_by_news_type(hrw_result.events)

    combined_events = amnesty_events + hrw_events
    combined_skipped = amnesty_result.skipped + hrw_result.skipped
    combined_raw_items_seen = amnesty_result.raw_items_seen + hrw_result.raw_items_seen

    dedup_result = deduplicate_events(combined_events)

    report = build_run_report(
        source="scrapers.pipeline (amnesty + hrw, deduplicated)",
        events=dedup_result.unique_events,
        skipped=combined_skipped,
        raw_items_seen=combined_raw_items_seen,
        duplicates_merged=dedup_result.duplicates_removed,
    )

    return {
        "events": dedup_result.unique_events,
        "duplicate_groups": dedup_result.groups,
        "report": report,
    }


if __name__ == "__main__":
    result = run()
    events = result["events"]
    groups = result["duplicate_groups"]
    report = result["report"]

    out_path = Path("data/events.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([e.to_dict() for e in events], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {len(events)} deduplicated events to {out_path}")

    if groups:
        dupes_path = Path("data/duplicate_groups.json")
        dupes_path.write_text(
            json.dumps([g.to_dict() for g in groups], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Wrote {len(groups)} duplicate group(s) to {dupes_path}")

    report_path = Path("data/pipeline_run_report.json")
    report_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print(report.summary_text())
