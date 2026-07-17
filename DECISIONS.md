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

<!--
Template for new entries:

## YYYY-MM-DD — Short decision title

**Decision:** What was decided.

**Rationale:** Why.

**Alternatives considered:** What else was on the table and why it lost.
-->
