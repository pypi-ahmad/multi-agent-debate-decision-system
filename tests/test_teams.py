# Copyright (c) 2026 Ahmad Mujtaba
from __future__ import annotations

from debate_decision_system.agents.huddle import huddle_node
from debate_decision_system.graph import initial_state, next_action
from debate_decision_system.teams import (
    TEAM_TEMPLATES,
    is_team,
    members_from_template,
    public_voice,
)


def test_individual_skips_huddle() -> None:
    state = initial_state("Q", "Ollama", "m", 2, 1)
    assert not is_team(state["debaters"][0])
    state["awaiting_speech"] = True
    state["transcript"] = [{"role": "tool", "name": "tool:docs", "content": "x"}]
    assert next_action(state) == "debater"


def test_team_huddle_then_leader(monkeypatch) -> None:
    members = members_from_template("Engineering", "Ollama", "m")
    assert members[0]["is_leader"] is True
    seats = [
        {"name": "Engineering", "kind": "team", "members": members},
        {
            "name": "Product",
            "kind": "team",
            "members": members_from_template("Product", "Ollama", "m"),
        },
    ]
    state = initial_state("Q", "Ollama", "m", 2, 1, seats=seats)
    assert is_team(state["debaters"][0])
    assert public_voice(state["debaters"][0])["name"] == "Engineering"
    state["awaiting_speech"] = True
    state["transcript"] = [{"role": "moderator", "name": "Moderator", "content": "go"}]
    assert next_action(state) == "huddle"
    monkeypatch.setattr(
        "debate_decision_system.agents.huddle.get_chat_model",
        lambda *_a, **_k: type(
            "C",
            (),
            {"invoke": staticmethod(lambda _m: type("M", (), {"text": "Ship small."})())},
        )(),
    )
    out = huddle_node(state)
    assert out["transcript"][0]["role"] == "huddle"
    assert out["transcript"][0]["name"].startswith("Engineering /")
    assert "Engineering" in TEAM_TEMPLATES


def test_mix_agent_and_team() -> None:
    seats = [
        {
            "name": "Pragmatist",
            "kind": "agent",
            "style": "x",
            "instructions": "y",
            "provider": "Ollama",
            "model": "m",
            "members": [],
        },
        {
            "name": "Security",
            "kind": "team",
            "members": members_from_template("Security", "Ollama", "m"),
        },
    ]
    state = initial_state("Q", "Ollama", "m", 2, 1, seats=seats)
    assert state["debaters"][0]["kind"] == "agent"
    assert state["debaters"][1]["kind"] == "team"
    state["transcript"] = [{"role": "tool", "name": "tool:docs", "content": "x"}]
    state["awaiting_speech"] = True
    state["next_speaker"] = 0
    assert next_action(state) == "debater"
    state["next_speaker"] = 1
    assert next_action(state) == "huddle"
