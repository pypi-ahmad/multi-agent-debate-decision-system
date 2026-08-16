# Copyright (c) 2026 Ahmad Mujtaba
from __future__ import annotations

import pytest

from debate_decision_system.graph import initial_state
from debate_decision_system.history import (
    link_decisions,
    list_debates,
    load_debate,
    related_ids,
    save_debate,
    search_decisions,
)


@pytest.fixture
def memory_db(tmp_path, monkeypatch):
    monkeypatch.setattr("debate_decision_system.history.DB_PATH", tmp_path / "decisions.db")
    monkeypatch.setattr("debate_decision_system.history.HISTORY_DIR", tmp_path / "json")
    return tmp_path


def test_save_search_link_resume(memory_db) -> None:  # noqa: ARG001
    first = initial_state("Choose SQLite", "Ollama", "m", 2, 1)
    first["verdict"] = {
        "recommendation": "Use SQLite",
        "confidence": 80,
        "outcome": "clear_winner",
        "winner": "Pragmatist",
        "strongest_arguments": ["Local file, no server"],
        "rationale": "We chose SQLite last month because it is local.",
    }
    save_debate(first)
    second = initial_state("Pick a cache", "Ollama", "m", 2, 1)
    save_debate(second)
    hits = search_decisions("SQLite last month")
    assert hits[0]["debate_id"] == first["debate_id"]
    assert hits[0]["status"] == "decided"
    assert hits[0]["confidence"] == 80
    decided = search_decisions(status="decided", min_confidence=50)
    assert len(decided) == 1
    link_decisions(str(first["debate_id"]), str(second["debate_id"]))
    assert second["debate_id"] in related_ids(str(first["debate_id"]))
    loaded = load_debate(str(first["debate_id"]))
    assert loaded["topic"] == "Choose SQLite"
    assert list_debates()
    with pytest.raises(KeyError, match="Unknown"):
        load_debate("missing")
