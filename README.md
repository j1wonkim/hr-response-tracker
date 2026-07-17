# Human Rights Response Tracker

A fully automated, public-facing pipeline that tracks how major states
respond — or stay silent — when human rights organizations document
state-perpetrated human rights violations.

Every day the pipeline scrapes event-level content from human rights
organizations (currently Human Rights Watch, with more as they're added —
Amnesty International was tried and dropped, see `DECISIONS.md`), scrapes
a config-driven list of foreign ministry sources (US State Dept, China
MFA, Russia MID, EU EEAS, and more as they're added), links new ministry
statements to open events, and codes each country's response as
**shamed**, **endorsed**, **abstention**, or **no response**. The result
is published as a public dataset and visualized as a per-event response
matrix.

**Status:** event ingestion, deduplication, and state-perpetrator
classification (HRW) are working end to end and verified against the live
Anthropic API; ministry-side response monitoring has its first adapter
(South Korea MFA); linking, issue classification, and visualization are
not built yet — see [Current state](#current-state) below.

## Why this exists

When a government violates human rights, other states' public reactions —
condemnation, defense, silence — are themselves a signal about international
norms, alliances, and accountability. This project makes that reaction
pattern observable, systematically and over time, instead of anecdotally.

## How it works

1. **Event ingestion** — scrape discrete, datable event content daily from
   human rights organizations (currently HRW News Releases/Statements —
   reports and other ongoing-practice documentation are deliberately
   excluded), deduplicate events reported more than once for the same
   incident, filter to state-perpetrated violations via an LLM
   classification call.
2. **Response monitoring** — scrape foreign ministry sources daily via a
   common adapter interface, one adapter per source, sources declared in
   config.
3. **Event–statement linking** — match new ministry statements to open
   events (entity/keyword/date-window + embedding similarity,
   LLM-verified) within a 30-day response window. Code each response as
   `shamed` / `endorsed` / `abstention` / `no_response`, with `dispute_facts`
   and `whataboutism` sub-tags on `endorsed`, and a `self_response` flag.
4. **Issue classification** — multi-label zero-shot LLM classification
   against a fixed codebook (civil/political rights, governance, migrant
   rights, physical integrity, race/ethnicity/religion, economic/social
   rights, vulnerable populations, women's rights, LGBTQIA+ rights).
5. **Storage + automation** — flat JSON/CSV committed to this repo (the repo
   is the database), updated daily by a GitHub Actions cron job. Parser
   failures auto-open an issue.
6. **Visualization** — a static GitHub Pages site: a per-event response
   matrix plus supporting views (timeline, who-shames-whom matrix, issue
   breakdowns, response-latency distributions).

Full methodology, including the reasoning behind the 30-day window, the
response taxonomy, and every analytical decision along the way, is logged in
[DECISIONS.md](DECISIONS.md) and published as a Methodology page on the
site.

## Fork this

This project is designed to be forked. If you want to track a different set
of ministries, add a country your government cares about, or improve the
matching/classification logic, you don't need permission — fork it. Adding a
new ministry source is meant to require only a config entry plus, if needed,
a small scraper adapter behind a shared interface; see
[CONTRIBUTING.md](CONTRIBUTING.md) for the walkthrough. Everything —
prompts, thresholds, taxonomy — is a config file or a logged decision, not
buried in code.

## Running it locally

The pipeline runs in Docker end to end — that's the only supported way to
run it, in CI and locally.

```bash
docker build -t hr-response-tracker .
docker run --rm hr-response-tracker
```

Without any credential, the pipeline still runs end to end — it ingests
and deduplicates events but skips classification with a clear
"CLASSIFICATION SKIPPED" notice.

**API cost.** Running classification requires an `ANTHROPIC_API_KEY` and
calls the Anthropic API — this costs real money, not a lot, but non-zero,
and it's not something you should be surprised by after forking this. The
classification stage uses `claude-haiku-4-5` specifically because it's the
cheapest model that comfortably handles this bounded yes/no task, and each
call is one short prompt against one event's title/body — see
`prompts/state_perpetrator_filter.txt` for what's actually sent. If you
fork this and want to estimate your own cost, check
[Anthropic's current pricing](https://www.anthropic.com/pricing) against
your expected daily event volume (typically single digits to low tens of
events per day from one source) before wiring in a key and running it on a
schedule.

```bash
docker run --rm -e ANTHROPIC_API_KEY hr-response-tracker
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow, testing
against fixtures, and how to add a new source.

## Current state

Event ingestion runs on HRW alone. Amnesty (`scrapers/amnesty.py`) was
built first, then dropped — its Action/Urgent Action content lives almost
entirely at `amnesty.org/en/documents/...` URLs, unreachable from its RSS
feed, REST API, or sitemap, and a live pipeline run confirmed 0 events made
it through in practice (see `DECISIONS.md`). `scrapers/hrw.py` fetches
Human Rights Watch's RSS feed for an item index, then fetches each article
page for country/topic/news-type tags, narrowing to `News
Release`/`Statement`/`Dispatches` (widened from just the first two on
2026-07-17 — Dispatches turned out to be the largest category; see
`DECISIONS.md`) — a live run pulled 19 real, tagged events from 20 raw
feed items. This taxonomy filter doesn't screen out multimedia-format
content (HRW tags a documentary premiere the same as a real incident
report) — that's caught downstream by the classification stage's
discrete-incident check instead, by design; see `DECISIONS.md`.

**Crawl reliability.** `scrapers/hrw.py` fetches one un-paginated feed
response per run — there's no backward crawl. Instead, each run is
deduped against `data/events.json` (the repo's committed state, keyed on
URL, via `scrapers/storage.py`) before classification, both to avoid
duplicate rows and to avoid re-paying for classification on an
already-classified event. `scrapers/coverage.py` checks after every run
whether the fetched feed still overlaps the newest committed event, and
opens a GitHub issue if it doesn't (optional `GITHUB_TOKEN`; skipped
loudly, not silently, if unset — same pattern as `ANTHROPIC_API_KEY`).
The feed's cache TTL is 4 hours, the main lever available to shrink the
risk window given there's no pagination. HRW's feed URL and both cache
TTLs are config-driven (`config/pipeline.yaml`'s `hrw:` section via
`scrapers/config.py`), not hardcoded. See `DECISIONS.md`, "Redesign HRW
crawl reliability" for the full design and its known limitations.

`scrapers/dedup.py` merges events reported more than once for
the same real-world incident (heuristic: shared country + title similarity
+ a 3-day window — not LLM-verified, see `DECISIONS.md`). `scrapers/classify.py`
is the LLM classification stage — one call asks both whether an item
describes a discrete incident and whether it was state-perpetrated, using
`claude-haiku-4-5` with structured JSON output (prompt in
`prompts/state_perpetrator_filter.txt`). Haiku, not a larger model — this
is a bounded yes/no classification, and Haiku is meaningfully cheaper for a
daily cron job (see [Running it locally](#running-it-locally) below for
what that costs, and `DECISIONS.md` for the reasoning). It needs `ANTHROPIC_API_KEY`;
`scrapers/pipeline.py` runs it after dedup but degrades gracefully — with a
clear "CLASSIFICATION SKIPPED" notice, not silence — if no key is set, so
`docker run` still works out of the box. **Verified against the live API
on 2026-07-17** (a real live run kept 4 of 9 events, correctly excluding a
documentary-premiere announcement and a natural-disaster item — see
`DECISIONS.md`; that first run also caught a real bug, a too-old pinned
`anthropic` SDK version that didn't support structured output, since
fixed). `scrapers/pipeline.py` writes `data/events.json` plus a run report
(events found, date range, per-country counts, skipped items, duplicates
merged) via `scrapers/report.py`. All of it is tested against fixtures in
`tests/fixtures/`; tests pass via `docker run --rm hr-response-tracker
pytest`. `scrapers/mofa.py` is the first ministry-side (response
monitoring) adapter, crawling South Korea MFA's Press Releases (`m_5676`)
and Press Briefings (`m_5679`) RSS feeds — chosen over the broader
Ministry News board (`m_5674`), which has no RSS feed at all; see
`DECISIONS.md`. Single-phase, since each feed already carries full
statement text in `content:encoded` — no second article-page fetch the
way HRW needs. A live run pulled 58 real statements with zero skipped
items. Run standalone with `python -m scrapers.mofa`; not yet wired into
`scrapers/pipeline.py`, since linking (stage 3) — which is what would
actually connect ministry statements to events — doesn't exist yet. No
event–statement linking, issue classification, automation, or
visualization yet, and the US State Dept DRL adapter is still just an
investigated lead (no DRL-specific RSS, but a promising REST API angle).
Build order and architecture are documented in `CLAUDE.md`.

## License

This repository carries two licenses, covering different things:

- **Code** — everything in `scrapers/`, `prompts/`, `site/`, and other
  source/tooling in this repo — is licensed under [MIT](LICENSE).
- **Data** — everything under `data/` and any generated exports — is
  licensed separately under [CC BY 4.0](LICENSE-DATA). You're free to use,
  share, and adapt it, even commercially, with attribution.


If you use this dataset, please cite it:

> Kim, Jiwon. (2026). *Human Rights Response Tracker* [Data set]. GitHub.
> https://github.com/j1wonkim/hr-response-tracker

```bibtex
@misc{hr_response_tracker,
  author       = {Kim, Jiwon},
  title        = {Human Rights Response Tracker},
  year         = {2026},
  publisher    = {GitHub},
  howpublished = {\url{https://github.com/j1wonkim/hr-response-tracker}}
}
```

Tagged releases will be archived on Zenodo with a per-release DOI once the
pipeline is producing data; a release-specific citation and DOI badge will
be added here at that point.
