# scrapers/

Scraper code for both sides of the pipeline: Amnesty International event
ingestion and foreign ministry response monitoring. Ministry sources share a
common adapter interface and are declared via config (YAML/JSON) wherever
possible — see [CONTRIBUTING.md](../CONTRIBUTING.md) for how to add one.

## amnesty.py

Fetches and parses Amnesty International's global RSS feed
(`https://www.amnesty.org/en/feed/`), which covers `/latest/news/` content
and carries Amnesty's own taxonomy (country/region, topic, content-type,
resource-type) as custom `<amn:*>` RSS elements — no HTML scraping needed.
`parse_feed()` is the pure, skip-tolerant parsing function tested against
the fixture in `tests/fixtures/amnesty/feed_sample.xml` (a malformed item
is recorded and skipped, not fatal); `parse_events()` is a thin wrapper
returning just the event list. `fetch_raw_cached()` handles the network
call with a local on-disk cache (default 20h TTL) per the "crawl once
daily, cache aggressively" requirement. Run directly with
`python -m scrapers.amnesty` to fetch, filter, write
`data/amnesty_events.json`, and print/write a run report.

Ingestion is narrowed to resource type `Action`/`Urgent Action` via
`filter_by_resource_type()` — reports, research briefings, etc. are
excluded (see the "Narrow ingestion to Action / Urgent Action resource
types" entry in `DECISIONS.md`). **Known gap:** that content lives almost
entirely at `amnesty.org/en/documents/...` URLs, which this RSS feed
doesn't reach — the filter is correct but currently yields close to zero
events. Same DECISIONS.md entry has the detail; not yet resolved.

Deliberately out of scope here: determining the perpetrating actor and
filtering to state-perpetrated violations, which CLAUDE.md assigns to a
separate LLM classification call (a later pipeline stage). See the module
docstring and `DECISIONS.md` for the country/region split heuristic.

## report.py

`build_run_report()` produces the small end-of-run report every pipeline
stage generates (events found, date range covered, per-country counts,
skipped/unparseable items) — see the "Run reports" hard requirement in
`CLAUDE.md`. Source-agnostic: it duck-types on `.published_at` and
`.countries` attributes, so future ministry adapters can reuse it directly
rather than inventing a per-adapter report format.

Ministry-side adapters (US State Dept, China MFA, etc.) land here next,
behind a shared adapter interface — see [CONTRIBUTING.md](../CONTRIBUTING.md)
for how to add one.
