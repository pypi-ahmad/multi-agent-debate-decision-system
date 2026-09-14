# Copyright (c) 2026 Ahmad Mujtaba
"""SQLite decision memory. Full state is stored so a hearing can resume.

Each row keeps two things: individual columns (topic, recommendation, tags,
...) used for search/filtering, and a `state_json` blob holding the complete
DebateState verbatim, used only by load_debate() to resume a hearing. They
are NOT kept in sync automatically — see update_decision_meta(). Next module:
rag/pipeline.py, which indexes a decision's text into the vector store
separately from this table.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from debate_decision_system.config import PROJECT_ROOT
from debate_decision_system.state import DebateState

DB_PATH = PROJECT_ROOT / "data" / "decisions.db"
HISTORY_DIR = PROJECT_ROOT / "data" / "debates"

_STOP = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "about",
        "because",
        "did",
        "do",
        "does",
        "for",
        "from",
        "how",
        "in",
        "is",
        "last",
        "month",
        "of",
        "on",
        "or",
        "our",
        "should",
        "that",
        "the",
        "this",
        "to",
        "was",
        "we",
        "were",
        "what",
        "when",
        "why",
        "with",
        "decide",
        "decided",
        "choose",
        "chose",
        "chosen",
    }
)
_NEW_COLUMNS = {
    "agent_models": "TEXT",
    "arguments_for": "TEXT",
    "arguments_against": "TEXT",
    "transcript": "TEXT",
    "tags": "TEXT",
    "category": "TEXT",
    "notes": "TEXT",
    "archived": "INTEGER NOT NULL DEFAULT 0",
}


def save_debate(
    state: DebateState,
    *,
    notes: str | None = None,
    tags: list[str] | None = None,
    category: str | None = None,
) -> Path:
    debate_id = str(state.get("debate_id") or "untitled")
    now = datetime.now(UTC).isoformat(timespec="seconds")
    verdict = state.get("verdict") or {}
    arguments_for = list(verdict.get("strongest_arguments") or [])
    arguments_against = list(verdict.get("key_risks") or [])
    combined = [*arguments_for, *arguments_against]
    with _connect() as conn:
        prior = _existing_meta(conn, debate_id)
        conn.execute(
            """
            INSERT INTO decisions (
                debate_id, topic, created_at, updated_at, phase, mode, status,
                recommendation, confidence, outcome, winner, participants,
                agent_models, key_arguments, arguments_for, arguments_against,
                rationale, transcript, tags, category, notes, archived, state_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                agent_models=excluded.agent_models,
                key_arguments=excluded.key_arguments,
                arguments_for=excluded.arguments_for,
                arguments_against=excluded.arguments_against,
                rationale=excluded.rationale,
                transcript=excluded.transcript,
                tags=excluded.tags,
                category=excluded.category,
                notes=excluded.notes,
                archived=excluded.archived,
                state_json=excluded.state_json
            """,
            (
                debate_id,
                state.get("topic", ""),
                prior.get("created_at") or now,
                now,
                state.get("phase", ""),
                state.get("mode", "open"),
                _status(state),
                verdict.get("recommendation", ""),
                verdict.get("confidence"),
                verdict.get("outcome", ""),
                verdict.get("winner", ""),
                json.dumps(_participant_names(state)),
                json.dumps(_agent_models(state)),
                json.dumps(combined),
                json.dumps(arguments_for),
                json.dumps(arguments_against),
                verdict.get("rationale", ""),
                _flatten_transcript(state),
                json.dumps(tags if tags is not None else prior.get("tags") or []),
                category if category is not None else prior.get("category") or "",
                notes if notes is not None else prior.get("notes") or "",
                int(prior.get("archived") or 0),
                json.dumps(state),
            ),
        )
        row = conn.execute("SELECT * FROM decisions WHERE debate_id = ?", (debate_id,)).fetchone()
        if row is not None:
            _upsert_fts(conn, row)
    _index_decision_safe(state)
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
        state = cast(DebateState, json.loads(legacy.read_text(encoding="utf-8")))
        save_debate(state)
        return state
    msg = f"Unknown debate: {debate_id}"
    raise KeyError(msg)


def _index_decision_safe(state: DebateState) -> None:
    try:
        from debate_decision_system.rag.pipeline import index_decision  # noqa: PLC0415

        index_decision(state)
    except (OSError, ValueError, sqlite3.Error):
        return


def _drop_decision_vectors(debate_id: str) -> None:
    try:
        from debate_decision_system.rag.vectorstore import delete_source  # noqa: PLC0415

        delete_source("decision", debate_id)
    except (OSError, sqlite3.Error):
        return


def list_debates() -> list[dict[str, Any]]:
    return search_decisions()


def search_decisions(  # noqa: PLR0913
    query: str = "",
    *,
    outcome: str = "",
    status: str = "",
    since: str = "",
    until: str = "",
    tag: str = "",
    category: str = "",
    min_confidence: int | None = None,
    include_archived: bool = False,
) -> list[dict[str, Any]]:
    where, params = _filters(
        outcome=outcome,
        status=status,
        since=since,
        until=until,
        tag=tag,
        category=category,
        min_confidence=min_confidence,
        include_archived=include_archived,
    )
    ids = _fts_ids(query) if query.strip() else None
    if ids is not None:
        if not ids:
            return _like_search(query, where, params)
        placeholders = ",".join("?" * len(ids))
        sql = (
            f"SELECT * FROM decisions WHERE debate_id IN ({placeholders}) AND {where} "  # noqa: S608
            "ORDER BY updated_at DESC"
        )
        with _connect() as conn:
            rows = conn.execute(sql, [*ids, *params]).fetchall()
        if rows:
            return [_row_to_record(row) for row in rows]
        return _like_search(query, where, params)
    sql = f"SELECT * FROM decisions WHERE {where} ORDER BY updated_at DESC"  # noqa: S608
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_record(row) for row in rows]


def relevant_decisions(topic: str, *, exclude_id: str = "", limit: int = 3) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for row in search_decisions(topic, status="decided"):
        if row["debate_id"] == exclude_id:
            continue
        hits.append(row)
        if len(hits) >= limit:
            break
    return hits


def update_decision_meta(
    debate_id: str,
    *,
    notes: str | None = None,
    tags: list[str] | None = None,
    category: str | None = None,
) -> None:
    """Update only the notes/tags/category columns. This does not touch
    state_json, so load_debate() on this debate_id still returns the state as
    of the last save_debate() call, without these edits."""
    assignments: list[str] = []
    params: list[Any] = []
    if notes is not None:
        assignments.append("notes = ?")
        params.append(notes)
    if tags is not None:
        assignments.append("tags = ?")
        params.append(json.dumps(tags))
    if category is not None:
        assignments.append("category = ?")
        params.append(category)
    if not assignments:
        return
    assignments.append("updated_at = ?")
    params.append(datetime.now(UTC).isoformat(timespec="seconds"))
    params.append(debate_id)
    sql = f"UPDATE decisions SET {', '.join(assignments)} WHERE debate_id = ?"  # noqa: S608
    with _connect() as conn:
        conn.execute(sql, params)
        row = conn.execute("SELECT * FROM decisions WHERE debate_id = ?", (debate_id,)).fetchone()
        if row is not None:
            _upsert_fts(conn, row)


def archive_decision(debate_id: str, *, archived: bool = True) -> None:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            "UPDATE decisions SET archived = ?, updated_at = ? WHERE debate_id = ?",
            (1 if archived else 0, now, debate_id),
        )


def delete_decision(debate_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "DELETE FROM decision_links WHERE left_id = ? OR right_id = ?",
            (debate_id, debate_id),
        )
        if _fts_ready(conn):
            conn.execute("DELETE FROM decisions_fts WHERE debate_id = ?", (debate_id,))
        conn.execute("DELETE FROM decisions WHERE debate_id = ?", (debate_id,))
    _drop_decision_vectors(debate_id)


def list_tags() -> list[str]:
    found: set[str] = set()
    for row in search_decisions(include_archived=True):
        found.update(str(tag) for tag in (row.get("tags") or []) if str(tag).strip())
    return sorted(found)


def list_categories() -> list[str]:
    found: set[str] = set()
    for row in search_decisions(include_archived=True):
        value = str(row.get("category") or "").strip()
        if value:
            found.add(value)
    return sorted(found)


def link_decisions(left_id: str, right_id: str) -> None:
    """Links are undirected. Sorting the pair before insert just avoids storing
    both (A, B) and (B, A) as separate rows; related_ids() below still queries
    both columns, so lookups don't depend on this ordering."""
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
            agent_models TEXT,
            key_arguments TEXT,
            arguments_for TEXT,
            arguments_against TEXT,
            rationale TEXT,
            transcript TEXT,
            tags TEXT,
            category TEXT,
            notes TEXT,
            archived INTEGER NOT NULL DEFAULT 0,
            state_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS decision_links (
            left_id TEXT NOT NULL,
            right_id TEXT NOT NULL,
            PRIMARY KEY (left_id, right_id)
        );
        """
    )
    _migrate(conn)
    _ensure_fts(conn)
    _rebuild_fts_if_stale(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    have = {str(row[1]) for row in conn.execute("PRAGMA table_info(decisions)")}
    for name, decl in _NEW_COLUMNS.items():
        if name not in have:
            conn.execute(f"ALTER TABLE decisions ADD COLUMN {name} {decl}")


def _ensure_fts(conn: sqlite3.Connection) -> bool:
    # FTS5 is a compile-time SQLite extension and isn't guaranteed present in
    # every Python build; when CREATE VIRTUAL TABLE fails, every FTS-dependent
    # query below degrades to the plain LIKE search in _like_search().
    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
                debate_id UNINDEXED,
                topic,
                recommendation,
                rationale,
                arguments,
                notes,
                participants,
                tags,
                category,
                transcript
            )
            """
        )
    except sqlite3.OperationalError:
        return False
    return True


def _fts_ready(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = 'decisions_fts'"
    ).fetchone()
    return row is not None


def _rebuild_fts_if_stale(conn: sqlite3.Connection) -> None:
    """Cheap staleness check: only compares row counts, not content. A matching
    count is treated as "in sync" even if a row's text changed without the FTS
    mirror being updated some other way; a full rebuild is the recovery path
    whenever counts disagree (e.g. after a migration or manual DB edit)."""
    if not _fts_ready(conn):
        return
    stored = int(conn.execute("SELECT COUNT(*) FROM decisions_fts").fetchone()[0])
    total = int(conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0])
    if stored == total:
        return
    conn.execute("DELETE FROM decisions_fts")
    for row in conn.execute("SELECT * FROM decisions"):
        _upsert_fts(conn, row)


def _upsert_fts(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    if not _fts_ready(conn):
        return
    debate_id = str(row["debate_id"])
    conn.execute("DELETE FROM decisions_fts WHERE debate_id = ?", (debate_id,))
    arguments = " ".join(
        [
            str(row["key_arguments"] or ""),
            str(_col(row, "arguments_for") or ""),
            str(_col(row, "arguments_against") or ""),
        ]
    )
    conn.execute(
        """
        INSERT INTO decisions_fts (
            debate_id, topic, recommendation, rationale, arguments, notes,
            participants, tags, category, transcript
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            debate_id,
            row["topic"] or "",
            row["recommendation"] or "",
            row["rationale"] or "",
            arguments,
            _col(row, "notes") or "",
            row["participants"] or "",
            _col(row, "tags") or "",
            _col(row, "category") or "",
            _col(row, "transcript") or "",
        ),
    )


def _fts_ids(query: str) -> list[str] | None:
    terms = _search_terms(query)
    if not terms:
        return None
    and_ids = _fts_match(" AND ".join(f'"{term}"' for term in terms))
    if and_ids:
        return and_ids
    if len(terms) > 1:
        or_ids = _fts_match(" OR ".join(f'"{term}"' for term in terms))
        if or_ids is not None:
            return or_ids
    return and_ids


def _fts_match(match: str) -> list[str] | None:
    try:
        with _connect() as conn:
            if not _fts_ready(conn):
                return None
            rows = conn.execute(
                "SELECT debate_id FROM decisions_fts WHERE decisions_fts MATCH ?",
                (match,),
            ).fetchall()
    except sqlite3.OperationalError:
        return None
    return [str(row["debate_id"]) for row in rows]


def _like_search(query: str, where: str, params: list[Any]) -> list[dict[str, Any]]:
    needle = f"%{query.strip()}%"
    sql = (
        f"SELECT * FROM decisions WHERE {where} AND ("  # noqa: S608
        "topic LIKE ? OR recommendation LIKE ? OR key_arguments LIKE ? "
        "OR rationale LIKE ? OR participants LIKE ? OR IFNULL(notes, '') LIKE ? "
        "OR IFNULL(tags, '') LIKE ? OR IFNULL(category, '') LIKE ? "
        "OR IFNULL(transcript, '') LIKE ? OR IFNULL(arguments_for, '') LIKE ? "
        "OR IFNULL(arguments_against, '') LIKE ?) ORDER BY updated_at DESC"
    )
    like = [needle] * 11
    with _connect() as conn:
        rows = conn.execute(sql, [*params, *like]).fetchall()
    return [_row_to_record(row) for row in rows]


def _filters(  # noqa: PLR0913
    *,
    outcome: str,
    status: str,
    since: str,
    until: str,
    tag: str,
    category: str,
    min_confidence: int | None,
    include_archived: bool,
) -> tuple[str, list[Any]]:
    clauses = ["1=1"]
    params: list[Any] = []
    if status == "archived":
        clauses.append("COALESCE(archived, 0) = 1")
    else:
        if not include_archived:
            clauses.append("COALESCE(archived, 0) = 0")
        if status:
            clauses.append("status = ?")
            params.append(status)
    if outcome:
        clauses.append("outcome = ?")
        params.append(outcome)
    if since:
        clauses.append("created_at >= ?")
        params.append(since)
    if until:
        clauses.append("created_at < ?")
        params.append(_until_bound(until))
    if tag:
        clauses.append("IFNULL(tags, '') LIKE ?")
        params.append(f"%{tag.strip()}%")
    if category:
        clauses.append("IFNULL(category, '') = ?")
        params.append(category)
    if min_confidence is not None:
        clauses.append("confidence >= ?")
        params.append(min_confidence)
    return " AND ".join(clauses), params


def _until_bound(until: str) -> str:
    """`created_at < until_bound` is the actual filter (see _filters), so a
    bare date is pushed to the start of the next day here — making a
    caller-supplied "until 2026-03-05" inclusive of the 5th, not exclusive of
    it. A value that already carries a time component is used as-is (exclusive
    at that exact instant)."""
    raw = until.strip()
    if "T" in raw or " " in raw:
        return raw
    try:
        day = datetime.fromisoformat(raw).date()
    except ValueError:
        return raw
    return (day + timedelta(days=1)).isoformat()


def _search_terms(query: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", query.lower())
    kept = [token for token in tokens if token not in _STOP and len(token) > 1]
    # If stopword/length filtering removes everything (e.g. query == "the a"),
    # search on the raw tokens instead of matching nothing.
    return kept or tokens


def _status(state: DebateState) -> str:
    verdict = state.get("verdict") or {}
    if verdict.get("recommendation") or verdict.get("winner"):
        return "decided"
    turns = state.get("transcript") or []
    if turns and turns[-1].get("role") == "judge":
        return "decided"
    return "in_progress"


def _participant_names(state: DebateState) -> list[str]:
    return [str(spec.get("name", "")) for spec in state.get("debaters") or []]


def _agent_models(state: DebateState) -> dict[str, str]:
    models: dict[str, str] = {
        "Moderator": f"{state.get('moderator_provider') or state.get('provider')}/"
        f"{state.get('moderator_model') or state.get('model')}",
        "Judge": f"{state.get('judge_provider') or state.get('provider')}/"
        f"{state.get('judge_model') or state.get('model')}",
    }
    for spec in state.get("debaters") or []:
        name = str(spec.get("name") or "Seat")
        models[name] = f"{spec.get('provider') or state.get('provider')}/{spec.get('model') or ''}"
        for member in spec.get("members") or []:
            member_name = str(member.get("name") or "member")
            models[f"{name}/{member_name}"] = (
                f"{member.get('provider') or spec.get('provider')}/"
                f"{member.get('model') or spec.get('model') or ''}"
            )
    return models


def _flatten_transcript(state: DebateState) -> str:
    return "\n".join(
        f"{turn.get('name', '')}: {turn.get('content', '')}"
        for turn in state.get("transcript") or []
    )


def _existing_meta(conn: sqlite3.Connection, debate_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT created_at, notes, tags, category, archived FROM decisions WHERE debate_id = ?",
        (debate_id,),
    ).fetchone()
    if row is None:
        return {}
    return {
        "created_at": str(row["created_at"]),
        "notes": row["notes"] or "",
        "tags": _loads_list(row["tags"]),
        "category": row["category"] or "",
        "archived": int(row["archived"] or 0),
    }


def _as_bool(value: object) -> bool:
    if isinstance(value, (int, float, str)):
        return bool(int(value))
    return False


def _col(row: sqlite3.Row, name: str) -> object:
    try:
        return row[name]
    except (KeyError, IndexError):
        return None


def _loads_list(raw: object) -> list[Any]:
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        data = json.loads(str(raw))
    except json.JSONDecodeError:
        return [str(raw)]
    return data if isinstance(data, list) else []


def _loads_dict(raw: object) -> dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        data = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    debate_id = row["debate_id"]
    return {
        "decision_id": debate_id,
        "debate_id": debate_id,
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
        "participants": _loads_list(row["participants"]),
        "agent_models": _loads_dict(_col(row, "agent_models")),
        "key_arguments": _loads_list(row["key_arguments"]),
        "arguments_for": _loads_list(_col(row, "arguments_for")),
        "arguments_against": _loads_list(_col(row, "arguments_against")),
        "rationale": row["rationale"],
        "tags": _loads_list(_col(row, "tags")),
        "category": _col(row, "category") or "",
        "notes": _col(row, "notes") or "",
        "archived": _as_bool(_col(row, "archived")),
    }
