# Copyright (c) 2026 Ahmad Mujtaba
"""Markdown export of a finished (or in-progress) debate."""

from __future__ import annotations

from debate_decision_system.state import DebateState, SpeechScore, Turn


def debate_to_markdown(state: DebateState) -> str:
    topic = state.get("topic", "")
    lines = [
        f"# Debate: {topic}",
        "",
        "## Settings",
        f"- Rounds: {state.get('max_rounds', '')}",
        f"- Temperature: {state.get('temperature', '')}",
        f"- Speaking order: {state.get('speaking_order', 'sequential')}",
        f"- Mode: {state.get('mode', 'open')}",
        f"- Outcome: {(state.get('verdict') or {}).get('outcome', '')}",
        "",
    ]
    options = state.get("options") or []
    if options:
        lines.extend(["## Options", "", *[f"- {item}" for item in options], ""])
    if state.get("pros_cons"):
        lines.extend(["## Pros / cons", "", str(state.get("pros_cons")), ""])
    lines.extend(["## Transcript", ""])
    for turn in state.get("transcript") or []:
        lines.extend(_turn_lines(turn))
    scores = (state.get("verdict") or {}).get("scores") or []
    if scores:
        lines.extend(["## Scores", "", _score_table(scores), ""])
    verdict = state.get("verdict") or {}
    if verdict:
        lines.extend(
            [
                "## Judgment",
                "",
                f"**Winner:** {verdict.get('winner', 'Split')}",
                "",
                f"**Recommendation:** {verdict.get('recommendation', '')}",
                "",
                f"**Confidence:** {verdict.get('confidence', '')}",
                "",
            ]
        )
        args = verdict.get("strongest_arguments") or []
        risks = verdict.get("key_risks") or []
        if args:
            lines.extend(["### Strongest arguments", "", *[f"- {item}" for item in args], ""])
        if risks:
            lines.extend(["### Key risks", "", *[f"- {item}" for item in risks], ""])
        lines.extend([verdict.get("rationale", ""), ""])
    return "\n".join(lines).rstrip() + "\n"


def _turn_lines(turn: Turn) -> list[str]:
    return [f"### {turn['name']} ({turn['role']})", "", turn["content"], ""]


def _score_table(scores: list[SpeechScore]) -> str:
    rows = [
        "| Speaker | Clarity | Logic | Evidence | Persuasiveness |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    rows.extend(
        f"| {row['speaker']} | {row['clarity']} | {row['logic']} "
        f"| {row['evidence']} | {row['persuasiveness']} |"
        for row in scores
    )
    return "\n".join(rows)


def timeline_mermaid(state: DebateState) -> str:
    current = state.get("phase", "debate")
    steps = ["problem", "options", "pros_cons", "debate", "judge"]
    if state.get("mode") != "structured":
        steps = ["problem", "debate", "judge"]
    edges = " --> ".join(steps)
    highlight = current if current in steps else "debate"
    return (
        "```mermaid\n"
        f"flowchart LR\n  {edges}\n"
        f"  style {highlight} stroke:#0969da,stroke-width:3px\n"
        "```\n"
    )
