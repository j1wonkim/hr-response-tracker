# data/

The dataset produced by the pipeline: events from human rights orgs
(currently HRW — see `DECISIONS.md` for why Amnesty was dropped), ministry
statements, event–statement links with coded responses, and issue
classifications. Stored as flat JSON/CSV (or SQLite) and committed
directly to this repo — the repo is the database. Updated daily by the
GitHub Actions cron job.

Licensed separately from the code under [CC BY 4.0](../LICENSE-DATA).

Empty for now. `scrapers/hrw.py` can already produce `hrw_events.json`
locally, and `scrapers/pipeline.py` produces `events.json` (ingested,
deduplicated, and — if `ANTHROPIC_API_KEY` is set — filtered to
state-perpetrated incidents), plus `duplicate_groups.json` when any merges
happened and `classification_results.json` when classification ran. Run
either with `python -m scrapers.hrw` / `python -m scrapers.pipeline`. That
output is gitignored rather than committed here — it's a one-off local
snapshot, not the output of the automated daily pipeline (GitHub Actions
cron, slice 4) that this directory is meant to hold under version control.
