# scrapers/

Scraper code for both sides of the pipeline: human rights org event
ingestion (currently HRW) and foreign ministry response monitoring. Ministry
sources share a common adapter interface and are declared via config
(YAML/JSON) wherever possible — see [CONTRIBUTING.md](../CONTRIBUTING.md)
for how to add one.

## config.py

`load_pipeline_config()` reads `config/pipeline.yaml` (not hardcoded,
per CLAUDE.md's config-over-code goal — a *hard requirement*, not a
feature tied to any one setting, see DECISIONS.md's "Restore the config
system after an over-scoped removal") into a `PipelineConfig` dataclass.
Currently one section, `hrw:` (an `HRWConfig`): `feed_url`,
`feed_cache_ttl_hours` (4), and `article_cache_ttl_hours` (168) — see
`hrw.py` below for why these live in config rather than as hardcoded
constants/defaults. Ministry-source config (CLAUDE.md stage 2) will live
in the same file, likely a new top-level section, once the adapter
interface exists.

## http.py

`fetch_raw()`/`fetch_raw_cached()` — the shared polite-fetch-with-cache
helper used by every scraper (default 20h cache TTL, overridable per
call — `hrw.py` overrides it via config, see below), so "crawl once daily,
cache aggressively" is enforced in one place rather than reimplemented per
source.

## hrw.py

The event-ingestion source. Two-phase, because HRW's RSS feed (URL is
config-driven — `config/pipeline.yaml`'s `hrw.feed_url`, currently
`hrw.org/rss/news`) carries no country/topic/news-type taxonomy — only the
article page does. `parse_feed_index()` (pure, skip-tolerant) parses the
feed into bare index items; `parse_article_page()` (pure) parses one
article's HTML into a full event, reading the article's own
`.news-header__flag` (news type) and `.tag-block` sections ("Region /
Country", "Topic"); `fetch_events()` is the network-touching orchestration
that does both, tolerating a single article failing to fetch/parse, and
takes `feed_url`/`feed_max_age_hours`/`article_max_age_hours` as required
parameters (no hardcoded defaults — always supplied from config by both
entrypoints). Tested against fixtures in `tests/fixtures/hrw/` (feed + 4
article-page snapshots covering News Release, Statement, Dispatches, and
an excluded Report). Run directly with `python -m scrapers.hrw` to fetch,
filter, write `data/hrw_events.json`, and print/write a run report.

**Crawl reliability (2026-07-17 redesign — see DECISIONS.md, "Redesign
HRW crawl reliability").** `fetch_events()` fetches exactly one,
un-paginated feed response per run; there is no backward crawl and no
persistent cursor within this module. Instead: each run is deduped
against already-committed events in `data/events.json` (keyed on URL, via
`scrapers/storage.py`) before any further processing, both `hrw.py`'s
standalone `__main__` and `scrapers/pipeline.py`'s `run()` do this, and it
avoids redundant classification spend, not just duplicate output rows.
After every fetch, `scrapers/coverage.py`'s `check_coverage_overlap()`
compares this run's oldest raw feed item against the newest committed
event; if the feed's window no longer reaches back far enough to overlap,
`open_coverage_gap_issue()` opens a GitHub issue (gated on `GITHUB_TOKEN`,
skipped loudly rather than failing if unset; reads the target repo from
`GITHUB_REPOSITORY` so a fork's own automated runs stay fork-safe; skips
filing a duplicate if one's already open). The feed's cache TTL dropped
from 20h to 4h (`config/pipeline.yaml`'s `hrw.feed_cache_ttl_hours`) as
the main lever available to shrink the risk window, since there's no
pagination to fall back on. `FetchResult.index_items` exposes the raw
feed's index (pre-filtering) so both the coverage check and the run
report's new `feed_date_range` field (see `report.py` below) can see the
feed's actual date span, not just the final filtered events' span.

Narrowed to news type `News Release`/`Statement`/`Dispatches` via
`filter_by_news_type()` — see the "Add Human Rights Watch as a second
event source" and "Widen HRW's taxonomy filter to include Dispatches"
entries in `DECISIONS.md` for why these three (Dispatches was initially
deferred, then widened to on 2026-07-17 once the pipeline had enough of a
track record to widen with confidence — a live run went from 9 to 19
events out of 20 raw feed items once it was added). `Commentary`,
`Interview`, and `Letter` remain deferred. Also a known nuance where a US
policy-area label was seen tagged as if it were a country.

This taxonomy filter does not exclude multimedia-format content — HRW
doesn't tag a documentary premiere or similar piece any differently from
a real incident report (both can be `News Release`), so items like that
pass this filter untouched. That's `scrapers/classify.py`'s job: its
discrete-incident check (Check 1) asks whether the item actually describes
a specific, datable incident, which is what catches a documentary-premiere
announcement regardless of its news-type tag. See the "Widen HRW's
taxonomy filter to include Dispatches" entry in `DECISIONS.md` for why
this two-layer split (taxonomy filter + LLM incident check) is deliberate,
not a gap.

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

## storage.py

Reads the repo's committed state — `data/events.json` — not the local,
gitignored `.cache/` directory, which is disposable scratch space, not a
record of what's been ingested. `load_committed_events()` returns `[]` on
a first run (file doesn't exist yet, not an error); `load_known_urls()`
extracts just the URL set; `filter_new_events()` drops any freshly
fetched event whose URL is already committed. Used by both `hrw.py`'s
standalone `__main__` and `pipeline.py`'s `run()`, before deduplication
and classification — so a previously-classified event is never
reclassified, not just never re-written to output. See DECISIONS.md,
"Redesign HRW crawl reliability."

## coverage.py

A crawl-coverage overlap check, added because `hrw.py` fetches one
un-paginated feed response per run with no backward crawl — the only
thing standing between "daily crawl" and "silently missed events" is
HRW's feed staying wide enough to overlap with the last successful crawl.
`check_coverage_overlap()` (pure) compares this run's oldest raw feed
item against the newest already-committed event; if the feed's window no
longer reaches that far back, `gap_detected` is `True`.
`open_coverage_gap_issue()` opens a GitHub issue when a gap is detected,
gated on `GITHUB_TOKEN` (a loud skip, not a silent no-op or hard failure,
mirroring `classify.py`'s `MissingCredentialsError` pattern), reading the
target repo from `GITHUB_REPOSITORY` (set automatically by GitHub
Actions) rather than hardcoding this project's repo, so a fork's own runs
file issues on the fork. Skips filing a duplicate if a `coverage-gap`-
labeled issue is already open. **Known limitation, logged deliberately**:
this compares against the newest *committed* (already-classified) event,
not a raw log of every URL ever crawled, so it has not yet fired against
real data — see DECISIONS.md, "Redesign HRW crawl reliability" for the
full reasoning and what would need to be true for it to actually catch a
real gap.

## classify.py

The LLM classification stage CLAUDE.md's stage 1 specifies ("an LLM
classification call: 'Is the government the responsible actor?'"), plus a
second check a live pipeline run surfaced the need for: whether the item
describes a discrete incident at all (a documentary-premiere announcement
passed the News Release filter but isn't a violation report). Both
questions are asked in one call to `claude-haiku-4-5` (deliberately not a
larger model — this is a bounded yes/no classification, cheap and
well-suited to Haiku; see the "Switch classification model to Haiku 4.5"
entry in `DECISIONS.md`) with structured JSON output (`output_config.format`,
so the response always parses) — the full instructions, inclusion/exclusion
rules, and calibration examples live in `prompts/state_perpetrator_filter.txt`,
not inline, per the "prompts as files" hard requirement.
`classify_event()`/`classify_events()` take an injected
`anthropic.Anthropic`-shaped client, so tests (`tests/test_classify.py`) run
against a fake client and never touch the live API. `build_client()` raises
`MissingCredentialsError` with a clear message if
`ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` isn't set — `scrapers/pipeline.py`
catches that and skips classification loudly rather than failing the whole
run. **Verified against the live API** — see the "Verify state-perpetrator
classification against the live API" entry in `DECISIONS.md`. Running this
stage against the live API costs real money (small, but non-zero) — see the
API cost note in the top-level README and CONTRIBUTING.md.

## mofa.py

The first ministry-side adapter (CLAUDE.md stage 2, response monitoring),
South Korea's Ministry of Foreign Affairs. Crawls two RSS feeds — Press
Releases (`m_5676`) and Press Briefings (`m_5679`) — chosen over the
broader-looking "Ministry News" board (`m_5674`) specifically because that
board has no RSS feed at all; see the "South Korea MFA: use Press Releases
+ Press Briefings via RSS, not Ministry News" entry in `DECISIONS.md` for
the full reasoning and alternatives considered.

Single-phase, unlike `hrw.py`: each feed's `<content:encoded>` already
carries the full statement text — a press release's full body, or an
entire day's spokesperson briefing transcript (MOFA doesn't split
multi-topic briefings into separate feed items) — so there's no second
article-page fetch. `parse_feed()` (pure) parses one feed's raw XML into
`MinistryStatement`s; `fetch_statements()` fetches and parses both feeds,
tolerating one feed failing without losing the other. A live run on
2026-07-17 pulled 58 statements (29 press releases + 29 briefings) from
both feeds with zero skipped items. Also confirmed live: both feeds serve
`Content-Type: application/rss+xml` with no charset parameter, but
`requests`' `apparent_encoding` detection still correctly decodes UTF-8
(including curly quotes and non-ASCII content) without any special
handling.

`MinistryStatement.countries` is always `["South Korea"]` — the
*responding* country the statement is attributed to, not a target/victim
country the way `HRWEvent.countries` is. It's exposed under the same field
name purely so `scrapers/report.py`'s `build_run_report()` can be reused
as-is; the semantic difference is called out in the module's docstring so
future adapter authors don't conflate the two.

Not yet wired into `scrapers/pipeline.py` — that pipeline is specifically
the stage-1 (event ingestion + classification) pipeline; ministry
statements will join it once stage 3 (event–statement linking) exists.
Run standalone with `python -m scrapers.mofa` to fetch, write
`data/mofa_statements.json`, and print/write a run report. Tested against
fixtures in `tests/fixtures/mofa/` (trimmed real feed snapshots, one per
board).

## pipeline.py

The entrypoint: loads config, runs HRW ingestion, applies the news-type
filter, dedupes against `data/events.json` (`storage.py`), deduplicates
near-duplicates within the batch (`dedup.py`), classifies (if a
credential is available), writes `data/events.json` plus a run report,
and runs the coverage-gap check (`coverage.py`). Run directly with
`python -m scrapers.pipeline`; `scrapers/hrw.py` can still be run standalone
for debugging ingestion in isolation from classification.

## report.py

`build_run_report()` produces the small end-of-run report every pipeline
stage generates (events found, date range covered, per-country counts,
skipped/unparseable items, duplicates merged, and — when a caller supplies
it — the raw feed's own date span) — see the "Run reports" hard
requirement in `CLAUDE.md`. Source-agnostic: it duck-types on
`.published_at` and `.countries` attributes, so future ministry adapters
can reuse it directly rather than inventing a per-adapter report format.
`compute_date_range()` is the shared min/max-date helper, used both
internally and by `hrw.py`/`pipeline.py` to compute `feed_date_range`
(the fetched feed's span, distinct from the final filtered events' span)
— see DECISIONS.md, "Redesign HRW crawl reliability."

More ministry-side adapters (US State Dept, China MFA, etc.) land here
next, behind a shared adapter interface extracted once there's a second
one to compare `mofa.py` against — see
[CONTRIBUTING.md](../CONTRIBUTING.md) for how to add one.
