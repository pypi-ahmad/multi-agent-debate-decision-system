# Copyright (c) 2026 Ahmad Mujtaba
"""Debater: one persona speaks, then the graph returns to the moderator."""

from __future__ import annotations

from debate_decision_system.llm import format_transcript, get_chat_model, message_text
from debate_decision_system.retrieve import knowledge_block
from debate_decision_system.state import DebaterSpec, DebateState
from debate_decision_system.teams import current_seat, is_team, public_voice


def current_debater(state: DebateState) -> DebaterSpec:
    return public_voice(current_seat(state))


def debater_node(state: DebateState) -> dict:
    seat = current_seat(state)
    speaker = public_voice(seat)
    system = (
        f"You are {speaker['name']}, a debate participant. "
        f"Reasoning style: {speaker['style']}. {speaker['instructions']} "
        "Reply in at most 180 words. Make one clear claim, one reason, and one "
        "named rebuttal to a prior point. If the last turn is an evidence request, "
        "answer only with a source, metric, uploaded-doc cite, or 'no evidence'. "
        "Cite every external fact as [filename] or [tool:name]. "
        "Do not play other roles."
    )
    if is_team(seat):
        huddle = [
            turn
            for turn in (state.get("transcript") or [])
            if turn["role"] == "huddle" and str(turn["name"]).startswith(f"{seat.get('name')} /")
        ][-6:]
        notes = "\n".join(f"- {turn['name']}: {turn['content']}" for turn in huddle)
        system += (
            f" You are the leader of team {seat.get('name')}. "
            "State the team's public position. Use the huddle notes. "
            "Do not list every member."
        )
        human = (
            f"Decision question: {state['topic']}\n\n"
            f"Huddle notes:\n{notes or '(no huddle notes)'}\n\n"
            f"Public debate:\n{format_transcript(list(state.get('transcript') or []), limit=8)}"
            f"{knowledge_block(state)}"
        )
    else:
        options = state.get("options") or []
        option_block = (
            ("\nOptions:\n" + "\n".join(f"- {item}" for item in options)) if options else ""
        )
        human = (
            f"Decision question: {state['topic']}{option_block}\n\n"
            f"Debate so far:\n{format_transcript(list(state.get('transcript', [])), limit=8)}"
            f"{knowledge_block(state)}"
        )
    if state.get("grounding") == "grounded":
        system += (
            " GROUNDED MODE: use only uploaded documents plus calculator/code. "
            "No web or Wikipedia. If you cannot cite a document, say you lack evidence."
        )
    try:
        provider = speaker.get("provider") or state["provider"]
        model = speaker.get("model") or state["model"]
        temp = float(state.get("temperature", 0.4))
        llm = get_chat_model(provider, model, temperature=temp)
        content = message_text(llm.invoke([("system", system), ("human", human)]))
        if (
            state.get("grounding") == "grounded"
            and (state.get("documents") or [])
            and "[" not in content
        ):
            retry = (
                human + "\n\nYour draft had no [source] cite. Rewrite and cite a document "
                "or say you lack evidence."
            )
            content = message_text(llm.invoke([("system", system), ("human", retry)]))
    except Exception as exc:  # noqa: BLE001
        content = f"{speaker['name']} could not speak this turn."
        return {
            "speeches_done": int(state.get("speeches_done", 0)) + 1,
            "awaiting_speech": False,
            "huddle_done": False,
            "huddle_index": 0,
            "transcript": [{"role": "debater", "name": speaker["name"], "content": content}],
            "errors": [f"debater:{speaker['name']}: {exc}"],
        }

    return {
        "speeches_done": int(state.get("speeches_done", 0)) + 1,
        "awaiting_speech": False,
        "huddle_done": False,
        "huddle_index": 0,
        "transcript": [{"role": "debater", "name": speaker["name"], "content": content}],
    }
