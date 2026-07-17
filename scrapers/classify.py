"""Stage 1, second half: is this a state-perpetrated human rights violation?

CLAUDE.md specifies this as "an LLM classification call: 'Is the government
the responsible actor?'". A live pipeline run on 2026-07-17 also surfaced a
prior question the filter needs to answer first: does the item describe a
discrete incident at all? ("Immersive Documentary Centers Human Rights in
Climate Crisis" passed the News Release filter but is a film premiere
announcement, not a violation report.) Both checks are asked in one call --
see prompts/state_perpetrator_filter.txt for the full instructions,
calibration examples, and the exact inclusion/exclusion rules. See
DECISIONS.md for why both checks live in one prompt.

Uses the Anthropic API (claude-opus-4-8) with structured JSON output, so the
response always parses -- no free-text scraping of the model's answer.
Requires ANTHROPIC_API_KEY (or an equivalent credential the SDK can resolve)
in the environment; raises clearly if none is available rather than
silently skipping classification. Never called from tests with a live key --
tests inject a fake client that mimics the `.messages.create()` interface.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import anthropic

MODEL = "claude-opus-4-8"
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "state_perpetrator_filter.txt"

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "is_incident": {
            "type": "boolean",
            "description": "True if the item reports a discrete, datable incident (Check 1).",
        },
        "is_state_perpetrated": {
            "type": "boolean",
            "description": "True if the incident was committed by the government or its agents (Check 2). Must be false if is_incident is false.",
        },
        "perpetrator": {
            "type": ["string", "null"],
            "description": "The specific actor identified, or null if none is named or is_state_perpetrated is false.",
        },
        "rationale": {
            "type": "string",
            "description": "One or two sentences citing what in the text drove each answer.",
        },
    },
    "required": ["is_incident", "is_state_perpetrated", "perpetrator", "rationale"],
    "additionalProperties": False,
}


class MissingCredentialsError(RuntimeError):
    pass


@dataclass
class ClassificationResult:
    event_id: str
    is_incident: bool
    is_state_perpetrated: bool
    perpetrator: str | None
    rationale: str

    @property
    def passes(self) -> bool:
        return self.is_incident and self.is_state_perpetrated

    def to_dict(self) -> dict:
        return asdict(self)


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_client() -> anthropic.Anthropic:
    """Raises MissingCredentialsError rather than letting the SDK's own
    error surface, so callers can give a clearer message about what's
    needed and why (see CONTRIBUTING.md)."""
    has_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not has_key:
        raise MissingCredentialsError(
            "ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN) is not set. Event "
            "classification calls the Anthropic API and needs a credential -- "
            "see CONTRIBUTING.md for how to provide one locally and in CI."
        )
    return anthropic.Anthropic()


def _event_text(event: Any) -> str:
    return getattr(event, "body", "") or getattr(event, "summary", "") or ""


def classify_event(event: Any, client: anthropic.Anthropic) -> ClassificationResult:
    """`event` must expose .id, .title, .countries, and .body/.summary."""
    user_content = (
        f"{load_prompt()}\n\n---\n\n"
        f"TITLE: {event.title}\n"
        f"COUNTRIES: {', '.join(getattr(event, 'countries', []))}\n\n"
        f"TEXT:\n{_event_text(event)}"
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        output_config={"format": {"type": "json_schema", "schema": RESPONSE_SCHEMA}},
        messages=[{"role": "user", "content": user_content}],
    )
    text = next(block.text for block in response.content if block.type == "text")
    payload = json.loads(text)
    return ClassificationResult(
        event_id=event.id,
        is_incident=payload["is_incident"],
        is_state_perpetrated=payload["is_state_perpetrated"],
        perpetrator=payload.get("perpetrator"),
        rationale=payload["rationale"],
    )


def classify_events(
    events: list[Any], client: anthropic.Anthropic
) -> tuple[list[Any], list[ClassificationResult]]:
    """Classifies every event and returns (events that pass both checks,
    every classification result -- including the ones filtered out, for
    audit)."""
    results = [classify_event(event, client) for event in events]
    passing = [event for event, result in zip(events, results) if result.passes]
    return passing, results
