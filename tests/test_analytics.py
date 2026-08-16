# Copyright (c) 2026 Ahmad Mujtaba
from __future__ import annotations

from debate_decision_system.analytics import (
    circular_pairs,
    persona_win_rates,
    quality_report,
    reset_for_rerun,
    run_until_done,
    strength_over_time,
    token_overlap,
)
from debate_decision_system.graph import debate_done, initial_state


def test_overlap_and_circular() -> None:
    assert token_overlap("ship the smallest slice now", "ship the smallest slice today") > 0.55
    state = initial_state("Q", "Ollama", "m", 2, 1)
    state["transcript"] = [
        {"role": "debater", "name": "A", "content": "ship the smallest slice now please"},
        {"role": "debater", "name": "B", "content": "ship the smallest slice now today"},
    ]
    pairs = circular_pairs(state)
    assert pairs
    assert pairs[0]["overlap"] >= 0.55


def test_win_rates_and_quality() -> None:
    records = [
        {"status": "decided", "winner": "Pragmatist"},
        {"status": "decided", "winner": "Pragmatist"},
        {"status": "decided", "winner": "Skeptic"},
    ]
    rates = persona_win_rates(records)
    assert rates["Pragmatist"] == 2
    state = initial_state("Q", "Ollama", "m", 2, 1)
    state["verdict"] = {
        "winner": "Pragmatist",
        "confidence": 70,
        "scores": [{"speaker": "A", "clarity": 8, "logic": 8, "evidence": 4, "persuasiveness": 8}],
        "transcript": [],
    }
    state["transcript"] = [{"role": "debater", "name": "A", "content": "one unique claim"}]
    report = quality_report(state)
    assert report["winner"] == "Pragmatist"
    assert report["strength_series"][0] == 7.0
    assert "balance" in report["summary"].lower() or "Participation" in report["summary"]


def test_reset_and_run_until_done() -> None:
    state = initial_state("Q", "Ollama", "m", 2, 1)
    state["transcript"] = [{"role": "judge", "name": "Judge", "content": "done"}]
    state["verdict"] = {"winner": "A", "recommendation": "x"}
    fresh = reset_for_rerun(state, model="other", batch_id="batch1")
    assert fresh["transcript"] == []
    assert fresh["verdict"] == {}
    assert fresh["debate_id"] != state["debate_id"]
    assert fresh["model"] == "other"
    assert fresh["batch_id"] == "batch1"
    assert fresh["debaters"][0]["model"] == "other"

    def stepper(current):
        current = dict(current)
        current["verdict"] = {"winner": "B"}
        current["transcript"] = [{"role": "judge", "name": "Judge", "content": "ok"}]
        return current

    done = run_until_done(initial_state("Q", "Ollama", "m", 2, 1), stepper)
    assert debate_done(done)
    assert done["verdict"]["winner"] == "B"


def test_strength_over_time() -> None:
    state = initial_state("Q", "Ollama", "m", 2, 1)
    state["verdict"] = {
        "scores": [
            {"speaker": "A", "clarity": 8, "logic": 8, "evidence": 8, "persuasiveness": 8},
        ]
    }
    series = strength_over_time([("2026-08-16T10:00:00", state)])
    assert series["2026-08-16"] == 8.0
