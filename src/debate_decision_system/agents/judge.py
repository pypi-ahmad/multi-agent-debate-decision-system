# Copyright (c) 2026 Ahmad Mujtaba
"""Judge: reads the transcript and writes a final verdict."""

from __future__ import annotations

from pydantic import BaseModel, Field

from debate_decision_system.llm import format_transcript, get_chat_model
from debate_decision_system.retrieve import knowledge_block
from debate_decision_system.state import DebateState, SpeechScore, Verdict


class SpeechScoreModel(BaseModel):
    speaker: str = Field(description="Debater name for this speech")
    clarity: int = Field(description="0-10", ge=0, le=10)
    logic: int = Field(description="0-10", ge=0, le=10)
    evidence: int = Field(description="0-10", ge=0, le=10)
    persuasiveness: int = Field(description="0-10", ge=0, le=10)


class JudgeOutput(BaseModel):
    winner: str = Field(description="Winning persona name, or Split if no clear winner")
    recommendation: str = Field(description="The action the user should take")
    rationale: str = Field(description="Why this recommendation follows from the debate")
    scores: list[SpeechScoreModel] = Field(
        default_factory=list,
        description="One score row per debater speech",
    )
    outcome: str = Field(
        default="clear_winner",
        description="clear_winner, consensus, or split",
    )
    confidence: int = Field(default=50, ge=0, le=100, description="0-100")
    strongest_arguments: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)


def judge_node(state: DebateState) -> dict:
    names = ", ".join(d["name"] for d in state["debaters"])
    system = (
        "You are the judge of a decision debate. Score arguments, not eloquence. "
        f"Winner must be one of: {names}, or Split. "
        "Give a concrete recommendation the user can act on. "
        "Score each debater speech 0-10 on clarity, logic, evidence, persuasiveness. "
        "Set outcome to clear_winner, consensus, or split. "
        "List strongest arguments and key risks. Confidence 0-100."
    )
    options = state.get("options") or []
    option_block = ("\nOptions:\n" + "\n".join(f"- {item}" for item in options)) if options else ""
    human = (
        f"Decision question: {state['topic']}{option_block}\n\n"
        f"Full debate:\n{format_transcript(list(state.get('transcript', [])), limit=24)}"
        f"{knowledge_block(state)}"
    )
    try:
        provider = state.get("judge_provider") or state["provider"]
        model = state.get("judge_model") or state["model"]
        temp = float(state.get("temperature", 0.4))
        llm = get_chat_model(provider, model, temperature=temp)
        raw = llm.with_structured_output(JudgeOutput).invoke([("system", system), ("human", human)])
        result = raw if isinstance(raw, JudgeOutput) else JudgeOutput.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        verdict = {
            "winner": "Split",
            "recommendation": "Re-run the debate or decide manually.",
            "rationale": f"Judge failed: {exc}",
            "scores": [],
            "outcome": "split",
            "confidence": 0,
            "strongest_arguments": [],
            "key_risks": [],
        }
        return {
            "phase": "judge",
            "verdict": verdict,
            "transcript": [
                {
                    "role": "judge",
                    "name": "Judge",
                    "content": verdict["rationale"],
                }
            ],
            "errors": [f"judge: {exc}"],
        }

    scores: list[SpeechScore] = [
        {
            "speaker": row.speaker,
            "clarity": row.clarity,
            "logic": row.logic,
            "evidence": row.evidence,
            "persuasiveness": row.persuasiveness,
        }
        for row in result.scores
    ]
    verdict: Verdict = {
        "winner": result.winner,
        "recommendation": result.recommendation,
        "rationale": result.rationale,
        "scores": scores,
        "outcome": result.outcome
        if result.outcome in {"clear_winner", "consensus", "split"}
        else "split",
        "confidence": result.confidence,
        "strongest_arguments": list(result.strongest_arguments),
        "key_risks": list(result.key_risks),
    }
    content = (
        f"**Outcome:** {verdict['outcome']} ({verdict['confidence']}%)\n\n"
        f"**Winner:** {result.winner}\n\n"
        f"**Recommendation:** {result.recommendation}\n\n"
        f"{result.rationale}"
    )
    return {
        "phase": "judge",
        "verdict": verdict,
        "transcript": [{"role": "judge", "name": "Judge", "content": content}],
    }
