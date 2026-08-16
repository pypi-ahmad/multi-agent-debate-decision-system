# Copyright (c) 2026 Ahmad Mujtaba
from __future__ import annotations

import json
import sqlite3

import pytest

from debate_decision_system.graph import initial_state
from debate_decision_system.memory import (
    archive_decision,
    delete_decision,
    link_decisions,
    list_categories,
    list_debates,
    list_tags,
    load_debate,
    related_ids,
    relevant_decisions,
    save_debate,
    search_decisions,
    update_decision_meta,
)
from debate_decision_system.retrieve import knowledge_block, memory_block


@pytest.fixture
def memory_db(tmp_path, monkeypatch):
    monkeypatch.setattr("debate_decision_system.memory.DB_PATH", tmp_path / "decisions.db")
    monkeypatch.setattr("debate_decision_system.memory.HISTORY_DIR", tmp_path / "json")
    return tmp_path


def _decided(topic: str, recommendation: str, rationale: str = "") -> dict:
    state = initial_state(topic, "Ollama", "m", 2, 1)
    state["verdict"] = {
        "recommendation": recommendation,
        "confidence": 80,
        "outcome": "clear_winner",
        "winner": "Pragmatist",
        "strongest_arguments": ["Local file, no server"],
        "key_risks": ["Single file lock"],
        "rationale": rationale,
    }
    state["transcript"] = [
        {"role": "debater", "name": "Pragmatist", "content": rationale or recommendation},
        {"role": "judge", "name": "Judge", "content": recommendation},
    ]
    return state


def test_save_search_link_resume(memory_db) -> None:  # noqa: ARG001
    first = _decided(
        "Choose SQLite",
        "Use SQLite",
        "We chose SQLite last month because it is local.",
    )
    save_debate(first)
    second = initial_state("Pick a cache", "Ollama", "m", 2, 1)
    save_debate(second)
    hits = search_decisions("SQLite last month")
    assert hits[0]["debate_id"] == first["debate_id"]
    assert hits[0]["decision_id"] == first["debate_id"]
    assert hits[0]["status"] == "decided"
    assert hits[0]["confidence"] == 80
    assert hits[0]["arguments_for"] == ["Local file, no server"]
    assert hits[0]["arguments_against"] == ["Single file lock"]
    assert "Pragmatist" in hits[0]["agent_models"]
    decided = search_decisions(status="decided", min_confidence=50)
    assert len(decided) == 1
    link_decisions(str(first["debate_id"]), str(second["debate_id"]))
    assert second["debate_id"] in related_ids(str(first["debate_id"]))
    loaded = load_debate(str(first["debate_id"]))
    assert loaded["topic"] == "Choose SQLite"
    assert list_debates()
    with pytest.raises(KeyError, match="Unknown"):
        load_debate("missing")


def test_natural_language_search(memory_db) -> None:  # noqa: ARG001
    state = _decided(
        "Choose SQLite",
        "Use SQLite",
        "We chose SQLite last month because it is local.",
    )
    save_debate(state)
    hits = search_decisions("Why did we decide SQLite last month?")
    assert hits[0]["debate_id"] == state["debate_id"]


def test_notes_tags_archive_delete(memory_db) -> None:  # noqa: ARG001
    state = _decided("Choose SQLite", "Use SQLite")
    save_debate(state, tags=["infra"], category="database", notes="first pass")
    debate_id = str(state["debate_id"])
    update_decision_meta(debate_id, notes="keep me", tags=["infra", "sqlite"], category="storage")
    save_debate(state)
    row = search_decisions(tag="sqlite")[0]
    assert row["notes"] == "keep me"
    assert row["tags"] == ["infra", "sqlite"]
    assert row["category"] == "storage"
    assert "sqlite" in list_tags()
    assert "storage" in list_categories()
    archive_decision(debate_id)
    assert search_decisions() == []
    archived = search_decisions(status="archived")
    assert archived[0]["archived"] is True
    archive_decision(debate_id, archived=False)
    assert search_decisions()[0]["debate_id"] == debate_id
    delete_decision(debate_id)
    assert search_decisions(include_archived=True) == []
    with pytest.raises(KeyError, match="Unknown"):
        load_debate(debate_id)


def test_relevant_and_memory_block(memory_db) -> None:  # noqa: ARG001
    past = _decided("Choose SQLite", "Use SQLite")
    save_debate(past)
    current = initial_state("Choose SQLite for history", "Ollama", "m", 2, 1)
    hits = relevant_decisions("Choose SQLite", exclude_id=str(current["debate_id"]))
    assert hits[0]["debate_id"] == past["debate_id"]
    assert "Use SQLite" in memory_block(current)
    assert "Related past decisions" in knowledge_block(current)
    assert memory_block(past) == ""


def test_migrates_legacy_schema(memory_db) -> None:
    path = memory_db / "decisions.db"
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE decisions (
            debate_id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            phase TEXT,
            mode TEXT,
            status TEXT,
            recommendation TEXT,
            confidence INTEGER,
            outcome TEXT,
            winner TEXT,
            participants TEXT,
            key_arguments TEXT,
            rationale TEXT,
            state_json TEXT NOT NULL
        )
        """
    )
    payload = {
        "debate_id": "oldid",
        "topic": "Old topic",
        "transcript": [],
        "verdict": {"recommendation": "Keep it", "winner": "Skeptic"},
    }
    conn.execute(
        """
        INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            "oldid",
            "Old topic",
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
            "judge",
            "open",
            "decided",
            "Keep it",
            70,
            "clear_winner",
            "Skeptic",
            "[]",
            "[]",
            "because",
            json.dumps(payload),
        ),
    )
    conn.commit()
    conn.close()
    hits = search_decisions("why did we decide old")
    assert hits[0]["debate_id"] == "oldid"
    assert hits[0]["tags"] == []
    assert hits[0]["archived"] is False
    loaded = load_debate("oldid")
    assert loaded["topic"] == "Old topic"


def test_date_and_legacy_json(memory_db) -> None:
    state = _decided("Choose SQLite", "Use SQLite")
    save_debate(state)
    leftover = memory_db / "json"
    leftover.mkdir()
    extra = initial_state("Legacy file", "Ollama", "m", 2, 1)
    extra["debate_id"] = "legacyjson"
    (leftover / "legacyjson.json").write_text(json.dumps(extra), encoding="utf-8")
    loaded = load_debate("legacyjson")
    assert loaded["topic"] == "Legacy file"
    today = search_decisions(since="2099-01-01")
    assert today == []
    bounded = search_decisions(until="1970-01-01")
    assert bounded == []
    found = search_decisions(until="2099-01-01")
    assert found
