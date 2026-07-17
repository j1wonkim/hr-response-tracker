"""Event-ingestion pipeline: fetch, filter, deduplicate, classify, report.

This is the "run everything and tell me what happened" entrypoint. HRW is
currently the only event source (Amnesty was dropped -- see DECISIONS.md,
2026-07-16/17); dedup and the report format stay source-agnostic so adding
a second source back is a matter of combining event lists, not redesigning
this module.

Classification (scrapers/classify.py) calls the Anthropic API and needs a
credential. If none is available, the pipeline still runs and produces
unclassified output -- CLAUDE.md's "forkers should be able to run the full
pipeline with docker build + docker run and nothing else" requirement
predates the classification stage, and a working exploratory run without an
API key is worth more than a hard failure. The run report says plainly
whether classification ran.

Each run is deduped against data/events.json -- the repo's committed
state, not the local .cache/ directory -- before classification, both to
avoid re-litigating the same event every day and to avoid re-paying for
classification on an event already classified in a prior run (see
scrapers/storage.py and DECISIONS.md, "Redesign HRW crawl reliability",
which replaced the old ingest_start_date post-hoc filter with this).

HRW's feed URL and cache TTLs are config-driven (config/pipeline.yaml via
scrapers/config.py), not hardcoded here or in scrapers/hrw.py -- see
DECISIONS.md, "Restore the config system after an over-scoped removal".
"""

from __future__ import annotations

import json
from pathlib import Path

from scrapers.classify import MissingCredentialsError, build_client, classify_events
from scrapers.config import PipelineConfig, load_pipeline_config
from scrapers.coverage import check_coverage_overlap, open_coverage_gap_issue
from scrapers.dedup import deduplicate_events
from scrapers.hrw import fetch_events as fetch_hrw_events
from scrapers.hrw import filter_by_news_type
from scrapers.report import build_run_report, compute_date_range
from scrapers.storage import filter_new_events, load_committed_events


def run(config: PipelineConfig | None = None) -> dict:
    config = config or load_pipeline_config()

    hrw_result = fetch_hrw_events(
        Path(".cache/hrw"),
        feed_url=config.hrw.feed_url,
        feed_max_age_hours=config.hrw.feed_cache_ttl_hours,
        article_max_age_hours=config.hrw.article_cache_ttl_hours,
    )
    hrw_events = filter_by_news_type(hrw_result.events)

    committed_events = load_committed_events()
    known_urls = {e["url"] for e in committed_events if e.get("url")}
    hrw_events = filter_new_events(hrw_events, known_urls)

    dedup_result = deduplicate_events(hrw_events)
    deduped_events = dedup_result.unique_events

    classification_results = []
    classification_skipped_reason = None
    try:
        client = build_client()
        events, classification_results = classify_events(deduped_events, client)
    except MissingCredentialsError as exc:
        events = deduped_events
        classification_skipped_reason = str(exc)

    report = build_run_report(
        source="scrapers.pipeline (hrw, deduped against data/events.json, deduplicated"
        + (", classified)" if classification_results else ", NOT classified)"),
        events=events,
        skipped=hrw_result.skipped,
        raw_items_seen=hrw_result.raw_items_seen,
        duplicates_merged=dedup_result.duplicates_removed,
        feed_date_range=compute_date_range(hrw_result.index_items),
    )

    coverage_result = check_coverage_overlap(hrw_result.index_items, committed_events)

    return {
        "events": events,
        "duplicate_groups": dedup_result.groups,
        "classification_results": classification_results,
        "classification_skipped_reason": classification_skipped_reason,
        "report": report,
        "coverage_result": coverage_result,
    }


if __name__ == "__main__":
    result = run()
    events = result["events"]
    groups = result["duplicate_groups"]
    classification_results = result["classification_results"]
    report = result["report"]

    out_path = Path("data/events.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([e.to_dict() for e in events], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {len(events)} events to {out_path}")

    if groups:
        dupes_path = Path("data/duplicate_groups.json")
        dupes_path.write_text(
            json.dumps([g.to_dict() for g in groups], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Wrote {len(groups)} duplicate group(s) to {dupes_path}")

    if classification_results:
        classify_path = Path("data/classification_results.json")
        classify_path.write_text(
            json.dumps([r.to_dict() for r in classification_results], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Wrote {len(classification_results)} classification result(s) to {classify_path}")
    elif result["classification_skipped_reason"]:
        print()
        print(f"CLASSIFICATION SKIPPED: {result['classification_skipped_reason']}")
        print("Events below are ingested + deduplicated but NOT filtered to state-perpetrated incidents.")

    report_path = Path("data/pipeline_run_report.json")
    report_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print(report.summary_text())

    coverage_result = result["coverage_result"]
    print()
    print(coverage_result.message)
    issue_url = open_coverage_gap_issue(coverage_result)
    if issue_url:
        print(f"Opened coverage-gap issue: {issue_url}")
