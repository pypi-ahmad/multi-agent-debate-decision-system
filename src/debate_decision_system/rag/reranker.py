# Copyright (c) 2026 Ahmad Mujtaba
"""Second-stage rerank: query-document interaction features + optional LLM."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import replace

from debate_decision_system.rag.retriever import tokens
from debate_decision_system.rag.vectorstore import Chunk


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def rerank(query: str, chunks: list[Chunk], *, limit: int = 6) -> list[Chunk]:
    """Cross-score: phrase hit, term overlap, title match, existing fusion score."""
    query_terms = set(tokens(query))
    phrase = query.lower().strip()
    scored: list[Chunk] = []
    for chunk in chunks:
        text = chunk.text.lower()
        name = chunk.source_name.lower()
        chunk_terms = set(tokens(chunk.text))
        overlap = len(query_terms & chunk_terms) / (len(query_terms) or 1)
        phrase_hit = 1.0 if phrase and phrase in text else 0.0
        title_hit = 1.0 if any(term in name for term in query_terms) else 0.0
        score = 0.45 * overlap + 0.25 * phrase_hit + 0.15 * title_hit + 0.15 * float(chunk.score)
        scored.append(replace(chunk, score=score))
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit]


def llm_rerank(
    query: str,
    chunks: list[Chunk],
    *,
    rank_fn: Callable[[str, list[str]], list[int]] | None = None,
    limit: int = 6,
) -> list[Chunk]:
    """Optional LLM rerank. `rank_fn(query, texts) -> list[int]` of preferred indexes."""
    fallback = rerank(query, chunks, limit=limit)
    if not chunks or rank_fn is None:
        return fallback
    try:
        raw = rank_fn(query, [chunk.text for chunk in chunks])
    except (OSError, RuntimeError, ValueError, TypeError):
        return fallback
    picked: list[Chunk] = []
    seen: set[str] = set()
    for index in raw:
        if not isinstance(index, int) or not 0 <= index < len(chunks):
            continue
        chunk = chunks[index]
        if chunk.id in seen:
            continue
        seen.add(chunk.id)
        picked.append(chunk)
    leftover = [chunk for chunk in fallback if chunk.id not in seen]
    return [*picked, *leftover][:limit]


def compress(query: str, text: str, *, max_chars: int = 480) -> str:
    """Keep sentences that share query terms. Falls back to a prefix."""
    query_terms = set(tokens(query))
    kept: list[str] = []
    size = 0
    for sentence in _sentences(text):
        if query_terms and not (set(tokens(sentence)) & query_terms):
            continue
        if size + len(sentence) > max_chars:
            break
        kept.append(sentence)
        size += len(sentence) + 1
    if kept:
        return " ".join(kept)
    return text[:max_chars].strip()
