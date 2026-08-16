# Copyright (c) 2026 Ahmad Mujtaba
"""SQLite decision memory. Full state is stored so a hearing can resume."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from debate_decision_system.config import PROJECT_ROOT
from debate_decision_system.graph import debate_done
from debate_decision_system.state import DebateState

DB_PATH = PROJECT_ROOT / "data" / "decisions.db"
HISTORY_DIR = PROJECT_ROOT / "data" / "debates"


def save_debate(state: DebateState) -> Path:
    debate_id = str(state.get("debate_id") or "untitled")
    now = datetime.now(UTC).isoformat(timespec="seconds")
    verdict = state.get("verdict") or {}
    participants = [spec.get("name", "") for spec in state.get("debaters") or []]
    arguments = list(verdict.get("strongest_arguments") or [])
    with _connect() as conn:
        created = _created_at(conn, debate_id) or now
        conn.execute(
            """
            INSERT INTO decisions (
                debate_id, topic, created_at, updated_at, phase, mode, status,
                recommendation, confidence, outcome, winner, participants,
                key_arguments, rationale, state_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(debate_id) DO UPDATE SET
                topic=excluded.topic,
                updated_at=excluded.updated_at,
                phase=excluded.phase,
                mode=excluded.mode,
                status=excluded.status,
                recommendation=excluded.recommendation,
                confidence=excluded.confidence,
                outcome=excluded.outcome,
                winner=excluded.winner,
                participants=excluded.participants,
                key_arguments=excluded.key_arguments,
                rationale=excluded.rationale,
                state_json=excluded.state_json
            """,
            (
                debate_id,
                state.get("topic", ""),
                created,
                now,
                state.get("phase", ""),
                state.get("mode", "open"),
                "decided" if debate_done(state) else "in_progress",
                verdict.get("recommendation", ""),
                verdict.get("confidence"),
                verdict.get("outcome", ""),
                verdict.get("winner", ""),
                json.dumps(participants),
                json.dumps(arguments),
                verdict.get("rationale", ""),
                json.dumps(state),
            ),
        )
    return DB_PATH


def load_debate(debate_id: str) -> DebateState:
    with _connect() as conn:
        row = conn.execute(
            "SELECT state_json FROM decisions WHERE debate_id = ?", (debate_id,)
        ).fetchone()
    if row is not None:
        return cast(DebateState, json.loads(row["state_json"]))
    legacy = HISTORY_DIR / f"{debate_id}.json"
    if legacy.exists():
        payload = json.loads(legacy.read_text(encoding="utf-8"))
        state = cast(DebateState, payload)
        save_debate(state)
        return state
    msg = f"Unknown debate: {debate_id}"
    raise KeyError(msg)


def list_debates() -> list[dict[str, Any]]:
    return search_decisions()


def search_decisions(
    query: str = "",
    *,
    outcome: str = "",
    status: str = "",
    since: str = "",
    min_confidence: int | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM decisions WHERE 1=1"
    params: list[Any] = []
    if query.strip():
        needle = f"%{query.strip()}%"
        sql += (
            " AND (topic LIKE ? OR recommendation LIKE ? OR key_arguments LIKE ?"
            " OR rationale LIKE ? OR participants LIKE ?)"
        )
        params.extend([needle, needle, needle, needle, needle])
    if outcome:
        sql += " AND outcome = ?"
        params.append(outcome)
    if status:
        sql += " AND status = ?"
        params.append(status)
    if since:
        sql += " AND created_at >= ?"
        params.append(since)
    if min_confidence is not None:
        sql += " AND confidence >= ?"
        params.append(min_confidence)
    sql += " ORDER BY updated_at DESC"
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_record(row) for row in rows]


def link_decisions(left_id: str, right_id: str) -> None:
    if left_id == right_id:
        return
    a, b = sorted((left_id, right_id))
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO decision_links (left_id, right_id) VALUES (?, ?)",
            (a, b),
        )


def related_ids(debate_id: str) -> list[str]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT right_id FROM decision_links WHERE left_id = ?
            UNION
            SELECT left_id FROM decision_links WHERE right_id = ?
            """,
            (debate_id, debate_id),
        ).fetchall()
    return [str(row[0]) for row in rows]


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _init(conn)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _init(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS decisions (
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
        );
        CREATE TABLE IF NOT EXISTS decision_links (
            left_id TEXT NOT NULL,
            right_id TEXT NOT NULL,
            PRIMARY KEY (left_id, right_id)
        );
        """
    )


def _created_at(conn: sqlite3.Connection, debate_id: str) -> str | None:
    row = conn.execute(
        "SELECT created_at FROM decisions WHERE debate_id = ?", (debate_id,)
    ).fetchone()
    return None if row is None else str(row["created_at"])


def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "debate_id": row["debate_id"],
        "topic": row["topic"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "phase": row["phase"],
        "mode": row["mode"],
        "status": row["status"],
        "recommendation": row["recommendation"],
        "confidence": row["confidence"],
        "outcome": row["outcome"],
        "winner": row["winner"],
        "participants": json.loads(row["participants"] or "[]"),
        "key_arguments": json.loads(row["key_arguments"] or "[]"),
        "rationale": row["rationale"],
    }
