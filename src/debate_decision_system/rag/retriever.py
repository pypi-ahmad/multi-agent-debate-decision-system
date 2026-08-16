# Copyright (c) 2026 Ahmad Mujtaba
"""Query rewrite, BM25, and hybrid (dense + sparse) fusion."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import replace

from debate_decision_system.rag.vectorstore import Chunk, all_chunks, dense_search

_STOP = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "for",
        "from",
        "how",
        "in",
        "is",
        "of",
        "on",
        "or",
        "the",
        "to",
        "what",
        "why",
        "with",
    }
)


def tokens(text: str) -> list[str]:
    return [part for part in re.findall(r"[a-z0-9]+", text.lower()) if part not in _STOP]


def rewrite_query(query: str, *, topic: str = "") -> str:
    """Expand the query with topic terms. No LLM required."""
    parts = tokens(query)
    extra = [term for term in tokens(topic) if term not in parts]
    merged = [*parts, *extra[:8]]
    return " ".join(merged) if merged else query.strip()


def bm25_search(
    query: str,
    chunks: list[Chunk],
    *,
    limit: int = 12,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[Chunk]:
    query_terms = tokens(query)
    if not query_terms or not chunks:
        return []
    docs = [tokens(chunk.text) for chunk in chunks]
    avg_len = sum(len(doc) for doc in docs) / len(docs)
    df: Counter[str] = Counter()
    for doc in docs:
        df.update(set(doc))
    n = len(docs)
    scored: list[Chunk] = []
    for chunk, doc in zip(chunks, docs, strict=True):
        tf = Counter(doc)
        score = 0.0
        length = len(doc) or 1
        for term in query_terms:
            if tf[term] == 0:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            denom = tf[term] + k1 * (1 - b + b * length / avg_len)
            score += idf * (tf[term] * (k1 + 1) / denom)
        if score > 0:
            scored.append(replace(chunk, score=score))
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit]


def rrf_fuse(*rankings: list[Chunk], k: int = 60, limit: int = 16) -> list[Chunk]:
    """Reciprocal rank fusion across dense and sparse lists."""
    scores: dict[str, float] = {}
    by_id: dict[str, Chunk] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, start=1):
            by_id[chunk.id] = chunk
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
    ordered = sorted(scores, key=lambda key: scores[key], reverse=True)
    return [replace(by_id[item], score=scores[item]) for item in ordered[:limit]]


def hybrid_search(  # noqa: PLR0913
    query: str,
    *,
    limit: int = 16,
    source_types: tuple[str, ...] | None = None,
    collection: str | None = None,
    decision_id: str | None = None,
    tags: str | None = None,
    since: str | None = None,
) -> list[Chunk]:
    pool = all_chunks(
        source_types=source_types,
        collection=collection,
        decision_id=decision_id,
        tags=tags,
        since=since,
    )
    dense = dense_search(
        query,
        limit=limit,
        source_types=source_types,
        collection=collection,
        decision_id=decision_id,
        tags=tags,
        since=since,
    )
    sparse = bm25_search(query, pool, limit=limit)
    return rrf_fuse(dense, sparse, limit=limit)
