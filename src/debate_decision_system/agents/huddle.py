# Copyright (c) 2026 Ahmad Mujtaba
"""Internal team huddle before the leader speaks publicly."""

from __future__ import annotations

from debate_decision_system.llm import format_transcript, get_chat_model, message_text
from debate_decision_system.retrieve import knowledge_block
from debate_decision_system.state import DebateState
from debate_decision_system.teams import current_seat, huddle_members, is_team


def huddle_node(state: DebateState) -> dict:
    """Speaks for exactly one huddle member per call, advancing huddle_index.
    graph.py's advance() calls this repeatedly (one per rerun) until
    huddle_done, the same one-step-per-turn pattern used for public speeches —
    this is what lets the UI show huddle notes appearing one at a time."""
    seat = current_seat(state)
    if not is_team(seat):
        return {"huddle_done": True, "huddle_index": 0}
    members = huddle_members(seat)
    idx = int(state.get("huddle_index") or 0)
    if idx >= len(members):
        return {"huddle_done": True, "huddle_index": 0}
    member = members[idx]
    team = seat.get("name", "Team")
    system = (
        f"You are {member.get('name')} in a private {team} huddle. "
        f"Style: {member.get('style', '')}. {member.get('instructions', '')} "
        "Advise the team in at most 80 words. This is not the public floor."
    )
    human = (
        f"Decision question: {state['topic']}\n"
        f"Public debate:\n{format_transcript(list(state.get('transcript') or []), limit=6)}"
        f"{knowledge_block(state)}"
    )
    try:
        llm = get_chat_model(
            member.get("provider") or state["provider"],
            member.get("model") or state["model"],
            temperature=float(state.get("temperature", 0.4)),
        )
        content = message_text(llm.invoke([("system", system), ("human", human)]))
    except Exception as exc:  # noqa: BLE001
        content = f"{member.get('name')} could not huddle."
        return {
            "huddle_index": idx + 1,
            "huddle_done": idx + 1 >= len(members),
            "transcript": [
                {
                    "role": "huddle",
                    "name": f"{team} / {member.get('name')}",
                    "content": content,
                }
            ],
            "errors": [f"huddle:{team}:{member.get('name')}: {exc}"],
        }
    return {
        "huddle_index": idx + 1,
        "huddle_done": idx + 1 >= len(members),
        "transcript": [
            {
                "role": "huddle",
                "name": f"{team} / {member.get('name')}",
                "content": content,
            }
        ],
    }
