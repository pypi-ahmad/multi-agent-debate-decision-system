# Copyright (c) 2026 Ahmad Mujtaba
"""LangGraph wiring: moderator <-> debater, then judge."""

from __future__ import annotations

import uuid
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from debate_decision_system.agents.debater import debater_node
from debate_decision_system.agents.judge import judge_node
from debate_decision_system.agents.moderator import moderator_node, should_judge
from debate_decision_system.agents.structure import options_node, pros_cons_node
from debate_decision_system.config import (
    DEFAULT_SPEAKING_ORDER,
    DEFAULT_TEMPERATURE,
    MIN_DEBATERS,
    SPEAKING_ORDERS,
)
from debate_decision_system.personas import assign_personas, select_personas
from debate_decision_system.state import DebaterSpec, DebateState, Document, Provider


def route_after_moderator(state: DebateState) -> str:
    """Moderator either gives the floor or closes the hearing."""
    if state.get("phase") == "judge" or should_judge(state):
        return "judge"
    return "debater"


def route_start(state: DebateState) -> str:
    if state.get("mode") == "structured" and state.get("phase") == "options":
        return "options"
    return "moderator"


def build_graph() -> Any:  # noqa: ANN401
    graph = StateGraph(cast(Any, DebateState))
    graph.add_node("options", options_node)
    graph.add_node("pros_cons", pros_cons_node)
    graph.add_node("moderator", moderator_node)
    graph.add_node("debater", debater_node)
    graph.add_node("judge", judge_node)
    graph.add_conditional_edges(START, route_start, ["options", "moderator"])
    graph.add_edge("options", "pros_cons")
    graph.add_edge("pros_cons", "moderator")
    graph.add_conditional_edges("moderator", route_after_moderator, ["debater", "judge"])
    graph.add_edge("debater", "moderator")
    graph.add_edge("judge", END)
    return graph.compile()


debate_graph = build_graph()


def initial_state(  # noqa: PLR0913
    topic: str,
    provider: str,
    model: str,
    debater_count: int,
    max_rounds: int,
    *,
    temperature: float = DEFAULT_TEMPERATURE,
    speaking_order: str = DEFAULT_SPEAKING_ORDER,
    persona_names: list[str] | None = None,
    seat_models: list[tuple[str, str]] | None = None,
    moderator_provider: str | None = None,
    moderator_model: str | None = None,
    judge_provider: str | None = None,
    judge_model: str | None = None,
    mode: str = "open",
    local_only: bool = False,
    documents: list[Document] | None = None,
) -> DebateState:
    if provider not in {"Ollama", "OpenAI", "Agnes AI", "Google"}:
        msg = f"Unknown provider: {provider}"
        raise ValueError(msg)
    if speaking_order not in SPEAKING_ORDERS:
        msg = f"Unknown speaking order: {speaking_order}"
        raise ValueError(msg)
    if mode not in {"open", "structured"}:
        msg = f"Unknown mode: {mode}"
        raise ValueError(msg)
    if local_only:
        provider = "Ollama"
        moderator_provider = "Ollama"
        judge_provider = "Ollama"
        if seat_models:
            seat_models = [("Ollama", model or seat[1]) for seat in seat_models]
    picked = select_personas(persona_names) if persona_names else []
    if len(picked) < MIN_DEBATERS:
        picked = assign_personas(debater_count)
    debaters: list[DebaterSpec] = []
    for i, persona in enumerate(picked):
        if seat_models and i < len(seat_models):
            seat_provider, seat_model = seat_models[i]
        else:
            seat_provider, seat_model = provider, model
        debaters.append(
            {
                "name": persona.name,
                "style": persona.style,
                "instructions": persona.instructions,
                "provider": cast(Provider, seat_provider),
                "model": seat_model,
            }
        )
    mod_provider = moderator_provider or provider
    judg_provider = judge_provider or provider
    phase = "options" if mode == "structured" else "debate"
    return cast(
        DebateState,
        {
            "debate_id": uuid.uuid4().hex[:12],
            "topic": topic.strip(),
            "mode": mode,
            "provider": provider,
            "model": model,
            "moderator_provider": mod_provider,
            "moderator_model": moderator_model or model,
            "judge_provider": judg_provider,
            "judge_model": judge_model or model,
            "temperature": temperature,
            "speaking_order": speaking_order,
            "local_only": local_only,
            "max_rounds": max_rounds,
            "debaters": debaters,
            "next_speaker": 0,
            "speeches_done": 0,
            "phase": phase,
            "options": [],
            "pros_cons": "",
            "documents": list(documents or []),
            "transcript": [],
            "verdict": {},
            "errors": [],
        },
    )


def apply_update(state: DebateState, update: dict[str, Any]) -> DebateState:
    merged: dict[str, Any] = dict(state)
    for key, value in update.items():
        if key in {"transcript", "errors"}:
            prior = merged.get(key)
            base = list(prior) if isinstance(prior, list) else []
            extra = list(value) if isinstance(value, list) else []
            merged[key] = base + extra
        else:
            merged[key] = value
    return cast(DebateState, merged)


def debate_done(state: DebateState) -> bool:
    turns = state.get("transcript") or []
    return bool(state.get("verdict")) or (bool(turns) and turns[-1]["role"] == "judge")


def next_action(state: DebateState) -> str:  # noqa: PLR0911
    if debate_done(state):
        return "end"
    phase = state.get("phase")
    if phase == "options":
        return "options"
    if phase == "pros_cons":
        return "pros_cons"
    if phase == "judge":
        return "judge"
    turns = state.get("transcript") or []
    if should_judge(state) or not turns or turns[-1]["role"] in {"debater", "human"}:
        return "moderator"
    if turns[-1]["role"] == "moderator":
        if turns[-1]["name"] == "Analyst":
            return "moderator"
        return "debater"
    return "end"


def advance(state: DebateState) -> DebateState:
    action = next_action(state)
    if action == "options":
        return apply_update(state, options_node(state))
    if action == "pros_cons":
        return apply_update(state, pros_cons_node(state))
    if action == "moderator":
        return apply_update(state, moderator_node(state))
    if action == "debater":
        return apply_update(state, debater_node(state))
    if action == "judge":
        return apply_update(state, judge_node(state))
    return state


def request_evidence(state: DebateState) -> DebateState:
    if debate_done(state):
        return state
    turns = state.get("transcript") or []
    last_debater = next((turn for turn in reversed(turns) if turn["role"] == "debater"), None)
    if last_debater is None:
        return state
    names = [spec["name"] for spec in state["debaters"]]
    try:
        idx = names.index(last_debater["name"])
    except ValueError:
        idx = int(state.get("next_speaker", 0))
    return apply_update(
        state,
        {
            "next_speaker": idx,
            "transcript": [
                {
                    "role": "moderator",
                    "name": "Moderator",
                    "content": (
                        f"Evidence request for {last_debater['name']}: cite a source, "
                        "metric, or uploaded document. If none exist, say so."
                    ),
                }
            ],
        },
    )


def inject_human(state: DebateState, text: str) -> DebateState:
    content = text.strip()
    if not content or debate_done(state):
        return state
    return apply_update(
        state,
        {"transcript": [{"role": "human", "name": "Human", "content": content}]},
    )
