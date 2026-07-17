# scrapers/

Scraper code for both sides of the pipeline: human rights org event
ingestion (Amnesty, HRW) and foreign ministry response monitoring. Ministry
sources share a common adapter interface and are declared via config
(YAML/JSON) wherever possible — see [CONTRIBUTING.md](../CONTRIBUTING.md)
for how to add one.

## http.py

`fetch_raw()`/`fetch_raw_cached()` — the shared polite-fetch-with-cache
helper used by every scraper (default 20h cache TTL), so "crawl once daily,
cache aggressively" is enforced in one place rather than reimplemented per
source.

## amnesty.py

Fetches and parses Amnesty International's global RSS feed
(`https://www.amnesty.org/en/feed/`), which covers `/latest/news/` content
and carries Amnesty's own taxonomy (country/region, topic, content-type,
resource-type) as custom `<amn:*>` RSS elements — no HTML scraping needed.
`parse_feed()` is the pure, skip-tolerant parsing function tested against
the fixture in `tests/fixtures/amnesty/feed_sample.xml` (a malformed item
is recorded and skipped, not fatal); `parse_events()` is a thin wrapper
returning just the event list. Run directly with `python -m scrapers.amnesty`
to fetch, filter, write `data/amnesty_events.json`, and print/write a run
report.

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

## hrw.py

Second event source, added specifically because Amnesty's ingestion can't
reach most of its own Action/Urgent Action content (see above). Two-phase,
unlike Amnesty's single feed request, because HRW's RSS feed
(`https://www.hrw.org/rss/news`) carries no country/topic/news-type
taxonomy — only the article page does. `parse_feed_index()` (pure,
skip-tolerant) parses the feed into bare index items; `parse_article_page()`
(pure) parses one article's HTML into a full event, reading the article's
own `.news-header__flag` (news type) and `.tag-block` sections ("Region /
Country", "Topic"); `fetch_events()` is the network-touching orchestration
that does both, tolerating a single article failing to fetch/parse. Tested
against fixtures in `tests/fixtures/hrw/` (feed + 3 article-page snapshots
covering News Release, Statement, and an excluded Report). Run directly
with `python -m scrapers.hrw` to fetch, filter, write
`data/hrw_events.json`, and print/write a run report.

Narrowed to news type `News Release`/`Statement` via `filter_by_news_type()`
— see the "Add Human Rights Watch as a second event source" entry in
`DECISIONS.md` for why those two (and not `Dispatches`/`Commentary`/
`Letter`, considered and deferred), plus a known nuance where a US
policy-area label was seen tagged as if it were a country.

## dedup.py

Merges events reported by more than one source as the same real-world
incident: two events are merged only if they share a country, have similar
titles (`difflib` ratio >= 0.6), and were published within 3 days of each
other — a deterministic heuristic, not the LLM-verified matching CLAUDE.md
specifies for event–statement linking (stage 3), since no LLM
infrastructure exists yet. `deduplicate_events()` is pure and works on any
mix of event objects (`AmnestyEvent`, `HRWEvent`, ...) via duck-typing.
Kept events are `unique_events`; merged-away events aren't discarded, they're
recorded in `groups` (a `DuplicateGroup` per cluster, with what matched) for
audit. See the "Cross-source event deduplication" entry in `DECISIONS.md`
for the thresholds' rationale and known limitations (greedy clustering, not
full transitive closure).

## pipeline.py

The combined entrypoint: runs Amnesty and HRW ingestion, applies each
source's filter, deduplicates the combined set, and writes one
`data/events.json` plus one run report covering both sources together.
Run directly with `python -m scrapers.pipeline`. Individual sources can
still be run standalone (`python -m scrapers.amnesty` / `scrapers.hrw`) for
debugging one source in isolation.

## report.py

`build_run_report()` produces the small end-of-run report every pipeline
stage generates (events found, date range covered, per-country counts,
skipped/unparseable items, duplicates merged) — see the "Run reports" hard
requirement in `CLAUDE.md`. Source-agnostic: it duck-types on
`.published_at` and `.countries` attributes, so future ministry adapters
can reuse it directly rather than inventing a per-adapter report format.

Ministry-side adapters (US State Dept, China MFA, etc.) land here next,
behind a shared adapter interface — see [CONTRIBUTING.md](../CONTRIBUTING.md)
for how to add one.
