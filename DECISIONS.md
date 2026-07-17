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

<!--
Template for new entries:

## YYYY-MM-DD — Short decision title

**Decision:** What was decided.

**Rationale:** Why.

**Alternatives considered:** What else was on the table and why it lost.
-->
