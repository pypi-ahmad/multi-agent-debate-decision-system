# Copyright (c) 2026 Ahmad Mujtaba
"""Persistent LanceDB vector store. Incremental upsert by content hash."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import lancedb

from debate_decision_system.config import PROJECT_ROOT
from debate_decision_system.rag.embeddings import embed_text

STORE_PATH = PROJECT_ROOT / "data" / "lancedb"
_TABLE_PREFIX = "chunks_"


@dataclass(frozen=True)
class Chunk:
    id: str
    source_type: str
    source_id: str
    source_name: str
    collection: str
    chunk_index: int
    text: str
    content_hash: str
    tags: str
    created_at: str
    decision_id: str
    vector: list[float]
    score: float = 0.0


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _esc(value: str) -> str:
    return value.replace("'", "''")


def _db() -> Any:  # noqa: ANN401
    Path(STORE_PATH).mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(STORE_PATH))


def _table_names(db: Any) -> list[str]:  # noqa: ANN401
    listed = db.list_tables()
    tables = getattr(listed, "tables", listed)
    return [str(name) for name in tables]


def _open_tables(db: Any) -> list[Any]:  # noqa: ANN401
    return [db.open_table(name) for name in _table_names(db) if str(name).startswith(_TABLE_PREFIX)]


def _record_to_chunk(row: dict[str, Any], score: float = 0.0) -> Chunk:
    raw_vec = row.get("vector") or []
    vector = [float(x) for x in raw_vec]
    return Chunk(
        id=str(row["id"]),
        source_type=str(row.get("source_type") or ""),
        source_id=str(row.get("source_id") or ""),
        source_name=str(row.get("source_name") or ""),
        collection=str(row.get("collection") or ""),
        chunk_index=int(row.get("chunk_index") or 0),
        text=str(row.get("text") or ""),
        content_hash=str(row.get("content_hash") or ""),
        tags=str(row.get("tags") or ""),
        created_at=str(row.get("created_at") or ""),
        decision_id=str(row.get("decision_id") or ""),
        vector=vector,
        score=score,
    )


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "source_type": row["source_type"],
        "source_id": row["source_id"],
        "source_name": row["source_name"],
        "collection": row["collection"],
        "chunk_index": int(row["chunk_index"]),
        "text": row["text"],
        "content_hash": row["content_hash"],
        "tags": row.get("tags") or "",
        "created_at": row.get("created_at") or _now(),
        "decision_id": row.get("decision_id") or "",
        "dim": int(row["dim"]),
        "vector": [float(x) for x in row["vector"]],
    }


def _existing_hashes(table: Any) -> dict[str, str]:  # noqa: ANN401
    if table.count_rows() == 0:
        return {}
    rows = table.to_arrow().to_pylist()
    return {str(row["id"]): str(row.get("content_hash") or "") for row in rows}


def upsert_chunks(rows: list[dict[str, Any]]) -> int:
    """Insert or replace chunks whose content_hash changed. Returns upsert count."""
    if not rows:
        return 0
    by_dim: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_dim.setdefault(int(row["dim"]), []).append(_payload(row))
    changed = 0
    db = _db()
    names = _table_names(db)
    for dim, group in by_dim.items():
        name = f"{_TABLE_PREFIX}{dim}"
        if name not in names:
            db.create_table(name, group)
            changed += len(group)
            continue
        table = db.open_table(name)
        hashes = _existing_hashes(table)
        fresh: list[dict[str, Any]] = []
        for row in group:
            if hashes.get(row["id"]) == row["content_hash"]:
                continue
            if row["id"] in hashes:
                table.delete(f"id = '{_esc(row['id'])}'")
            fresh.append(row)
        if fresh:
            table.add(fresh)
            changed += len(fresh)
    return changed


def delete_source(source_type: str, source_id: str) -> None:
    clause = f"source_type = '{_esc(source_type)}' AND source_id = '{_esc(source_id)}'"
    db = _db()
    for table in _open_tables(db):
        table.delete(clause)


def _match(  # noqa: PLR0913
    chunk: Chunk,
    *,
    source_types: tuple[str, ...] | None,
    collection: str | None,
    decision_id: str | None,
    tags: str | None,
    since: str | None,
) -> bool:
    if source_types and chunk.source_type not in source_types:
        return False
    if collection and chunk.collection != collection:
        return False
    if decision_id and chunk.decision_id != decision_id:
        return False
    if tags and tags not in chunk.tags:
        return False
    return not (since and chunk.created_at < since)


def all_chunks(
    *,
    source_types: tuple[str, ...] | None = None,
    collection: str | None = None,
    decision_id: str | None = None,
    tags: str | None = None,
    since: str | None = None,
) -> list[Chunk]:
    found: list[Chunk] = []
    db = _db()
    for table in _open_tables(db):
        if table.count_rows() == 0:
            continue
        for row in table.to_arrow().to_pylist():
            chunk = _record_to_chunk(row)
            if _match(
                chunk,
                source_types=source_types,
                collection=collection,
                decision_id=decision_id,
                tags=tags,
                since=since,
            ):
                found.append(chunk)
    return found


def dense_search(  # noqa: PLR0913
    query: str,
    *,
    limit: int = 12,
    source_types: tuple[str, ...] | None = None,
    collection: str | None = None,
    decision_id: str | None = None,
    tags: str | None = None,
    since: str | None = None,
) -> list[Chunk]:
    query_vec, _backend = embed_text(query)
    dim = len(query_vec)
    db = _db()
    name = f"{_TABLE_PREFIX}{dim}"
    if name not in _table_names(db):
        return []
    table = db.open_table(name)
    if table.count_rows() == 0:
        return []
    raw = table.search(query_vec).limit(max(limit * 4, 16)).to_list()
    scored: list[Chunk] = []
    for row in raw:
        distance = float(row.get("_distance") or 0.0)
        chunk = _record_to_chunk(row, score=1.0 / (1.0 + distance))
        if _match(
            chunk,
            source_types=source_types,
            collection=collection,
            decision_id=decision_id,
            tags=tags,
            since=since,
        ):
            scored.append(chunk)
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit]


def stats() -> dict[str, Any]:
    chunks = all_chunks()
    sources = {chunk.source_id for chunk in chunks}
    types: dict[str, int] = {}
    latest = ""
    for chunk in chunks:
        types[chunk.source_type] = types.get(chunk.source_type, 0) + 1
        latest = max(latest, chunk.created_at)
    return {
        "chunks": len(chunks),
        "sources": len(sources),
        "last_updated": latest,
        "by_type": types,
        "path": str(STORE_PATH),
        "engine": "lancedb",
    }
