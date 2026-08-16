# Copyright (c) 2026 Ahmad Mujtaba
"""Multi-stage RAG: rewrite → hybrid → rerank → compress → cite. Index helpers."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from debate_decision_system.rag.embeddings import embed_text
from debate_decision_system.rag.reranker import compress, llm_rerank, rerank
from debate_decision_system.rag.retriever import hybrid_search, rewrite_query
from debate_decision_system.rag.vectorstore import Chunk, upsert_chunks
from debate_decision_system.state import DebateState, Document

CHUNK_SIZE = 700
CHUNK_OVERLAP = 100


@dataclass(frozen=True)
class RagHit:
    text: str
    source_type: str
    source_id: str
    source_name: str
    chunk_index: int
    collection: str
    score: float
    citation: str


@dataclass(frozen=True)
class RagResult:
    query: str
    rewritten_query: str
    hits: list[RagHit]
    block: str


@dataclass(frozen=True)
class IndexReport:
    upserted: int
    sources: int


def citation_for(chunk: Chunk) -> str:
    return f"[source: {chunk.source_type}:{chunk.source_name}#{chunk.chunk_index}]"


def _hash_text(text: str) -> str:
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()


def _split_chunks(text: str) -> list[str]:
    clean = re.sub(r"\n{3,}", "\n\n", text.strip())
    if len(clean) <= CHUNK_SIZE:
        return [clean] if clean else []
    pieces: list[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + CHUNK_SIZE)
        if end < len(clean):
            cut = clean.rfind("\n", start + CHUNK_SIZE // 2, end)
            if cut > start:
                end = cut
        piece = clean[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(clean):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return pieces


def _chunk_rows(  # noqa: PLR0913
    *,
    source_type: str,
    source_id: str,
    source_name: str,
    text: str,
    collection: str,
    decision_id: str = "",
    tags: str = "",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, piece in enumerate(_split_chunks(text)):
        vector, _backend = embed_text(piece)
        rows.append(
            {
                "id": f"{source_type}:{source_id}:{index}",
                "source_type": source_type,
                "source_id": source_id,
                "source_name": source_name,
                "collection": collection,
                "chunk_index": index,
                "text": piece,
                "content_hash": _hash_text(piece),
                "tags": tags,
                "decision_id": decision_id,
                "dim": len(vector),
                "vector": vector,
            }
        )
    return rows


def index_documents(
    documents: list[Document],
    *,
    collection: str = "longterm",
    source_type: str = "document",
) -> IndexReport:
    rows: list[dict[str, Any]] = []
    names: set[str] = set()
    for doc in documents:
        name = str(doc.get("name") or "doc")
        text = str(doc.get("text") or "")
        names.add(name)
        rows.extend(
            _chunk_rows(
                source_type=source_type,
                source_id=name,
                source_name=name,
                text=text,
                collection=collection,
            )
        )
    return IndexReport(upserted=upsert_chunks(rows), sources=len(names))


def index_decision(state: DebateState) -> IndexReport:
    debate_id = str(state.get("debate_id") or "")
    if not debate_id:
        return IndexReport(upserted=0, sources=0)
    verdict = state.get("verdict") or {}
    parts = [
        f"Topic: {state.get('topic', '')}",
        f"Recommendation: {verdict.get('recommendation', '')}",
        f"Rationale: {verdict.get('rationale', '')}",
        "Arguments: " + "; ".join(verdict.get("strongest_arguments") or []),
        "Risks: " + "; ".join(verdict.get("key_risks") or []),
    ]
    tags = ""
    text = "\n".join(part for part in parts if not part.endswith(": "))
    rows = _chunk_rows(
        source_type="decision",
        source_id=debate_id,
        source_name=str(state.get("topic") or debate_id),
        text=text,
        collection="longterm",
        decision_id=debate_id,
        tags=tags,
    )
    return IndexReport(upserted=upsert_chunks(rows), sources=1)


def _to_hit(chunk: Chunk, query: str) -> RagHit:
    snippet = compress(query, chunk.text)
    return RagHit(
        text=snippet,
        source_type=chunk.source_type,
        source_id=chunk.source_id,
        source_name=chunk.source_name,
        chunk_index=chunk.chunk_index,
        collection=chunk.collection,
        score=chunk.score,
        citation=citation_for(replace(chunk, text=snippet)),
    )


def _format_block(hits: list[RagHit]) -> str:
    if not hits:
        return ""
    lines = ["Retrieved context (cite the [source:…] tags):"]
    lines.extend(f"- {hit.citation} {hit.text}" for hit in hits)
    return "\n".join(lines)


def run_rag(  # noqa: PLR0913
    query: str,
    *,
    documents: list[Document] | None = None,
    topic: str = "",
    pinned_ids: list[str] | None = None,
    source_types: tuple[str, ...] | None = None,
    collection: str | None = None,
    tags: str | None = None,
    since: str | None = None,
    hops: int = 1,
    limit: int = 6,
    rank_fn: Callable[[str, list[str]], list[int]] | None = None,
) -> RagResult:
    if documents:
        index_documents(documents, collection="session")
    rewritten = rewrite_query(query, topic=topic)
    fused = hybrid_search(
        rewritten or query,
        limit=max(limit * 2, 12),
        source_types=source_types,
        collection=collection,
        tags=tags,
        since=since,
    )
    if pinned_ids:
        for pin in pinned_ids:
            extra = hybrid_search(rewritten or query, limit=4, decision_id=pin)
            fused = extra + fused
    ranked = rerank(rewritten or query, fused, limit=limit)
    if rank_fn is not None:
        ranked = llm_rerank(rewritten or query, ranked, rank_fn=rank_fn, limit=limit)
    if hops and ranked:
        ranked = _multihop(rewritten or query, ranked, hops=hops, limit=limit)
    hits = [_to_hit(chunk, rewritten or query) for chunk in ranked]
    return RagResult(
        query=query,
        rewritten_query=rewritten,
        hits=hits,
        block=_format_block(hits),
    )


def _multihop(query: str, seed: list[Chunk], *, hops: int, limit: int) -> list[Chunk]:
    from debate_decision_system.memory import related_ids  # noqa: PLC0415

    seen = {chunk.id for chunk in seed}
    extra: list[Chunk] = list(seed)
    decision_ids = {chunk.source_id for chunk in seed if chunk.source_type == "decision"}
    for _ in range(hops):
        hop_ids: list[str] = []
        for debate_id in decision_ids:
            hop_ids.extend(related_ids(debate_id))
        hop_ids = [item for item in hop_ids if item]
        if not hop_ids:
            break
        more: list[Chunk] = []
        for debate_id in hop_ids:
            more.extend(hybrid_search(query, limit=4, decision_id=debate_id))
        decision_ids = {chunk.source_id for chunk in more if chunk.source_type == "decision"}
        for chunk in more:
            if chunk.id not in seen:
                seen.add(chunk.id)
                extra.append(chunk)
    return rerank(query, extra, limit=limit)


def context_for_state(state: DebateState) -> RagResult:
    turns = state.get("transcript") or []
    query = turns[-1]["content"] if turns else str(state.get("topic") or "")
    return run_rag(
        query,
        documents=list(state.get("documents") or []),
        topic=str(state.get("topic") or ""),
        pinned_ids=list(state.get("pinned_ids") or []),
        hops=1,
    )
