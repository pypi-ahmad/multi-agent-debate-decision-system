# Copyright (c) 2026 Ahmad Mujtaba
"""Debate analytics: strength, wins, circularity, participation, quality."""

from __future__ import annotations

import copy
import uuid
from collections import Counter
from collections.abc import Callable
from itertools import pairwise
from typing import Any, cast

from debate_decision_system.graph import debate_done
from debate_decision_system.state import DebateState

_OVERLAP_FLAG = 0.55  # empirical Jaccard threshold for "these two speeches restate each other"


def token_overlap(left: str, right: str) -> float:
    a = {part.lower() for part in left.split() if len(part) > 2}  # noqa: PLR2004
    b = {part.lower() for part in right.split() if len(part) > 2}  # noqa: PLR2004
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def participation(state: DebateState) -> dict[str, int]:
    counts = Counter(
        turn["name"]
        for turn in state.get("transcript") or []
        if turn["role"] in {"debater", "huddle"}
    )
    return dict(counts)


def circular_pairs(state: DebateState) -> list[dict[str, Any]]:
    speeches = [turn for turn in state.get("transcript") or [] if turn["role"] == "debater"]
    found: list[dict[str, Any]] = []
    for first, second in pairwise(speeches):
        score = token_overlap(first["content"], second["content"])
        if score >= _OVERLAP_FLAG:
            found.append(
                {
                    "left": first["name"],
                    "right": second["name"],
                    "overlap": round(score, 2),
                }
            )
    return found


def strength_series(state: DebateState) -> list[float]:
    rows = (state.get("verdict") or {}).get("scores") or []
    series: list[float] = []
    for row in rows:
        axes = [
            int(row.get("clarity") or 0),
            int(row.get("logic") or 0),
            int(row.get("evidence") or 0),
            int(row.get("persuasiveness") or 0),
        ]
        series.append(sum(axes) / 4)
    return series


def participation_balance(counts: dict[str, int]) -> float:
    if not counts:
        return 1.0
    values = list(counts.values())
    return min(values) / max(values)


def mean_strength(state: DebateState) -> float | None:
    series = strength_series(state)
    if not series:
        return None
    return sum(series) / len(series)


def strength_over_time(states: list[tuple[str, DebateState]]) -> dict[str, float]:
    """Mean argument strength by date (YYYY-MM-DD)."""
    by_day: dict[str, list[float]] = {}
    for day, state in states:
        value = mean_strength(state)
        if value is None:
            continue
        by_day.setdefault(day[:10], []).append(value)
    return {day: sum(vals) / len(vals) for day, vals in sorted(by_day.items())}


def persona_win_rates(records: list[dict[str, Any]]) -> dict[str, int]:
    wins = Counter(
        str(row.get("winner") or "Split")
        for row in records
        if row.get("status") == "decided" or row.get("winner")
    )
    return dict(wins)


def quality_report(state: DebateState) -> dict[str, Any]:
    counts = participation(state)
    circular = circular_pairs(state)
    series = strength_series(state)
    balance = participation_balance(counts)
    verdict = state.get("verdict") or {}
    bits = [
        f"Winner: {verdict.get('winner', 'n/a')}.",
        f"Confidence: {verdict.get('confidence', 'n/a')}.",
        f"Participation balance: {balance:.2f} (1.0 is even).",
    ]
    if circular:
        bits.append(f"Circular pairs flagged: {len(circular)}.")
    else:
        bits.append("No circular consecutive speeches flagged.")
    if series:
        bits.append(f"Mean argument strength: {sum(series) / len(series):.1f}/10.")
    return {
        "participation": counts,
        "circular": circular,
        "strength_series": series,
        "balance": balance,
        "winner": verdict.get("winner", ""),
        "confidence": verdict.get("confidence"),
        "summary": " ".join(bits),
    }


def reset_for_rerun(
    state: DebateState, *, model: str | None = None, batch_id: str | None = None
) -> DebateState:
    """Clone a finished debate back to a fresh, unstarted state, keeping the
    same topic/personas/settings. Used by app_pages/analytics.py to compare
    outcomes across models: pass `model` to swap every seat onto it and
    `batch_id` to group the resulting runs in decision history."""
    fresh = cast(DebateState, copy.deepcopy(dict(state)))
    fresh["debate_id"] = uuid.uuid4().hex[:12]
    fresh["transcript"] = []
    fresh["verdict"] = {}
    fresh["errors"] = []
    fresh["speeches_done"] = 0
    fresh["next_speaker"] = 0
    fresh["awaiting_speech"] = False
    fresh["huddle_done"] = False
    fresh["huddle_index"] = 0
    fresh["options"] = []
    fresh["pros_cons"] = ""
    fresh["phase"] = "options" if state.get("mode") == "structured" else "debate"
    if batch_id:
        fresh["batch_id"] = batch_id
    if model:
        fresh["model"] = model
        fresh["moderator_model"] = model
        fresh["judge_model"] = model
        for seat in fresh.get("debaters") or []:
            seat["model"] = model
            for member in seat.get("members") or []:
                member["model"] = model
    return fresh


def run_until_done(
    state: DebateState,
    advance_fn: Callable[[DebateState], DebateState],
    *,
    limit: int = 80,
) -> DebateState:
    # limit is a circuit breaker against a stuck/looping advance_fn, not an
    # expected debate length (rounds x debaters is normally well under this).
    current = state
    for _ in range(limit):
        if debate_done(current):
            return current
        nxt = advance_fn(current)
        if nxt is current:
            return current
        current = nxt
    return current
