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
`parse_events()` is a pure function tested against the fixture in
`tests/fixtures/amnesty/feed_sample.xml`; `fetch_raw_cached()` handles the
network call with a local on-disk cache (default 20h TTL) per the "crawl
once daily, cache aggressively" requirement. Run directly with
`python -m scrapers.amnesty` to fetch and write `data/amnesty_events.json`.

Deliberately out of scope here: determining the perpetrating actor and
filtering to state-perpetrated violations, which CLAUDE.md assigns to a
separate LLM classification call (a later pipeline stage). See the module
docstring and `DECISIONS.md` for the country/region split heuristic.

Ministry-side adapters (US State Dept, China MFA, etc.) land here next,
behind a shared adapter interface — see [CONTRIBUTING.md](../CONTRIBUTING.md)
for how to add one.
