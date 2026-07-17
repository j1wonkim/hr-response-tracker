# data/

The dataset produced by the pipeline: Amnesty events, ministry statements,
event–statement links with coded responses, and issue classifications.
Stored as flat JSON/CSV (or SQLite) and committed directly to this repo —
the repo is the database. Updated daily by the GitHub Actions cron job.

Licensed separately from the code under [CC BY 4.0](../LICENSE-DATA).

Empty for now. `scrapers/amnesty.py` can already produce
`amnesty_events.json` locally (`python -m scrapers.amnesty`), but that
output is gitignored rather than committed here — it's a one-off local
snapshot, not the output of the automated daily pipeline (GitHub Actions
cron, slice 4) that this directory is meant to hold under version control.
