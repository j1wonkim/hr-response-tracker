import json
from dataclasses import dataclass, field

import pytest

from scrapers.classify import (
    MissingCredentialsError,
    build_client,
    classify_event,
    classify_events,
    load_prompt,
)


@dataclass
class FakeEvent:
    id: str
    title: str
    countries: list[str] = field(default_factory=list)
    body: str = ""
    summary: str = ""


class _FakeTextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeResponse:
    def __init__(self, payload: dict):
        self.content = [_FakeTextBlock(json.dumps(payload))]


class _FakeMessages:
    """Mimics client.messages.create() -- returns queued payloads in order,
    never touches the network. Fixture-based-test spirit extended to LLM
    calls: no live API calls in the test suite."""

    def __init__(self, payloads: list[dict]):
        self._payloads = list(payloads)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse(self._payloads.pop(0))


class FakeClient:
    def __init__(self, payloads: list[dict]):
        self.messages = _FakeMessages(payloads)


def test_load_prompt_contains_both_checks():
    text = load_prompt()
    assert "CHECK 1" in text
    assert "CHECK 2" in text


def test_build_client_raises_without_credentials(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    with pytest.raises(MissingCredentialsError):
        build_client()


def test_build_client_succeeds_with_api_key_env_var(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-for-test")
    client = build_client()
    assert client is not None


def test_classify_event_incident_and_state_perpetrated():
    event = FakeEvent(
        id="h1",
        title="Uganda: Military Seizing Government Critics",
        countries=["Uganda"],
        body="Uganda's military unlawfully detained a lawyer and an activist in June and July 2026.",
    )
    client = FakeClient([
        {
            "is_incident": True,
            "is_state_perpetrated": True,
            "perpetrator": "Uganda military / UPDF",
            "rationale": "Names specific individuals, dates, and the UPDF as the actor.",
        }
    ])

    result = classify_event(event, client)

    assert result.event_id == "h1"
    assert result.is_incident is True
    assert result.is_state_perpetrated is True
    assert result.perpetrator == "Uganda military / UPDF"
    assert result.passes is True

    # verify the prompt actually included the event's own title/countries/text
    sent_content = client.messages.calls[0]["messages"][0]["content"]
    assert "Uganda: Military Seizing Government Critics" in sent_content
    assert "Uganda" in sent_content


def test_classify_event_not_an_incident_fails():
    event = FakeEvent(
        id="h2",
        title="Immersive Documentary Centers Human Rights in Climate Crisis",
        countries=["Solomon Islands"],
        body="A new immersive documentary will premiere at the Venice Film Festival.",
    )
    client = FakeClient([
        {
            "is_incident": False,
            "is_state_perpetrated": False,
            "perpetrator": None,
            "rationale": "This is a documentary premiere announcement, not a specific violation.",
        }
    ])

    result = classify_event(event, client)

    assert result.is_incident is False
    assert result.passes is False


def test_classify_event_incident_but_not_state_perpetrated_fails():
    event = FakeEvent(
        id="h3",
        title="Gang Violence Displaces Thousands",
        countries=["Country"],
        body="Criminal gangs, not government forces, drove the displacement.",
    )
    client = FakeClient([
        {
            "is_incident": True,
            "is_state_perpetrated": False,
            "perpetrator": None,
            "rationale": "A criminal gang is the described perpetrator, not the government.",
        }
    ])

    result = classify_event(event, client)

    assert result.is_incident is True
    assert result.is_state_perpetrated is False
    assert result.passes is False


def test_classify_events_filters_to_passing_only():
    events = [
        FakeEvent(id="h1", title="Uganda: Military Seizing Government Critics", countries=["Uganda"], body="..."),
        FakeEvent(id="h2", title="Immersive Documentary Centers Human Rights in Climate Crisis", countries=[], body="..."),
    ]
    client = FakeClient([
        {"is_incident": True, "is_state_perpetrated": True, "perpetrator": "Uganda military", "rationale": "..."},
        {"is_incident": False, "is_state_perpetrated": False, "perpetrator": None, "rationale": "..."},
    ])

    passing, results = classify_events(events, client)

    assert [e.id for e in passing] == ["h1"]
    assert len(results) == 2  # audit trail includes the filtered-out one too


def test_classify_event_falls_back_to_summary_when_no_body():
    event = FakeEvent(id="h4", title="Test", countries=[], body="", summary="Summary text only")
    client = FakeClient([
        {"is_incident": True, "is_state_perpetrated": True, "perpetrator": "X", "rationale": "..."}
    ])

    classify_event(event, client)

    sent_content = client.messages.calls[0]["messages"][0]["content"]
    assert "Summary text only" in sent_content
