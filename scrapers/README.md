# scrapers/

Scraper code for both sides of the pipeline: human rights org event
ingestion (currently HRW) and foreign ministry response monitoring. Ministry
sources share a common adapter interface and are declared via config
(YAML/JSON) wherever possible — see [CONTRIBUTING.md](../CONTRIBUTING.md)
for how to add one.

## http.py

`fetch_raw()`/`fetch_raw_cached()` — the shared polite-fetch-with-cache
helper used by every scraper (default 20h cache TTL), so "crawl once daily,
cache aggressively" is enforced in one place rather than reimplemented per
source.

## hrw.py

The event-ingestion source. Two-phase, because HRW's RSS feed
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

Amnesty (`scrapers/amnesty.py`) was the original event source and has been
removed from the codebase — its Action/Urgent Action content lives almost
entirely at `amnesty.org/en/documents/...` URLs that its RSS feed, REST
API, and sitemap all fail to expose. See "Drop Amnesty as an event source"
in `DECISIONS.md` for the full history (RSS-vs-HTML decision, the
`/en/documents/` gap, and the live-run evidence that finally settled it).

## dedup.py

Merges events that report the same real-world incident more than once:
two events are merged only if they share a country, have similar titles
(`difflib` ratio >= 0.6), and were published within 3 days of each other —
a deterministic heuristic, not the LLM-verified matching CLAUDE.md
specifies for event–statement linking (stage 3). `deduplicate_events()` is
pure and works on any event object via duck-typing (`.title`,
`.published_at`, `.countries`, `.source`, `.url`, `.id`) — built for
cross-source duplicates when Amnesty and HRW both ran, kept now because a
single source can still publish near-duplicates and a second source can be
added back without changing this module. Kept events are `unique_events`;
merged-away events aren't discarded, they're recorded in `groups` (a
`DuplicateGroup` per cluster, with what matched) for audit. See the
"Cross-source event deduplication" entry in `DECISIONS.md` for the
thresholds' rationale and known limitations (greedy clustering, not full
transitive closure).

## classify.py

The LLM classification stage CLAUDE.md's stage 1 specifies ("an LLM
classification call: 'Is the government the responsible actor?'"), plus a
second check a live pipeline run surfaced the need for: whether the item
describes a discrete incident at all (a documentary-premiere announcement
passed the News Release filter but isn't a violation report). Both
questions are asked in one call to `claude-opus-4-8` with structured JSON
output (`output_config.format`, so the response always parses) — the full
instructions, inclusion/exclusion rules, and calibration examples live in
`prompts/state_perpetrator_filter.txt`, not inline, per the "prompts as
files" hard requirement. `classify_event()`/`classify_events()` take an
injected `anthropic.Anthropic`-shaped client, so tests
(`tests/test_classify.py`) run against a fake client and never touch the
live API. `build_client()` raises `MissingCredentialsError` with a clear
message if `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` isn't set —
`scrapers/pipeline.py` catches that and skips classification loudly rather
than failing the whole run. **Not yet verified against the live Anthropic
API** — no key was available in the environment this was built in; see the
"Implement state-perpetrator classification" entry in `DECISIONS.md`.

## pipeline.py

The entrypoint: runs HRW ingestion, applies the news-type filter,
deduplicates, classifies (if a credential is available), and writes
`data/events.json` plus a run report. Run directly with
`python -m scrapers.pipeline`; `scrapers/hrw.py` can still be run standalone
for debugging ingestion in isolation from classification.

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
