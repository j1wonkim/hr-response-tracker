# The Human Rights Response Tracker

## What this project is

A fully automated, public-facing pipeline that tracks how major states respond (or stay silent) when Amnesty International documents state-perpetrated human rights violations. Data lives in this public GitHub repo, updates daily via GitHub Actions, and is visualized on GitHub Pages (later integrated into my personal website).

Maintainer: Jiwon (political scientist). This is an open community project: the explicit goal is that others fork it, add ministry sources, and improve the methods. Design every component to be forkable — config over code, documented decisions, reproducible environment.

## Pipeline architecture (six stages)

1. **Event ingestion (Amnesty side).** Scrape Amnesty International Urgent Actions and news (/latest/news/, RSS where available) daily. Extract: date, target country, perpetrating actor, summary text, URL. Filter to state-perpetrated violations only (an LLM classification call: "Is the government the responsible actor?"). The state is treated as the duty bearer.
2. **Response monitoring (foreign ministry side).** Config-driven list of ministry sources (YAML/JSON): US State Dept, China MFA spokesperson transcripts, Russia MID, EU EEAS, others added over time. One scraper adapter per source behind a common interface. Crawl daily; store date, source, full text, URL.
3. **Event–statement linking.** For each new ministry statement, match against open Amnesty events using entity/keyword/date-window matching plus embedding similarity, verified by an LLM call. Response window: 30 days. For each (event, country) pair, code **response** as a four-category variable:
   - `shamed` — country criticized/condemned the violation or the perpetrating government
   - `endorsed` — country defended the practice with justification and support of the perpetrating government's action. Typical framings: "non-interventionism," "law and order," "countercrime efforts." Any attempt to reframe the perpetrating government's action in a positive light falls here.
   - `abstention` — country responded (noted monitoring/awareness of the situation) but deferred both positive and negative judgment
   - `no_response` — no official communication referencing the event yet (silence is a data point; finalize after the 30-day window closes)

   **Sub-tags on `endorsed`** (binary flags, non-exclusive; a statement can carry both):
   - `dispute_facts` — the response does not positively reframe the action but disputes the facts and numbers of the allegation. This pertains to endorsement and is coded `endorsed` + `dispute_facts`.
   - `whataboutism` — the response deflects focus to the shaming states' lack of moral authority. Also a form of endorsement: coded `endorsed` + `whataboutism`.

   **Self-response flag** (binary, applies to any response category): `self_response` = the responding country is itself the target of the Amnesty criticism (e.g., China responding to a report on China). Self-defense and third-party responses are distinct phenomena; the dashboard must distinguish them.
4. **Issue classification.** "What is the dominant human rights issue being addressed?" Multi-label (one event can receive one or more labels). Zero-shot LLM classification using the codebook stored verbatim in `prompts/issue_codebook.txt`:
   - `cpr` — Civil and political rights: fair elections, freedom of expression, freedom of assembly and protest, rights to form a party, peaceful political opposition, protection of journalists and activists. *Hard case:* political detainment of a government-opposing figure is both `cpr` and `physint`.
   - `gps` — Governance, institutional functioning, and public services: accountability, a nondiscriminatory justice system aligned with international norms, judicial independence, anticorruption, transparency, rule of law, institutional reform for accountability. Due-process denial stemming from unequal application of the law, lack of legal aid or appeal mechanisms, or corruption/politicization of courts in general administration is `gps`.
   - `mig` — Migrant rights.
   - `physint` — Physical integrity rights: the most basic protections from state-inflicted harm and coercion — extrajudicial killings, politically motivated imprisonment, arbitrary detention, enforced disappearances, torture or cruel, inhuman, or degrading treatment. Due-process denial with respect to political imprisonment, arbitrary detention, or ill-treatment is `physint`.
   - `rer` — Race, ethnicity, or religious minority rights and freedoms.
   - `ecosoc` — Economic or social rights: labor rights, right to development, access to clean water and environment.
   - `vuln` — Vulnerable populations: children and the disabled only.
   - `women` — Women's rights.
   - `lgbt` — LGBTQIA+ population rights.

   `vuln`, `women`, and `lgbt` are mutually exclusive with each other — assign by whose rights are being invaded. (Each can still co-occur with the other labels above, e.g., an event can be `lgbt` + `physint`.)
5. **Storage + automation.** Flat JSON/CSV (or SQLite) committed to the repo; the repo is the database. GitHub Actions cron (daily) runs scrape → link → classify → commit. On parser failure (zero results), the Action opens an issue on this repo.
6. **Visualization.** GitHub Pages static site reading the JSON. Core view: a **per-event response matrix** — for each Amnesty event, every tracked country's response shown as one of the four categories (shamed / endorsed / abstention / no response yet), e.g., color-coded badges per country on each event card. `endorsed` badges display their sub-tags (`dispute_facts`, `whataboutism`) where present; `self_response` responses are visually distinguished from third-party responses (e.g., an outlined badge or separate row). Supporting views: event timeline, who-shames-whom matrix, issue-type breakdowns, response-latency distributions.

## Build order (vertical slices — do not build all layers at once)

1. Dockerfile (slim Python image, pinned dependencies) + Amnesty scraper + tests against saved HTML fixtures in `tests/fixtures/`. All development and testing happens inside the container from day one.
2. First ministry adapter (US State Dept), then the adapter interface, then China MFA
3. Linking logic, validated against a small hand-labeled set (~30 event–statement pairs I will provide)
4. GitHub Actions workflow (runs the pipeline inside the Docker container; publishes the image to GHCR on tagged releases) + failure alerting
5. GitHub Pages visualization, including a public **Methodology page** generated from `DECISIONS.md`

## Hard requirements

- **License:** Code under MIT (or similar permissive). Data under **CC BY 4.0**. Include LICENSE files, a suggested-citation block, and a BibTeX entry in the README and the site footer. Repo is public. Plan for Zenodo-integrated tagged releases (DOI per release).
- **Decision log → Methodology page:** Maintain `DECISIONS.md` at repo root. Every analytical or coding decision gets an entry: date, decision, rationale, alternatives considered. Examples: the 30-day window, response-type taxonomy, what qualifies as "state-perpetrated," matching thresholds, prompt wording changes, source inclusion/exclusion. This log feeds the public Methodology page on the site (not an academic paper) and serves as the intellectual changelog for forkers — err on the side of logging.
- **Docker throughout:** The pipeline runs in a Docker container locally and in CI. Keep the Dockerfile simple and readable (it's also a learning artifact for the maintainer). Forkers should be able to run the full pipeline with `docker build` + `docker run` and nothing else.
- **Fork-friendly by design:** Include `CONTRIBUTING.md` with "how to add a new ministry adapter" as the primary contribution path. New sources must be addable via config (YAML) wherever possible. README prominently invites forks.
- **Prompts as files:** All LLM prompts (violation filter, classifier, matcher) live as text files in `prompts/`, not inline in code, so they can be tuned and versioned independently.
- **Polite scraping:** Respect robots.txt, rate-limit, cache aggressively, crawl once daily. China MFA is known to block aggressive crawlers.
- **Fixture-based tests:** Parsers are tested against saved HTML snapshots, never live sites.

## Session hygiene

At the end of each working session, update this file's "Current state" section and append any new decisions to `DECISIONS.md`.

## Current state

Nothing built yet. First task: initialize repo structure, LICENSE files, DECISIONS.md, CONTRIBUTING.md, README skeleton with citation block and fork invitation, Dockerfile, then start slice 1 (Amnesty scraper inside the container).
