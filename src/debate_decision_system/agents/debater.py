# Copyright (c) 2026 Ahmad Mujtaba
"""Debater: one persona speaks, then the graph returns to the moderator."""

from __future__ import annotations

from debate_decision_system.llm import format_transcript, get_chat_model, message_text
from debate_decision_system.retrieve import knowledge_block
from debate_decision_system.state import DebaterSpec, DebateState


def current_debater(state: DebateState) -> DebaterSpec:
    return state["debaters"][int(state.get("next_speaker", 0))]


def debater_node(state: DebateState) -> dict:
    speaker = current_debater(state)
    system = (
        f"You are {speaker['name']}, a debate participant. "
        f"Reasoning style: {speaker['style']}. {speaker['instructions']} "
        "Reply in at most 180 words. Make one clear claim, one reason, and one "
        "named rebuttal to a prior point. If the last turn is an evidence request, "
        "answer only with a source, metric, uploaded-doc cite, or 'no evidence'. "
        "Do not play other roles."
    )
    options = state.get("options") or []
    option_block = ("\nOptions:\n" + "\n".join(f"- {item}" for item in options)) if options else ""
    human = (
        f"Decision question: {state['topic']}{option_block}\n\n"
        f"Debate so far:\n{format_transcript(list(state.get('transcript', [])), limit=8)}"
        f"{knowledge_block(state)}"
    )
    try:
        provider = speaker.get("provider") or state["provider"]
        model = speaker.get("model") or state["model"]
        temp = float(state.get("temperature", 0.4))
        llm = get_chat_model(provider, model, temperature=temp)
        content = message_text(llm.invoke([("system", system), ("human", human)]))
    except Exception as exc:  # noqa: BLE001
        content = f"{speaker['name']} could not speak this turn."
        return {
            "speeches_done": int(state.get("speeches_done", 0)) + 1,
            "transcript": [{"role": "debater", "name": speaker["name"], "content": content}],
            "errors": [f"debater:{speaker['name']}: {exc}"],
        }

    return {
        "speeches_done": int(state.get("speeches_done", 0)) + 1,
        "transcript": [{"role": "debater", "name": speaker["name"], "content": content}],
    }
