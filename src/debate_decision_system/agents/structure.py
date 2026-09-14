# Copyright (c) 2026 Ahmad Mujtaba
"""Structured decision: options, then pros/cons."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from debate_decision_system.config import MIN_DEBATERS
from debate_decision_system.llm import get_chat_model
from debate_decision_system.retrieve import knowledge_block
from debate_decision_system.state import DebateState


class OptionsOut(BaseModel):
    options: list[str] = Field(description="2-4 mutually exclusive options")


class ProsConsOut(BaseModel):
    analysis: str = Field(description="Pros and cons for each option, markdown")


def _llm(state: DebateState) -> BaseChatModel:
    provider = state.get("moderator_provider") or state["provider"]
    model = state.get("moderator_model") or state["model"]
    temp = float(state.get("temperature", 0.4))
    return get_chat_model(provider, model, temperature=temp)


def options_node(state: DebateState) -> dict:
    system = (
        "You define the decision space. Return 2-4 mutually exclusive options. "
        "Do not pick a winner."
    )
    human = f"Problem: {state['topic']}{knowledge_block(state)}"
    try:
        raw = (
            _llm(state)
            .with_structured_output(OptionsOut)
            .invoke([("system", system), ("human", human)])
        )
        result = raw if isinstance(raw, OptionsOut) else OptionsOut.model_validate(raw)
        options = [item.strip() for item in result.options if item.strip()][:4]
    except Exception as exc:  # noqa: BLE001
        options = [f"Do it: {state['topic']}", f"Do not: {state['topic']}"]
        return {
            "phase": "pros_cons",
            "options": options,
            "transcript": [
                {
                    "role": "moderator",
                    "name": "Analyst",
                    "content": "Options (fallback): " + " | ".join(options),
                }
            ],
            "errors": [f"options: {exc}"],
        }
    # MIN_DEBATERS (2) is reused here as "at least 2 options", not a debater count.
    if len(options) < MIN_DEBATERS:
        options = [f"Do it: {state['topic']}", f"Do not: {state['topic']}"]
    body = "\n".join(f"{i}. {opt}" for i, opt in enumerate(options, start=1))
    return {
        "phase": "pros_cons",
        "options": options,
        "transcript": [
            {"role": "moderator", "name": "Analyst", "content": f"**Options**\n\n{body}"}
        ],
    }


def pros_cons_node(state: DebateState) -> dict:
    options = state.get("options") or []
    listed = "\n".join(f"- {opt}" for opt in options)
    system = "For each option, list 2 pros and 2 cons. Stay neutral. Do not pick a winner."
    human = f"Problem: {state['topic']}\n\nOptions:\n{listed}{knowledge_block(state)}"
    try:
        raw = (
            _llm(state)
            .with_structured_output(ProsConsOut)
            .invoke([("system", system), ("human", human)])
        )
        result = raw if isinstance(raw, ProsConsOut) else ProsConsOut.model_validate(raw)
        analysis = result.analysis.strip()
    except Exception as exc:  # noqa: BLE001
        analysis = "Pros/cons unavailable. Debate the listed options."
        return {
            "phase": "debate",
            "pros_cons": analysis,
            "transcript": [
                {
                    "role": "moderator",
                    "name": "Analyst",
                    "content": f"**Pros / cons**\n\n{analysis}",
                }
            ],
            "errors": [f"pros_cons: {exc}"],
        }
    return {
        "phase": "debate",
        "pros_cons": analysis,
        "transcript": [
            {"role": "moderator", "name": "Analyst", "content": f"**Pros / cons**\n\n{analysis}"}
        ],
    }
