# Decision Log

This is the intellectual changelog of the Human Rights Response Tracker. Every
analytical or coding decision that shapes the data — what counts as an event,
how responses are coded, what thresholds trigger a match, how prompts are
worded — gets an entry here, in date order. This file is the source for the
public Methodology page on the site; write entries for a general audience,
not just future contributors.

Each entry: **date, decision, rationale, alternatives considered.**

---

## 2026-07-16 — Project scaffolding and licensing split

**Decision:** Code is licensed under MIT; data (everything under `data/` and
any generated exports) is licensed separately under CC BY 4.0. Two license
files at the repo root: `LICENSE` (MIT, code) and `LICENSE-DATA` (CC BY 4.0,
data).

**Rationale:** The project's value is split between reusable pipeline code
and the dataset it produces. MIT is the standard low-friction license for
forkable tooling. CC BY 4.0 is the standard for open research data — it
requires attribution (so downstream use is traceable back to this project
and its methodology) without restricting reuse, including commercial or
academic reuse.

**Alternatives considered:** A single license (e.g., MIT for everything) was
rejected because software licenses aren't a natural fit for datasets and
don't carry attribution requirements suited to research citation.
CC BY-SA or CC BY-NC were rejected: share-alike and non-commercial clauses
would restrict downstream research and journalism use, which conflicts with
the project's goal of being a maximally reusable public resource.

---

## 2026-07-16 — Response taxonomy: four categories

**Decision:** Every (event, country) pair is coded into exactly one of four
response categories: `shamed`, `endorsed`, `abstention`, `no_response`.
`endorsed` carries two non-exclusive binary sub-tags, `dispute_facts` and
`whataboutism`. A separate binary flag, `self_response`, marks whether the
responding country is itself the target of the original Amnesty criticism.

**Rationale:** Collapsing state responses to a single ordinal scale (e.g.,
critical → neutral → supportive) would lose two distinct phenomena that are
analytically important: (1) *how* a state endorses a violation — by
disputing the underlying facts versus by attacking the shaming state's
credibility are different rhetorical strategies and should be queryable
independently — and (2) whether a response is self-defense or third-party
commentary, which have different theoretical drivers in the international
relations literature on human rights shaming.

**Alternatives considered:** A single 5-point ordinal scale (strongly
condemns → strongly endorses) was considered and rejected as it would force
premature aggregation and hide the sub-tag information described above. A
free-text-only coding (no categorical variable) was rejected because it
would make the core matrix visualization and cross-country comparison
impossible.

---

## 2026-07-16 — 90-day response window

**Superseded** by [2026-07-16 — Response window shortened to 30 days](#2026-07-16--response-window-shortened-to-30-days-supersedes-90-day-window) below, same day, before any data collection began.

**Decision:** A ministry statement is eligible to be linked to an Amnesty
event only within a 90-day window following the event's publication date.
If no statement is linked within that window, the (event, country) pair is
finalized as `no_response`.

**Rationale:** An unbounded window would mean every event stays "open"
indefinitely, making `no_response` uncomputable and the dashboard perpetually
provisional. 90 days is long enough to capture delayed diplomatic responses
(which often lag weeks behind an Urgent Action) while still allowing the
dataset to converge and be reported on with a stable `no_response` count.

**Alternatives considered:** 30 days was considered too short — ministry
responses, especially rebuttals requiring internal clearance, often lag
initial reporting by 4-8 weeks. An unbounded/open-ended window was rejected
for the reason above. The 90-day figure is a starting assumption, not
validated against data yet; revisit once the hand-labeled linking set
(~30 pairs) is available and response-latency distributions can be examined
empirically.

---

## 2026-07-16 — Response window shortened to 30 days (supersedes 90-day window)

**Decision:** The event–statement linking window is shortened from 90 days
to 30 days following the event's publication date. If no ministry statement
is linked within 30 days, the (event, country) pair is finalized as
`no_response`. `CLAUDE.md` and all references to the window elsewhere are
updated from 90 to 30 days.

**Rationale:** Two reasons, both stemming from a reframing of what this
project is for. First, a shorter window more easily bounds the
event–statement match itself — at 90 days, a single ministry statement has
much more opportunity to plausibly reference multiple older, unrelated
Amnesty events, which makes the entity/keyword/date-window/embedding match
noisier and harder to verify with an LLM call. Second, and more
fundamentally: this project is a real-time advocacy tracker, not an
archival dataset. A 30-day `no_response` is a claim someone can act on now
("this government has said nothing for a month") — a 90-day `no_response`
mostly just describes history after the news cycle has already moved on.
Shortening the window makes `no_response` a more meaningful, timely signal
for that use case.

**Scope implication — annual reports are out of scope by design:** Because
the tracker is oriented around a short, actionable response window rather
than a comprehensive historical record, government annual human rights
reports (e.g., end-of-year white papers, annual reviews issued by a foreign
ministry) are deliberately excluded as a response source. An annual report
responding to an event 6+ months after the fact falls outside any
reasonable real-time window and would not be captured as a `shamed` /
`endorsed` / `abstention` response — it would just show up (correctly) as
`no_response`. This is a deliberate design boundary, not a gap: sources are
scoped to timely, event-linkable communications, and annual/periodic
retrospective reports are not a source type the pipeline targets.

**Alternatives considered:** Keeping the 90-day window (see the superseded
entry above) was rejected for the reasons above. A much shorter window
(e.g., 14 days) was considered but not chosen yet — 30 days is judged a
better fit for diplomatic response latency (which can require internal
clearance) while still being short enough to keep `no_response` meaningful;
revisit once real response-latency data is available from the hand-labeled
linking set. Treating annual reports as an in-scope response source with a
separate, longer window was also considered and rejected, since it would
reintroduce the archival framing this change is meant to move away from and
would require a second, parallel taxonomy/timeline for periodic sources.

---

## 2026-07-16 — State-perpetrated violations only, LLM-classified

**Decision:** Stage 1 (event ingestion) filters to events where the
perpetrating actor is the government, using an LLM classification call
("Is the government the responsible actor?"). Non-state-perpetrated
violations (e.g., by armed non-state groups) are excluded from the tracked
event set.

**Rationale:** The project's causal question is about state responses to
*state* human rights violations — i.e., how governments react when a peer
government is criticized, which is a distinct social/diplomatic phenomenon
from responses to non-state actors. Keeping the scope narrow also keeps the
downstream response-coding taxonomy (`shamed`/`endorsed`/etc.) coherent,
since "endorsing" a non-state actor's violation doesn't have the same
diplomatic meaning as endorsing a government's.

**Alternatives considered:** Including all Amnesty-documented violations
regardless of perpetrator was rejected — it would dilute the response
matrix with events where no third-country response is diplomatically
expected, and would require a second taxonomy for non-state contexts.

---

## 2026-07-16 — Issue classification: multi-label zero-shot codebook

**Decision:** Stage 4 classifies each event against a fixed 9-label codebook
(`cpr`, `gps`, `mig`, `physint`, `rer`, `ecosoc`, `vuln`, `women`, `lgbt`),
multi-label, via zero-shot LLM classification. The codebook text is stored
verbatim in `prompts/issue_codebook.txt`, not inline in code. `vuln`,
`women`, and `lgbt` are mutually exclusive with each other (assigned by
whose rights are invaded) but each can co-occur with any of the other six
labels.

**Rationale:** Multi-label is necessary because real events frequently
implicate more than one right (e.g., political detention is both `cpr` and
`physint`). Storing the codebook as a versioned text file (rather than
embedding it in code) means prompt wording changes are tracked in git
history and can be iterated on without a code deploy, per the project's
"prompts as files" requirement.

**Alternatives considered:** A single-label forced-choice classification was
rejected as too lossy for the stated hard cases (e.g., political detainment
is deliberately dual-coded `cpr` + `physint`). A fully open-vocabulary
classification (no fixed codebook) was rejected because it would break the
per-issue-type breakdown visualization and make cross-country comparison
inconsistent.

---

## 2026-07-16 — Amnesty ingestion via RSS feed, not HTML scraping

**Decision:** `scrapers/amnesty.py` (slice 1) ingests events from Amnesty's
global RSS feed (`https://www.amnesty.org/en/feed/`) rather than scraping
the `/en/latest/news/` HTML listing page. The feed carries Amnesty's own
taxonomy as custom `<amn:*>` elements (content-type, resource-type, topic,
and a `countries` list) alongside the standard title/link/pubDate/
description/content:encoded fields.

**Rationale:** Inspecting the live site (2026-07-16) showed the HTML
article template does not reliably expose country/topic tags in the
article content itself — the only country-like links found on an article
page came from an unrelated "related content" grid widget and a generic
sidebar menu that mixes countries and regions with no way to tell them
apart from markup alone. The RSS feed, by contrast, has explicit
Amnesty-curated `<amn:countries>`, `<amn:topics>`, `<amn:content-types>`,
and `<amn:resource-types>` elements per item, and also satisfies the "RSS
where available" preference already stated in the ingestion stage
description. One feed request also replaces what would otherwise be one
listing-page request plus one request per article, which is more polite to
Amnesty's servers.

**Scope boundary — perpetrating actor is not extracted here:** The feed
does not identify who committed a violation, only what/where/when it was
reported. Determining the perpetrating actor and filtering to
state-perpetrated violations remains a separate LLM classification call
(as already specified for this stage), applied downstream of this scraper,
not inside it.

**Country vs. region split is a maintained list, not derived from the
feed:** `<amn:countries>` mixes actual countries (e.g. "Myanmar") with
Amnesty's own continent/subregion taxonomy (e.g. "Asia and the Pacific",
"South Asia") in the same flat list, with nothing in the markup to tell
them apart. `scrapers/amnesty.py` splits them using a hardcoded
`REGION_NAMES` set, populated from region names actually observed in the
feed and the news-page country filter facets on 2026-07-16. This is a
maintained list, not a general solution — if Amnesty adds a new region
name, events tagged with it will be miscounted as a country until the list
is updated.

**Alternatives considered:** Scraping the HTML listing/article pages was
rejected per the reasoning above — no reliable, request-free source of
country tagging was found there. Treating the raw `<amn:countries>` list as
undifferentiated "location tags" (skipping the country/region split
entirely) was considered and rejected because the response matrix
(`CLAUDE.md` stage 6) is keyed on country, and passing regions through
as if they were countries would corrupt it. A full ISO-3166 lookup was
considered but rejected as overkill — Amnesty's own taxonomy already
distinguishes region names by name, just not by markup, so a maintained
list of the (small, low-churn) region names is simpler than reimplementing
country/region classification from scratch.

---

## 2026-07-16 — Narrow ingestion to Action / Urgent Action resource types

**Decision:** Amnesty ingestion is narrowed to items tagged with resource
type `Action` or `Urgent Action` (`RESOURCE_TYPE_INCLUDE` in
`scrapers/amnesty.py`, applied via `filter_by_resource_type()`). Everything
else — `Report`, `Research Briefing`, `Annual Report`, `Position`, `Blog
Post`, `Public Statement`, `Governance`, etc. — is excluded from the event
set, even though it's still visible on `amnesty.org/en/latest/`.

**Rationale:** Reports, research briefings, and similar resource types
document ongoing, multi-year practices — not a discrete, datable event. They
don't fit a real-time response tracker: there's no single date a foreign
ministry could plausibly be "responding to," and forcing them into the
30-day linking window (see the "Response window shortened to 30 days"
entry above) would produce meaningless `no_response` counts. Actions and Urgent Actions,
by contrast, are each tied to a specific case with a specific publication
date, which is exactly what the event–statement linking stage needs.

**Known limitation — the current RSS source barely reaches this content:**
Verified directly against the live site on 2026-07-16. Amnesty's
`Action`/`Urgent Action` content (24,000+ items site-wide, confirmed via
`/en/wp-json/wp/v2/resourceType`) lives almost entirely at
`amnesty.org/en/documents/...` URLs — a separate content system from the
`/en/latest/news/` posts this scraper's RSS feed (`/en/feed/`) covers. That
system has no dedicated RSS feed (`/en/documents/feed/` 404s), isn't
exposed through the public REST API (`/en/wp-json/wp/v2/types` lists no
`documents` collection; querying `/wp/v2/posts?resourceType=<urgent-action-id>`
returns only 1 cross-tagged item), and isn't in the XML sitemap. It's only
browsable through the `/en/latest/` filtered search UI, which is backed by
a third-party enterprise search widget (an exposed client-side API key,
product tag `PRO_MULTISITE`) rather than a stable, documented, scrapeable
endpoint. Running `filter_by_resource_type()` against the current feed is
correct but currently yields close to zero events (confirmed: 0 of 12 items
in a live run) — the filter isn't broken, the source just can't reach most
of what it's supposed to select. **A different ingestion path for
`/en/documents/` content is a prerequisite for this filter to do real work**
and is not yet built; flagged to the maintainer rather than silently
shipping a scraper that always returns ~nothing.

**Alternatives considered:** Keeping all resource types and letting Stage 4
issue classification or Stage 3 linking implicitly filter them out was
rejected — it would silently let non-event content pollute the response
matrix rather than being excluded by an explicit, logged rule. Reverse-
engineering the third-party search widget's API to reach `/en/documents/`
content now was considered and rejected for this slice: it's undocumented,
the exposed API key appears scoped to the widget rather than general
programmatic use, and building a scraper around an unfamiliar private
endpoint is a bigger, riskier lift than warranted without confirming this
is the right approach first.

---

## 2026-07-17 — Add Human Rights Watch as a second event source

**Superseded** by [2026-07-17 — Drop Amnesty as an event source](#2026-07-17--drop-amnesty-as-an-event-source) below, same day: "alongside Amnesty, not a replacement" (this entry's framing) turned out to be wrong once a live pipeline run confirmed Amnesty was contributing zero events in practice, not just in the worst case. HRW itself is unaffected — this note only corrects the "not a replacement" claim.

**Decision:** `scrapers/hrw.py` ingests Human Rights Watch news
(`hrw.org/news`, via the RSS feed at `hrw.org/rss/news`) as a second event
source alongside Amnesty, not a replacement. Narrowed the same way as
Amnesty: only news type `News Release` or `Statement` counts as a discrete,
datable event (`NEWS_TYPE_INCLUDE` in `scrapers/hrw.py`); `Report`,
`Background Briefing`, `Fact Sheet`, `UPR`, `Journal Article`, etc. are
excluded for the same reason Amnesty's `Report`/`Research Briefing` are —
they document ongoing practices, not a single dated incident. `Dispatches`,
`Commentary`, `Interview`, and `Letter` were considered but left out for
now: they're each dated and specific-incident-adjacent, but lean editorial/
advocacy rather than incident reporting, and the maintainer wants to see
how `News Release`/`Statement` alone performs before widening the filter.

**Rationale:** HRW was evaluated specifically because of the Amnesty
`/en/documents/` gap logged above. Unlike Amnesty, HRW's discrete-event
content (`News Release`, `Statement`) is NOT walled off in a separate,
unreachable content system — it's the same `/news/...` URL space as
everything else on the site, and a live run against the real feed on
2026-07-17 confirmed it works end-to-end: 9 of 20 raw feed items passed
the filter, each with real country/topic tags attached (Libya, Tunisia,
Uganda, Peru, Bangladesh, etc.) — a working equivalent of what the Amnesty
resource-type filter was supposed to do but structurally cannot right now.

**Two-phase ingestion, unlike Amnesty's single feed request:** HRW's RSS
feed carries only title/link/pubDate/guid — no country/topic/news-type
taxonomy, unlike Amnesty's `<amn:*>` elements. That taxonomy only exists on
the article page itself, as clean, article-scoped tags (`.news-header__flag`
for news type, a `.tag-block` labeled "Region / Country" and another labeled
"Topic" — verified directly against the live site on 2026-07-17, and unlike
Amnesty's article pages, no cross-content noise from unrelated "related
articles" widgets was found reusing the same tag classes). So `fetch_events()`
does one feed request plus one article-page request per item, each cached
separately (`scrapers/http.py`'s `fetch_raw_cached`, now shared between
Amnesty and HRW since both need the same polite-fetch-with-cache behavior).
This is still polite — daily feed volume is small — but it's a structurally
different, heavier request pattern than Amnesty's one-request design, worth
knowing about if request volume ever becomes a concern.

**Known nuance — "Region / Country" isn't always a place:** At least one
live HRW article tagged a US policy-area label ("Immigrants' Rights and
Border Policy") inside the same "Region / Country" tag-block used for
actual countries, rather than under "Topic". `REGION_NAMES` in
`scrapers/hrw.py` only knows to exclude HRW's seven top-level region names
(Africa, Americas, Asia, Europe/Central Asia, Middle East/North Africa,
United States, Global); it doesn't yet know to exclude "United States"
sub-facet labels like this one. Not fixed here — noted so it isn't mistaken
for a bug later; revisit once more real examples are seen.

**Alternatives considered:** Replacing Amnesty outright was rejected —
Amnesty's News/Press Release content (even without Urgent Actions) still
has value as context, and dropping a working, tested scraper wasn't
warranted just because one specific content type is unreachable. Fetching
country/topic from the RSS `<description>` field instead of the article
page was rejected: HRW's feed description is the full article body as raw
HTML with no separate taxonomy fields, so there was nothing to gain over
fetching the article page directly, which also gives access to the cleaner
`.news-header__flag`/`.tag-block` markup.

---

## 2026-07-17 — Cross-source event deduplication (heuristic, not LLM-verified)

**Decision:** `scrapers/dedup.py` merges events that are almost certainly
the same real-world incident reported by more than one source (currently
Amnesty + HRW). Two events are merged only if ALL of: they share at least
one country, their titles are similar (`difflib.SequenceMatcher` ratio >=
0.6), and they were published within 3 days of each other. Within a merged
group, the earliest-published event is kept as the canonical record; the
rest are dropped from the event set but retained in a separate audit trail
(`DuplicateGroup`, written to `data/duplicate_groups.json` by
`scrapers/pipeline.py`) recording exactly what matched and why, so nothing
is silently discarded. Runs after each source's own resource-type/news-type
filter, not before — deduplicating content that's already excluded from
the event set (Reports, Background Briefings, etc.) is wasted work.

**Rationale:** Without this, the same incident covered by both Amnesty and
HRW would produce two rows in the event set, each independently eligible
for event–statement linking (stage 3) — silently double-counting one
incident in the response matrix (a government's single reaction would
appear to "respond" to two events instead of one, and `no_response` tallies
would be thrown off the same way). A deterministic, conservative heuristic
was chosen over the LLM-verified entity/embedding matching CLAUDE.md
specifies for event–statement linking (stage 3) because no LLM
infrastructure exists yet in this repo, and event-vs-event dedup is a
simpler problem than event-vs-statement linking (same underlying incident,
reported in similar language, close together in time — not an incident
being referenced obliquely in a diplomatic statement). The 0.6 similarity
threshold and 3-day window are initial values, not validated against real
duplicate pairs yet (a live pipeline run on 2026-07-17 found zero
duplicates, because Amnesty's own filter currently yields almost no events
to cross-match against — see the Amnesty/HRW entries above); revisit once
real cross-source duplicates are observed.

**Known limitation — greedy clustering, not full transitive closure:** if
event A matches event B, and B matches event C, but A and C don't
pairwise-match each other, C still joins A's cluster in the current
implementation (whichever event is encountered first "claims" every later
event that matches it). Documented in the module docstring rather than
silently assumed correct; a proper union-find implementation would fix this
but wasn't justified before real multi-way duplicate clusters are observed.

**Alternatives considered:** Matching on URL or GUID was rejected outright
— different organizations' URLs share no structure. Matching on country
alone (no title similarity) was rejected as far too permissive — two
unrelated events about the same country would merge constantly. Deferring
dedup entirely until stage 3's LLM/embedding infrastructure exists was
considered, but rejected: shipping known-duplicate rows into the response
matrix in the meantime was judged worse than a conservative, honestly-
limited heuristic that can be tightened later.

---

## 2026-07-17 — Drop Amnesty as an event source

**Decision:** `scrapers/amnesty.py`, its tests, and its fixtures are
deleted. HRW is now the sole event-ingestion source. `scrapers/pipeline.py`
no longer references Amnesty at all.

**Rationale:** This was a theoretical concern (the `/en/documents/` gap,
logged 2026-07-16) until a live pipeline run on 2026-07-17 made it
empirical: with real requests against the real Amnesty RSS feed, the
`Action`/`Urgent Action` filter returned **0 events out of 12 raw items** —
not a worst case, the actual outcome. Every avenue checked at the time
(RSS feed, REST API, XML sitemap) failed to expose the content the filter
is supposed to select, and no new avenue has been found since. Keeping a
scraper that reliably contributes nothing to the live dataset is worse
than removing it: it adds maintenance surface (a `REGION_NAMES` list to
keep in sync, a resource-type filter to keep in sync with Amnesty's
taxonomy), it made `scrapers/dedup.py`'s cross-source design untestable
against real duplicate pairs (the previous entry above notes 0 duplicates
found, precisely because Amnesty contributed 0 events to cross-match
against), and it implied the dataset covers Amnesty when it structurally
does not.

**Alternatives considered:** Keeping the code but excluding it from
`scrapers/pipeline.py` (dormant, not deleted) was considered and rejected
— dead code that still claims to be a working scraper in its own
docstrings and tests is more misleading than no code at all, and nothing
about git history or this decision log is lost by deleting it (both
preserve exactly how it worked and why it was dropped). Waiting for a
proper `/en/documents/` ingestion path before dropping Amnesty was
rejected: that path was never found despite the investigation logged
2026-07-16, and the project already has a working single source (HRW) —
there's no reason to keep a non-contributing scraper "just in case" a
solution turns up later. If one does, re-adding Amnesty is a new,
separately-justified decision, not a revival of dead code.

---

## 2026-07-17 — Implement state-perpetrator + discrete-incident classification

**Decision:** `scrapers/classify.py` implements the LLM classification
call CLAUDE.md's stage 1 has always specified ("Is the government the
responsible actor?"), extended with a second question a live pipeline run
surfaced: does the item describe a discrete incident at all? Both
questions are asked in a single call to `claude-opus-4-8` with structured
JSON output. The full instructions — inclusion/exclusion rules and three
calibration examples — live in `prompts/state_perpetrator_filter.txt`, not
inline in code, per the "prompts as files" hard requirement. An event must
pass both checks to enter the dataset.

**Rationale — why a second check, not just the one CLAUDE.md named:** A
2026-07-17 live run showed "Immersive Documentary Centers Human Rights in
Climate Crisis" — a film premiere announcement — passing HRW's
`News Release` filter cleanly, because it genuinely is HRW's `News
Release` type on their site; the news-type filter (stage 1's first half)
correctly does its job of excluding ongoing-practice documentation, but it
was never designed to catch an announcement that carries the right resource
type while describing no incident at all. Asking "is the government the
perpetrator" alone would not have caught this either — the natural fix is
a prior question: is there an incident here in the first place? Combining
both checks into one call (rather than two separate LLM calls) was chosen
for cost and latency — one classification pass per event rather than two,
and the two questions share nearly all their context (the same title/body
text).

**Scope and integration:** Runs after `scrapers/dedup.py`, not before —
classifying content that's about to be discarded as a duplicate wastes a
call. Requires `ANTHROPIC_API_KEY` (or `ANTHROPIC_AUTH_TOKEN`);
`scrapers/pipeline.py` catches the missing-credential case and skips
classification with a clear, printed "CLASSIFICATION SKIPPED" notice
rather than failing the run or silently shipping unclassified events as if
they'd passed — CLAUDE.md's "forkers should be able to run the full
pipeline with docker build + docker run and nothing else" hard requirement
predates this stage, and a working exploratory run without a key was
judged more valuable than a hard failure, as long as the skip is loud.

**Not yet verified against the live API:** this was built and tested
entirely against a fake client (`tests/test_classify.py`) — no
`ANTHROPIC_API_KEY` was available in the environment this was built in.
The prompt's calibration examples and inclusion/exclusion rules have not
been checked against real model output yet; treat the classification
behavior as unverified until a live run happens with a real key.

**Alternatives considered:** Two separate LLM calls (one for "is this an
incident", one for "is it state-perpetrated") were considered and
rejected — doubles cost and latency per event for no accuracy benefit the
maintainer asked for, since the two checks share context and a single
well-structured prompt can ask both reliably. Filtering "is this an
incident" with a cheaper heuristic (e.g. keyword rules) instead of an LLM
call was considered and rejected: the failure case that motivated this
(a documentary premiere with human-rights-adjacent language) is exactly
the kind of judgment call keyword matching handles badly, and the
maintainer's own framing of the requirement was already phrased as a
question for a classifier, not a rule set.

---

## 2026-07-17 — Restructure LICENSE files so GitHub detects them

**Decision:** `LICENSE` now contains only the verbatim, unmodified MIT
license text (copyright line: "Copyright (c) 2026 Jiwon Kim", nothing
else). `LICENSE-DATA` now contains only the verbatim, unmodified CC BY 4.0
legal code (fetched directly from
`creativecommons.org/licenses/by/4.0/legalcode.txt` to guarantee exact
text). Everything that isn't the license text itself — which license
covers what (code vs. `data/`), the suggested citation, and the BibTeX
block — moved into the README's License section.

**Rationale:** GitHub was showing this repo's license as "Unknown."
GitHub's license detector (`licensee`) matches file contents against known
license templates and is strict about extraneous text — the previous
`LICENSE` had the correct MIT body but an appended paragraph explaining
the code/data split, and `LICENSE-DATA` had explanatory prose wrapped
around a CC BY *summary* (not the actual legal code) plus a suggested-
attribution block. Either of those is enough to break template matching.
Splitting "what the license says" (verbatim, in the license files) from
"what this project wants you to know about its licensing" (in the README)
fixes detection while keeping the explanation — it just lives somewhere
a license-detection tool doesn't parse.

**Alternatives considered:** Keeping the explanatory text in the license
files and hoping GitHub's detector tolerates it was rejected — it already
didn't, that's the bug being fixed. Dropping the CC BY 4.0 data license
notice entirely (relying on GitHub only ever detecting one repo-wide
license, which would necessarily be the code license) was rejected: the
project's data-vs-code licensing split is a deliberate, hard requirement
(see the 2026-07-16 "Project scaffolding and licensing split" entry), and
losing that distinction to satisfy a detector would be the wrong trade.
Using CC BY 4.0's short "deed" summary text instead of the full legal code
in `LICENSE-DATA` was considered and rejected — the deed is explicitly not
the license itself (creativecommons.org describes it as a human-readable
summary of the legal code), so a `LICENSE-DATA` file containing only the
deed would not actually state the terms being agreed to.

---

## 2026-07-17 — Verify state-perpetrator classification against the live API; fix pinned SDK version

**Decision:** Bump the pinned `anthropic` package from `0.69.0` to
`0.117.0` in `requirements.txt`. With that fix, `scrapers/classify.py` was
run against the real Anthropic API for the first time (previously it had
only been exercised through the mocked client in `tests/test_classify.py`
— see the "Implement state-perpetrator + discrete-incident classification"
entry above, which flagged this as unverified).

**What broke, and why:** `client.messages.create(..., output_config={...})`
raised `TypeError: Messages.create() got an unexpected keyword argument
'output_config'` on the first live run. `output_config`-based structured
JSON output is a real, current Anthropic API feature, but the
`anthropic==0.69.0` pin — chosen without checking against a specific
verified-compatible version — predates client-side support for it in the
Python SDK. `pip index versions anthropic` showed `0.117.0` as latest;
upgrading to it resolved the error immediately with no other code changes
needed.

**Live verification result:** Against a real run of 9 deduplicated HRW
events, classification kept 4 and excluded 5, with reasoning that closely
tracked `prompts/state_perpetrator_filter.txt`'s calibration examples. Two
results worth noting specifically: "Immersive Documentary Centers Human
Rights in Climate Crisis" — the film-premiere announcement that originally
motivated adding the is-this-an-incident check — was correctly excluded,
with the model's own rationale citing "(matching Example A)" from the
prompt. A Bangladesh landslide item was correctly split on the two checks
(`is_incident: true`, `is_state_perpetrated: false`) despite HRW's article
criticizing government policy alongside the disaster reporting — matching
calibration Example C's natural-disaster-vs-state-action distinction. Two
of the five exclusions (an EU/Tunisia advocacy-anniversary piece and a
Peru veto-the-bill piece) are more debatable calls — both cite real past
incidents in their body text but were excluded because the model read the
item's primary thrust as advocacy/procedural rather than incident
reporting — worth the maintainer's review, not treated here as either
confirmed-correct or confirmed-wrong.

**Alternatives considered:** None — this is a bugfix plus a verification
record, not a design decision with real alternatives. Logged anyway
because CLAUDE.md's "prompt wording changes" and "source inclusion/
exclusion" logging mandate extends naturally to "the first time a prompt's
real output was checked, and what it got right or wrong" — this is exactly
the kind of empirical result future maintainers need when deciding whether
to trust or retune the prompt.

---

## 2026-07-17 — South Korea MFA: use Press Releases + Press Briefings via RSS, not Ministry News

**Decision:** The South Korea MFA adapter will crawl board `m_5676`
("Press Releases") and board `m_5679` ("Press Briefings") via their
working RSS feeds (`http://www.mofa.go.kr/www/brd/rss.do?brdId=302` and
`brdId=303` respectively), not board `m_5674` ("Ministry News").

**Rationale:** `m_5674` carries the broadest and, per the maintainer's
original read, most relevant content (including MOFA Spokesperson's
Statements), but it has no RSS feed of its own — reaching it would mean
HTML-scraping a listing page instead of consuming a structured feed.
`m_5676` and `m_5679` do have working RSS feeds, confirmed live before
this decision (see the "Investigate slice 2 sources" work on 2026-07-17).
Preferring the structured, feed-backed boards over the single broadest
board matches this project's existing bias toward RSS where available
(the same reasoning that shaped the HRW adapter) and toward adapters that
don't depend on a listing page's HTML structure staying stable.

**Alternatives considered:**
- **`m_5674` via HTML parsing.** Broadest coverage, including the
  Spokesperson's Statements the maintainer originally had in mind, but
  requires HTML scraping of a listing page with no feed, and no guarantee
  the government won't restructure that page without notice.
- **All three boards.** Maximizes coverage but adds a second parsing path
  (HTML for `m_5674`, RSS for the other two) for uncertain additional
  value; can be revisited later if `m_5676`/`m_5679` turn out to miss
  content the Spokesperson's Statements would have caught.

The maintainer chose RSS-only (`m_5676` + `m_5679`) on 2026-07-17.

---

## 2026-07-17 — Switch classification model to Haiku 4.5; document API cost for forkers

**Decision:** `scrapers/classify.py`'s `MODEL` constant changes from
`claude-opus-4-8` to `claude-haiku-4-5`. Also added an explicit "this costs
real money" disclosure to the top-level README and CONTRIBUTING.md, next
to the existing `ANTHROPIC_API_KEY` instructions.

**Rationale:** The classification call asks two bounded yes/no questions
per event (discrete incident? state-perpetrated?) against a single
article's title and body — well within a smaller model's capability, and
already verified working end to end on live HRW events (see the prior
entry). Opus was the right choice for the first live-verification pass,
where accuracy on edge cases (documentary premiere, natural-disaster
item) needed close scrutiny; now that the prompt and schema are verified,
Haiku is the appropriate default for a daily cron job across a public,
forkable project, where every fork that turns on classification incurs
its own Anthropic bill. Making the model choice and its cost implications
explicit in the docs (not just in code) matters specifically because
CLAUDE.md's fork-friendly design goal means people who didn't build this
will be the ones deciding whether to turn classification on and pay for
it themselves.

**Alternatives considered:**
- **Keep Opus.** Higher accuracy ceiling on ambiguous cases, but no
  evidence yet that Haiku performs meaningfully worse on this specific,
  narrow task, and the cost difference compounds daily for every forker
  running this unattended.
- **Say nothing about cost and let forkers discover it themselves.**
  Rejected outright — silently exposing new self-hosters to an unexpected
  bill conflicts with the project's fork-friendly, transparent-by-design
  posture.

**Live re-verification (same day):** re-ran the pipeline against the same
9 deduplicated HRW events used for the Opus verification. Haiku 4.5 kept
the identical 4 events (Libya ICC, Uganda military, Fort Bliss detention
deaths, Thailand forced returns) and excluded the same 5, including both
calibration-relevant cases: the documentary-premiere item was still
correctly excluded as not a discrete incident, and the Bangladesh
landslide item was still correctly split (`is_incident: true`,
`is_state_perpetrated: false`) as a natural disaster, not a state action.
No quality regression observed on this sample.

---

## 2026-07-17 — Build the South Korea MFA adapter (scrapers/mofa.py)

**Decision:** Implement `scrapers/mofa.py` as the first ministry-side
(response monitoring, CLAUDE.md stage 2) adapter, fetching and parsing
the two RSS feeds chosen in the prior entry. Three implementation choices
worth recording:

1. **Single-phase, not two-phase.** `scrapers/hrw.py` needs a second
   article-page fetch because HRW's feed carries no taxonomy and no full
   text. MOFA's feeds are different: `<content:encoded>` already contains
   the complete statement text (a full press release, or an entire day's
   spokesperson briefing transcript). There's nothing on the article page
   the feed doesn't already have, so `mofa.py` has no second fetch at
   all — `parse_feed()` is the whole parser.
2. **A multi-topic briefing is stored as one statement, not split by
   topic.** MOFA's Press Briefings board publishes one item per day that
   can cover several unrelated topics (e.g., the July 14, 2026 briefing
   covers an ASEAN travel announcement in a single transcript). Per
   CLAUDE.md stage 2, ingestion's job is only to store date/source/full
   text/URL; deciding which specific event(s) within a multi-topic
   transcript a later linking pass should match against is stage 3's job,
   not this adapter's. Splitting briefings by topic now would mean
   guessing at topic boundaries with no linking logic yet to validate the
   guess against.
3. **`MinistryStatement.countries` means the responding country, not a
   target/victim country.** `HRWEvent.countries` (stage 1) names who a
   violation was committed against; reusing the same field name for "which
   country's ministry issued this statement" risks confusion once a second
   ministry adapter exists and both datasets get compared. Kept the same
   field name anyway — `scrapers/report.py`'s `build_run_report()`
   duck-types on `.countries` for its per-country tally, and inventing a
   parallel field just for this would mean either forking the report
   format or teaching it a second attribute name for the same purpose.
   The semantic difference is called out directly in `mofa.py`'s
   docstring and field comment so it isn't silently assumed elsewhere.

**Encoding finding (recorded for future adapter authors):** both MOFA
feeds serve `Content-Type: application/rss+xml` with no `charset`
parameter. Initial inspection via this project's browser tooling showed
mojibake (e.g. "Koreaâ€™s" instead of "Korea's"), which looked like it
might require manual encoding handling in the adapter. Verified directly
against the live feeds using this project's actual `requests`-based
fetch path (`scrapers/http.py`) inside the built Docker image: `requests`
leaves `response.encoding` unset when no charset is declared, but its
`apparent_encoding` fallback correctly detects UTF-8 from the raw bytes,
and `response.text` renders curly quotes and non-ASCII content correctly.
The mojibake was an artifact of the inspection tool, not the data or the
production fetch path — no special decoding logic was added to `mofa.py`
as a result, but this is worth knowing before "fixing" an encoding
problem that doesn't actually exist in the real scraper.

**Verification:** 28/28 tests pass (24 existing + 4 new in
`tests/test_mofa.py`, against trimmed real-feed fixtures in
`tests/fixtures/mofa/`). A live run on 2026-07-17 via `python -m
scrapers.mofa` pulled 58 statements (29 press releases + 29 briefings)
with zero skipped items, date range spanning January-July 2026.

**Alternatives considered:** None beyond the three implementation choices
above, each already justified against the two-phase HRW pattern and
CLAUDE.md's stage boundaries.

---

## 2026-07-17 — Bound initial HRW ingestion with a config-driven ingest_start_date

**Decision:** Add `ingest_start_date` to a new `config/pipeline.yaml`
(loaded via `scrapers/config.py`, not hardcoded), set to `2026-01-01`.
`scrapers/hrw.py` gets a new `filter_by_start_date()` function that drops
any event published before this date; it's applied both in `hrw.py`'s own
`__main__` block and in `scrapers/pipeline.py`'s `run()`, so a standalone
HRW run and the full pipeline run behave identically.

**Rationale:** This tracker is real-time by design — it exists to observe
new events and new state responses as they happen, not to reconstruct a
complete historical record. Launching with an open-ended backfill (whatever
happens to still be in HRW's RSS feed) would mean the dataset's early
period is an arbitrary, incomplete slice of history rather than a
deliberate starting point — and because response coding depends on a
30-day window after an event, any event ingested without enough runway
before the launch date would show `no_response` not because the state
actually stayed silent, but because the tracker wasn't watching yet. That
would misrepresent past response patterns as if they were observed, when
they weren't. A clean, known, config-declared start date makes the
dataset's coverage boundary an explicit, citable fact instead of an
accident of whatever the RSS feed happened to contain on launch day.

**This bounds ingestion, not retention.** `ingest_start_date` only
determines which events are picked up during ingestion; it is not
re-applied to the existing dataset on every run, and events already
ingested are never dropped, re-filtered, or expired as they age past this
date. Moving `ingest_start_date` forward later to "clean up" old data
would defeat its purpose and must not be done — if the date ever changes,
it should only be to correct a mistake in the original launch-date choice,
with the change and its reasoning logged here.

**Config over code:** the date lives in `config/pipeline.yaml`, not as a
constant in `scrapers/hrw.py`, per CLAUDE.md's fork-friendly design goal —
a fork with different launch timing (or backfill needs) can change one
YAML value instead of editing scraper code.

**Alternatives considered:**
- **No start date (full backfill of whatever HRW's feed exposes).**
  Rejected for the reason above — the response-window mechanics would
  silently mislabel early events as `no_response` when the real answer is
  "the tracker didn't exist yet to observe a response."
- **Hardcode the date in `scrapers/hrw.py`.** Simpler, but violates
  CLAUDE.md's "config over code" principle and this project's existing
  pattern (news-type inclusion is already a constant *in* `hrw.py`, but a
  date a forker is likely to want to change on day one belongs in config,
  not in a file they'd have to read the source of to find).
- **Apply the filter inside `fetch_events()`, pre-fetch, using the RSS
  index's `pubDate` before fetching the article page.** Would save a
  request per stale item, but HRW's RSS feed only ever carries recent
  items in practice, so the savings are negligible; kept the filter as a
  simple post-fetch step (same pattern as `filter_by_news_type`) for
  testability and consistency instead.

---

<!--
Template for new entries:

## YYYY-MM-DD — Short decision title

**Decision:** What was decided.

**Rationale:** Why.

**Alternatives considered:** What else was on the table and why it lost.
-->
