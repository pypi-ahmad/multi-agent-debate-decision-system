# Copyright (c) 2026 Ahmad Mujtaba
from __future__ import annotations

import json
from io import BytesIO

import pytest
from langchain_core.messages import AIMessage

from debate_decision_system.agents.debater import current_debater, debater_node
from debate_decision_system.agents.judge import JudgeOutput, judge_node
from debate_decision_system.agents.moderator import (
    max_speeches,
    moderator_node,
    next_speaker_index,
    should_judge,
)
from debate_decision_system.agents.structure import OptionsOut, ProsConsOut
from debate_decision_system.config import (
    GOOGLE_MODELS,
    MAX_DEBATERS,
    OPENAI_MODELS,
    list_ollama_models,
    models_for_provider,
    required_key,
)
from debate_decision_system.export import debate_to_markdown, timeline_mermaid
from debate_decision_system.graph import (
    advance,
    debate_done,
    initial_state,
    inject_human,
    next_action,
    request_evidence,
    route_after_moderator,
)
from debate_decision_system.history import list_debates, load_debate, save_debate
from debate_decision_system.llm import format_transcript, get_chat_model, message_text
from debate_decision_system.personas import PERSONAS, assign_personas, select_personas
from debate_decision_system.retrieve import retrieve


def test_assign_personas_clamps_and_is_distinct() -> None:
    two = assign_personas(2)
    assert len(two) == 2
    assert two[0].name != two[1].name
    assert assign_personas(1)[0].name == PERSONAS[0].name
    assert len(assign_personas(99)) == min(MAX_DEBATERS, len(PERSONAS))
    assert select_personas(["Skeptic", "Nope", "Creative"])[0].name == "Skeptic"


def test_provider_catalogs() -> None:
    assert models_for_provider("OpenAI") == OPENAI_MODELS
    assert models_for_provider("Google") == GOOGLE_MODELS
    assert models_for_provider("Agnes AI") == ("agnes-2.5-flash",)
    assert models_for_provider("Ollama") == ()
    assert required_key("Ollama") is None
    assert required_key("OpenAI") == "OPENAI_API_KEY"
    assert required_key("Agnes AI") == "AGNES_API_KEY"
    assert required_key("Google") == "GOOGLE_API_KEY"


def test_list_ollama_models_parses_and_rejects_bad_scheme(monkeypatch) -> None:
    payload = json.dumps({"models": [{"name": "llama3.1:8b"}, {"model": "qwen2.5:7b"}]}).encode()

    def fake_urlopen(_url, timeout=2):  # noqa: ARG001
        return BytesIO(payload)

    monkeypatch.setattr("debate_decision_system.config.urllib.request.urlopen", fake_urlopen)
    assert list_ollama_models("http://localhost:11434") == ["llama3.1:8b", "qwen2.5:7b"]
    assert list_ollama_models("file:///etc/passwd") == []


def test_message_text_and_transcript() -> None:
    assert message_text(AIMessage(content="  hello  ")) == "hello"
    assert (
        message_text(
            AIMessage(content=[{"type": "text", "text": "ab"}, {"type": "text", "text": "c"}])
        )
        == "abc"
    )
    assert format_transcript([]) == "(no speeches yet)"
    rendered = format_transcript(
        [
            {"name": "A", "role": "debater", "content": "one"},
            {"name": "B", "role": "debater", "content": "two"},
        ],
        limit=1,
    )
    assert "B" in rendered
    assert "A" not in rendered


def test_initial_state_and_routing() -> None:
    state = initial_state("Ship or wait?", "Ollama", "llama3.1:8b", 2, 2)
    assert len(state["debaters"]) == 2
    assert state["speeches_done"] == 0
    assert max_speeches(state) == 4
    assert should_judge(state) is False
    assert route_after_moderator(state) == "debater"
    assert next_speaker_index(state) == 0

    state["speeches_done"] = 4
    assert should_judge(state) is True
    assert route_after_moderator(state) == "judge"

    state["speeches_done"] = 1
    state["phase"] = "judge"
    assert route_after_moderator(state) == "judge"


def test_get_chat_model_rejects_bad_inputs(monkeypatch) -> None:
    monkeypatch.setattr("debate_decision_system.config.OPENAI_API_KEY", "")
    monkeypatch.setattr("debate_decision_system.config.AGNES_API_KEY", "")
    monkeypatch.setattr("debate_decision_system.config.GOOGLE_API_KEY", "")
    with pytest.raises(ValueError, match=r"gpt-5\.6-luna"):
        get_chat_model("OpenAI", "gpt-4o")
    with pytest.raises(ValueError, match="Unknown provider"):
        get_chat_model("Nope", "x")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_chat_model("OpenAI", "gpt-5.6-luna")
    with pytest.raises(RuntimeError, match="AGNES_API_KEY"):
        get_chat_model("Agnes AI", "agnes-2.5-flash")
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        get_chat_model("Google", "gemini-3.5-flash-lite")


def test_get_chat_model_ollama() -> None:
    model = get_chat_model("Ollama", "llama3.1:8b")
    assert model is not None


class _FakeChat:
    def __init__(self, text: str) -> None:
        self.text = text

    def invoke(self, _messages):
        return AIMessage(content=self.text)

    def with_structured_output(self, _cls):
        return self

    def invoke_structured(self) -> JudgeOutput:
        return JudgeOutput(winner="Pragmatist", recommendation="Ship", rationale="Clear owner")


class _FakeJudge(_FakeChat):
    def invoke(self, _messages):
        return JudgeOutput(
            winner="Pragmatist", recommendation="Ship it", rationale="Skeptic had no counter"
        )


def test_nodes_with_fake_llm(monkeypatch) -> None:
    state = initial_state("Ship or wait?", "Ollama", "llama3.1:8b", 2, 1)
    monkeypatch.setattr(
        "debate_decision_system.agents.moderator.get_chat_model",
        lambda *_args, **_kwargs: _FakeChat("Pragmatist has the floor."),
    )
    out = moderator_node(state)
    assert out["phase"] == "debate"
    assert out["transcript"][0]["role"] == "moderator"

    state["next_speaker"] = 0
    assert current_debater(state)["name"] == "Pragmatist"
    monkeypatch.setattr(
        "debate_decision_system.agents.debater.get_chat_model",
        lambda *_args, **_kwargs: _FakeChat("Ship the smallest slice."),
    )
    spoken = debater_node(state)
    assert spoken["speeches_done"] == 1
    assert spoken["transcript"][0]["name"] == "Pragmatist"

    state["transcript"] = spoken["transcript"]
    monkeypatch.setattr(
        "debate_decision_system.agents.judge.get_chat_model",
        lambda *_args, **_kwargs: _FakeJudge("unused"),
    )
    judged = judge_node(state)
    assert judged["verdict"]["winner"] == "Pragmatist"
    assert judged["transcript"][0]["role"] == "judge"
    assert judged["verdict"]["scores"] == []
    assert judged["verdict"]["outcome"] == "clear_winner"


def test_speaking_order_reverse_and_random() -> None:
    state = initial_state("Q", "Ollama", "m", 3, 1, speaking_order="reverse")
    assert next_speaker_index(state) == 2
    state["speeches_done"] = 1
    assert next_speaker_index(state) == 1
    state["speaking_order"] = "random"
    assert 0 <= next_speaker_index(state) < 3


def test_debater_uses_seat_model(monkeypatch) -> None:
    state = initial_state("Q", "Ollama", "llama3.1:8b", 2, 1)
    state["debaters"][0]["model"] = "qwen2.5:7b"
    seen: dict[str, str] = {}

    def fake_get(provider, model, temperature=0.4):  # noqa: ARG001
        seen["provider"] = provider
        seen["model"] = model
        return _FakeChat("ok")

    monkeypatch.setattr("debate_decision_system.agents.debater.get_chat_model", fake_get)
    debater_node(state)
    assert seen["model"] == "qwen2.5:7b"
    assert seen["provider"] == "Ollama"


def test_advance_inject_export(monkeypatch) -> None:
    state = initial_state("Ship or wait?", "Ollama", "m", 2, 1, temperature=0.3)
    monkeypatch.setattr(
        "debate_decision_system.agents.moderator.get_chat_model",
        lambda *_a, **_k: _FakeChat("Floor to Pragmatist."),
    )
    monkeypatch.setattr(
        "debate_decision_system.agents.debater.get_chat_model",
        lambda *_a, **_k: _FakeChat("Ship the slice."),
    )
    monkeypatch.setattr(
        "debate_decision_system.agents.judge.get_chat_model",
        lambda *_a, **_k: _FakeJudge("unused"),
    )
    stepped = advance(state)
    assert stepped["transcript"][-1]["role"] == "moderator"
    with_human = inject_human(stepped, "Consider cost.")
    assert with_human["transcript"][-1]["role"] == "human"
    assert inject_human(stepped, "  ") is stepped
    while not debate_done(with_human):
        with_human = advance(with_human)
    assert with_human["verdict"]["winner"] == "Pragmatist"
    md = debate_to_markdown(with_human)
    assert "# Debate: Ship or wait?" in md
    assert "Human (human)" in md
    assert "**Winner:** Pragmatist" in md
    assert "Temperature: 0.3" in md
    with_human["verdict"]["scores"] = [
        {
            "speaker": "Pragmatist",
            "clarity": 8,
            "logic": 7,
            "evidence": 6,
            "persuasiveness": 7,
        }
    ]
    scored = debate_to_markdown(with_human)
    assert "| Pragmatist | 8 | 7 | 6 | 7 |" in scored


class _FakeStructured:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def with_structured_output(self, _cls):
        return self

    def invoke(self, _messages):
        return self.payload


def test_phase3_local_retrieve_history(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("debate_decision_system.history.HISTORY_DIR", tmp_path)
    docs = [{"name": "note.md", "text": "ship the smallest slice this quarter"}]
    state = initial_state(
        "Q",
        "OpenAI",
        "gpt-5.6-luna",
        2,
        1,
        local_only=True,
        documents=docs,
    )
    assert state["provider"] == "Ollama"
    assert state["debaters"][0]["provider"] == "Ollama"
    assert "smallest" in retrieve(docs, "smallest slice")
    save_debate(state)
    loaded = load_debate(str(state["debate_id"]))
    assert loaded["topic"] == "Q"
    assert list_debates()[0]["debate_id"] == state["debate_id"]
    assert "flowchart" in timeline_mermaid(state)


def test_structured_flow_and_evidence(monkeypatch) -> None:
    payloads = [
        _FakeStructured(OptionsOut(options=["Ship", "Wait"])),
        _FakeStructured(ProsConsOut(analysis="Ship: fast. Wait: safer.")),
    ]

    def fake_get(*_a, **_k):
        return payloads.pop(0)

    monkeypatch.setattr("debate_decision_system.agents.structure.get_chat_model", fake_get)
    state = initial_state("Q", "Ollama", "m", 2, 1, mode="structured")
    assert next_action(state) == "options"
    state = advance(state)
    assert state["options"] == ["Ship", "Wait"]
    assert next_action(state) == "pros_cons"
    state = advance(state)
    assert state["phase"] == "debate"
    assert next_action(state) == "moderator"
    state["transcript"].append({"role": "debater", "name": "Pragmatist", "content": "Ship."})
    asked = request_evidence(state)
    assert "Evidence request" in asked["transcript"][-1]["content"]
    assert asked["next_speaker"] == 0
    assert request_evidence(initial_state("Q", "Ollama", "m", 2, 1))["transcript"] == []


def test_should_judge_after_full_roster() -> None:
    state = initial_state("Q", "Ollama", "m", 2, 1)
    state["speeches_done"] = 2
    assert should_judge(state) is True
    assert moderator_node(state) == {"phase": "judge"}
