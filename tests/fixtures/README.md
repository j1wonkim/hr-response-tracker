# tests/fixtures/

Saved HTML/XML snapshots used to test scraper parsers. Parsers are tested
against these fixtures only — never against live sites — so tests stay
fast, deterministic, and don't hammer real ministry/HRW servers.

One subdirectory per source: `hrw/` (event ingestion) and `mofa/`
(South Korea MFA response monitoring, two RSS feeds — see
`scrapers/mofa.py`) today, plus `us_state_dept/`, `china_mfa/`, etc. as
more ministry adapters land.
