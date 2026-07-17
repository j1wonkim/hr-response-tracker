# Contributing

Thanks for considering a contribution to the Human Rights Response Tracker.
This is an open, forkable project — the whole point is that the community
adds ministry sources, improves matching/classification, and finds bugs in
the methodology. Small, well-scoped PRs are very welcome.

Before contributing analytical logic (taxonomy changes, prompt wording,
matching thresholds), read [DECISIONS.md](DECISIONS.md) — it's the record of
why things are the way they are, and your PR should either respect an
existing decision or propose changing it explicitly (see below).

## The primary contribution path: adding a ministry adapter

The most valuable and most welcome contribution is a new foreign ministry
source. The pipeline is designed so this requires minimal code:

1. **Check the adapter interface.** Every ministry source implements the
   same interface (see `scrapers/base.py` once slice 2 lands). At minimum an
   adapter needs to return, per statement: date, source name, full text, and
   source URL.
2. **Add a config entry.** Sources are declared in a YAML/JSON config (see
   `scrapers/ministries/` and its README once it exists), not hardcoded. If
   the source's structure is a close match for an existing adapter (e.g.
   another government using a similar press-release CMS), you may only need
   a config entry — no new code.
3. **Write a scraper adapter if needed.** If the source needs bespoke
   parsing, add a new adapter module implementing the shared interface.
   Keep network/parsing logic separated so it can be tested against a
   fixture.
4. **Add fixtures, not live requests.** Save a representative HTML snapshot
   of the source under `tests/fixtures/<source-name>/` and write a test that
   parses the fixture. Parsers must never hit live sites in tests — see
   "Polite scraping" below and in CLAUDE.md.
5. **Generate a run report.** End your adapter's run with a small report —
   events found, date range covered, per-country counts, and any
   skipped/unparseable items. Reuse `scrapers/report.py`'s
   `build_run_report()` (it duck-types on `.published_at`/`.countries`,
   so it works for any adapter's event objects) rather than inventing a new
   format; see `scrapers/hrw.py`'s `__main__` block for the pattern, or
   `scrapers/pipeline.py` for how sources are deduplicated and reported on
   together.
6. **Respect robots.txt and rate limits.** The pipeline crawls once daily.
   New adapters must not introduce aggressive polling. Some sources (e.g.
   China MFA) are known to block or throttle aggressive crawlers — cache
   responses and back off appropriately.
7. **Open a PR** with: the adapter/config, its fixture-based test(s), and a
   one-paragraph note on the source (official spokesperson transcripts vs.
   press releases vs. social media, language, update cadence).

## Other ways to contribute

- **Bug reports:** parser failures, misclassified events, incorrect links
  between statements and events. Open an issue with the event/statement URL
  and what you expected vs. what happened. Note that daily parser failures
  (zero results) auto-open an issue via GitHub Actions — check for an
  existing one before filing a duplicate.
- **Improving matching/classification:** the linking logic (Stage 3) and
  issue classification (Stage 4) both rely on prompts kept as plain text
  files in `prompts/`. If you're proposing a prompt wording change, include
  before/after examples against the hand-labeled validation set where
  possible, and add a corresponding entry to `DECISIONS.md`.
- **Proposing a taxonomy or methodology change:** e.g., changing the 30-day
  response window, adding a response category, changing the issue codebook.
  These are the most consequential kind of change since they affect how
  history is coded. Open an issue first to discuss before submitting a PR,
  and any accepted change must include a `DECISIONS.md` entry explaining
  what changed and why (see the alternatives-considered format already
  used there).

## Decision log discipline

If your PR changes *how* something is decided — not just implementation
details — add an entry to `DECISIONS.md`: date, decision, rationale,
alternatives considered. This file feeds the public Methodology page, so
write entries for a general audience. PRs that change taxonomy, thresholds,
prompt wording, or source inclusion criteria without a `DECISIONS.md` entry
will be asked to add one before merge.

## Development environment

The pipeline runs in Docker, and all development/testing should happen
inside the container — this keeps contributions reproducible regardless of
your local Python setup.

```bash
docker build -t hr-response-tracker .
docker run --rm -it hr-response-tracker bash
```

Run tests inside the container:

```bash
docker run --rm hr-response-tracker pytest
```

Tests never call the live Anthropic API — `scrapers/classify.py`'s tests
inject a fake client (see `tests/test_classify.py`), so no credential is
needed to run the suite. To exercise the real classification stage
(`scrapers/pipeline.py`'s `docker run --rm hr-response-tracker` default,
or `python -m scrapers.pipeline` directly), set `ANTHROPIC_API_KEY` and
pass it into the container:

```bash
docker run --rm -e ANTHROPIC_API_KEY hr-response-tracker
```

Without it, the pipeline still runs — it prints a clear "CLASSIFICATION
SKIPPED" notice and produces ingested-but-unclassified output rather than
failing, so `docker build` + `docker run` with nothing else still works
for exploration.

**This costs real money.** Classification calls the Anthropic API on every
event, using `claude-haiku-4-5` specifically to keep that cost small — but
it's not free, and forkers running this on a daily schedule should expect
a (small, ongoing) charge on whatever Anthropic account the key belongs to.
See the "API cost" note in the top-level [README](README.md#running-it-locally)
before wiring a key into a scheduled run, and never commit a key — `.env`
and `*.local` are already gitignored for this reason.

`scrapers/coverage.py`'s crawl-coverage-gap alert (see DECISIONS.md,
"Redesign HRW crawl reliability") optionally uses `GITHUB_TOKEN` to open a
GitHub issue when the fetched feed no longer overlaps the newest
committed event:

```bash
docker run --rm -e GITHUB_TOKEN hr-response-tracker
```

Without it, a detected gap is printed loudly instead of filed as an
issue — same graceful-skip pattern as `ANTHROPIC_API_KEY`, so this is
never required to run the pipeline. The token needs `issues:write` on
whichever repo `GITHUB_REPOSITORY` points at (set automatically by GitHub
Actions to the running repo's own `owner/name`, so a fork's automated
runs file issues on the fork, not on this project's repo).

## Code style

- Keep scrapers and parsing logic separate from network calls so they're
  testable against fixtures without hitting the network.
- No prompts inline in code — LLM prompts live as files in `prompts/`.
- New config-driven sources over new code paths wherever possible.
- Keep the Dockerfile simple; it doubles as documentation of the runtime
  environment.

## Code of conduct

Be respectful. This project documents real human rights violations and
government responses to them — treat the subject matter, the data, and
other contributors accordingly. Disagreement about coding decisions is
expected and welcome; keep it in the issue tracker and grounded in evidence.
