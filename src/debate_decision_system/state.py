# Copyright (c) 2026 Ahmad Mujtaba
"""LangGraph state for one debate run."""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

Provider = Literal["Ollama", "OpenAI", "Agnes AI", "Google"]
Phase = Literal["options", "pros_cons", "debate", "judge"]
SpeakingOrder = Literal["sequential", "reverse", "random"]
DebateMode = Literal["open", "structured"]
Grounding = Literal["open", "grounded"]
Outcome = Literal["clear_winner", "consensus", "split"]


class Turn(TypedDict):
    role: Literal["moderator", "debater", "judge", "human", "tool", "huddle"]
    name: str
    content: str


class TeamMember(TypedDict, total=False):
    name: str
    style: str
    instructions: str
    provider: Provider
    model: str
    is_leader: bool


class DebaterSpec(TypedDict, total=False):
    name: str
    style: str
    instructions: str
    provider: Provider
    model: str
    kind: Literal["agent", "team"]
    members: list[TeamMember]


class SpeechScore(TypedDict):
    speaker: str
    clarity: int
    logic: int
    evidence: int
    persuasiveness: int


class Document(TypedDict):
    name: str
    text: str


class Verdict(TypedDict, total=False):
    winner: str
    recommendation: str
    rationale: str
    scores: list[SpeechScore]
    outcome: Outcome
    confidence: int
    strongest_arguments: list[str]
    key_risks: list[str]


class DebateState(TypedDict, total=False):
    debate_id: str
    topic: str
    mode: DebateMode
    provider: Provider
    model: str
    moderator_provider: Provider
    moderator_model: str
    judge_provider: Provider
    judge_model: str
    temperature: float
    speaking_order: SpeakingOrder
    local_only: bool
    grounding: Grounding
    batch_id: str
    awaiting_speech: bool
    huddle_done: bool
    huddle_index: int
    max_rounds: int
    debaters: list[DebaterSpec]
    next_speaker: int
    speeches_done: int
    phase: Phase
    options: list[str]
    pros_cons: str
    documents: list[Document]
    rag_enabled: bool
    pinned_ids: list[str]
    transcript: Annotated[list[Turn], operator.add]
    verdict: Verdict
    errors: Annotated[list[str], operator.add]
