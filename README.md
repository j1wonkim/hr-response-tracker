# Human Rights Response Tracker

A fully automated, public-facing pipeline that tracks how major states
respond — or stay silent — when human rights organizations document
state-perpetrated human rights violations.

Every day the pipeline scrapes event-level content from human rights
organizations (Amnesty International, Human Rights Watch, and more as
they're added), scrapes a config-driven list of foreign ministry sources
(US State Dept, China MFA, Russia MID, EU EEAS, and more as they're added),
links new ministry statements to open events, and codes each country's
response as **shamed**, **endorsed**, **abstention**, or **no response**.
The result is published as a public dataset and visualized as a per-event
response matrix.

**Status:** early scaffolding. Nothing is scraping yet — see
[Current state](#current-state) below.

## Why this exists

When a government violates human rights, other states' public reactions —
condemnation, defense, silence — are themselves a signal about international
norms, alliances, and accountability. This project makes that reaction
pattern observable, systematically and over time, instead of anecdotally.

## How it works

1. **Event ingestion** — scrape discrete, datable event content daily from
   human rights organizations (Amnesty Urgent Actions/Actions, HRW News
   Releases/Statements — reports and other ongoing-practice documentation
   are deliberately excluded), filter to state-perpetrated violations via
   LLM classification.
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

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow, testing
against fixtures, and how to add a new source.

## Current state

Two event-ingestion sources are working. `scrapers/amnesty.py` fetches
Amnesty's RSS feed and narrows to `Action`/`Urgent Action` items, but **that
filter currently yields close to zero events** — most of that content lives
at `amnesty.org/en/documents/...`, unreachable from the RSS feed, REST API,
or sitemap (see `DECISIONS.md`). `scrapers/hrw.py` fetches Human Rights
Watch's RSS feed for an item index, then fetches each article page for
country/topic/news-type tags, narrowing to `News Release`/`Statement` — and
this one actually works: a live run pulled 9 real, tagged events from 20
raw feed items. Both are tested against fixtures in `tests/fixtures/`; 24
tests pass via `docker run --rm hr-response-tracker pytest`. Every run ends
with a small report (events found, date range, per-country counts, skipped
items) via `scrapers/report.py`. Neither source yet determines the
perpetrating actor or filters to state-perpetrated violations — that's a
separate LLM classification call, still to come. No ministry-side scraping,
linking, classification, automation, or visualization yet. Build order and
architecture are documented in `CLAUDE.md`.

## Data & citation

Code in this repository is licensed under [MIT](LICENSE). Data (everything
under `data/` and any generated exports) is licensed separately under
[CC BY 4.0](LICENSE-DATA) — you're free to use, share, and adapt it, even
commercially, with attribution.

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

## License

- Code: [MIT](LICENSE)
- Data: [CC BY 4.0](LICENSE-DATA)
