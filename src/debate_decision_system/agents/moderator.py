# Copyright (c) 2026 Ahmad Mujtaba
"""Moderator: opens the debate, picks the next speaker, or sends it to the judge."""

from __future__ import annotations

from debate_decision_system.llm import format_transcript, get_chat_model, message_text
from debate_decision_system.retrieve import knowledge_block
from debate_decision_system.state import DebaterSpec, DebateState


def max_speeches(state: DebateState) -> int:
    return int(state["max_rounds"]) * len(state["debaters"])


def should_judge(state: DebateState) -> bool:
    return int(state.get("speeches_done", 0)) >= max_speeches(state)


def next_speaker_index(state: DebateState) -> int:
    n = len(state["debaters"])
    done = int(state.get("speeches_done", 0))
    order = state.get("speaking_order", "sequential")
    if order == "reverse":
        return (n - 1 - (done % n)) % n
    if order == "random":
        # hash() of a tuple containing strings is salted per-process (CPython
        # hash randomization), so this is NOT reproducible across restarts even
        # for the same topic/debaters — it only needs to be stable *within* one
        # run, which it is (same inputs -> same hash for the life of the process).
        seed = hash((state.get("topic", ""), done, tuple(d["name"] for d in state["debaters"])))
        return seed % n
    return done % n


def _roster(debaters: list[DebaterSpec]) -> str:
    return ", ".join(
        f"{d['name']} (team)" if d.get("kind") == "team" else f"{d['name']} ({d['style']})"
        for d in debaters
    )


def moderator_node(state: DebateState) -> dict:
    if should_judge(state):
        return {"phase": "judge"}

    speaker = state["debaters"][next_speaker_index(state)]
    opening = not state.get("transcript")
    if opening:
        system = (
            "You are the debate moderator. Open in 3 short sentences: restate the "
            "question, name the speakers, and give the first speaker the floor. "
            "Do not argue a side."
        )
        options = state.get("options") or []
        option_block = (
            ("\nOptions:\n" + "\n".join(f"- {item}" for item in options)) if options else ""
        )
        human = (
            f"Question: {state['topic']}{option_block}\n"
            f"Speakers: {_roster(state['debaters'])}\n"
            f"First speaker: {speaker['name']}\n"
            f"Rounds: {state['max_rounds']}"
            f"{knowledge_block(state)}"
        )
    else:
        system = (
            "You are the debate moderator. In 2 short sentences, acknowledge the "
            "last speech and hand the floor to the named next speaker. Stay neutral. "
            "If the last speech made a claim with no metric or source, add one "
            "evidence request before giving the floor."
        )
        options = state.get("options") or []
        option_block = (
            ("\nOptions:\n" + "\n".join(f"- {item}" for item in options)) if options else ""
        )
        human = (
            f"Question: {state['topic']}{option_block}\n"
            f"Next speaker: {speaker['name']}\n"
            f"Recent debate:\n{format_transcript(list(state.get('transcript', [])), limit=4)}"
            f"{knowledge_block(state)}"
        )

    try:
        provider = state.get("moderator_provider") or state["provider"]
        model = state.get("moderator_model") or state["model"]
        temp = float(state.get("temperature", 0.4))
        llm = get_chat_model(provider, model, temperature=temp)
        content = message_text(llm.invoke([("system", system), ("human", human)]))
    except Exception as exc:  # noqa: BLE001
        content = f"{speaker['name']} has the floor."
        return {
            "phase": "debate",
            "next_speaker": next_speaker_index(state),
            "transcript": [{"role": "moderator", "name": "Moderator", "content": content}],
            "errors": [f"moderator: {exc}"],
        }

    return {
        "phase": "debate",
        "next_speaker": next_speaker_index(state),
        "transcript": [{"role": "moderator", "name": "Moderator", "content": content}],
    }
