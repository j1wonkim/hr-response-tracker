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

Ingestion is bounded by config/pipeline.yaml's ingest_start_date -- see
scrapers/config.py and DECISIONS.md ("Bound initial HRW ingestion with a
config-driven ingest_start_date"). This is a one-time backfill floor, not
a retention policy: events already ingested are never dropped as they age.
"""

from __future__ import annotations

import json
from pathlib import Path

from scrapers.classify import MissingCredentialsError, build_client, classify_events
from scrapers.config import PipelineConfig, load_pipeline_config
from scrapers.dedup import deduplicate_events
from scrapers.hrw import fetch_events as fetch_hrw_events
from scrapers.hrw import filter_by_news_type, filter_by_start_date
from scrapers.report import build_run_report


def run(config: PipelineConfig | None = None) -> dict:
    config = config or load_pipeline_config()

    hrw_result = fetch_hrw_events(Path(".cache/hrw"))
    hrw_events = filter_by_news_type(hrw_result.events)
    hrw_events = filter_by_start_date(hrw_events, config.ingest_start_date)

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
        source="scrapers.pipeline (hrw, ingest_start_date="
        + config.ingest_start_date.isoformat()
        + ", deduplicated"
        + (", classified)" if classification_results else ", NOT classified)"),
        events=events,
        skipped=hrw_result.skipped,
        raw_items_seen=hrw_result.raw_items_seen,
        duplicates_merged=dedup_result.duplicates_removed,
    )

    return {
        "events": events,
        "duplicate_groups": dedup_result.groups,
        "classification_results": classification_results,
        "classification_skipped_reason": classification_skipped_reason,
        "report": report,
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
