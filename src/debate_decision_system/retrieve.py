# Copyright (c) 2026 Ahmad Mujtaba
"""Retrieval facade: keyword fallback plus advanced RAG."""

from __future__ import annotations

from debate_decision_system.memory import relevant_decisions
from debate_decision_system.rag.pipeline import context_for_state
from debate_decision_system.state import DebateState, Document


def retrieve(documents: list[Document], query: str, limit: int = 3) -> str:
    terms = {part.lower() for part in query.split() if len(part) > 2}  # noqa: PLR2004
    if not documents:
        return ""
    ranked: list[tuple[int, Document, str]] = []
    for doc in documents:
        text = doc.get("text", "")
        score = 0
        snippet = text[:400]
        lower = text.lower()
        for term in terms:
            score += lower.count(term)
            idx = lower.find(term)
            if idx >= 0:
                start = max(0, idx - 80)
                snippet = text[start : start + 280]
        ranked.append((score, doc, snippet))
    ranked.sort(key=lambda item: item[0], reverse=True)
    chunks: list[str] = []
    for score, doc, snippet in ranked[:limit]:
        if score <= 0 and chunks:
            continue
        chunks.append(f"[{doc.get('name', 'doc')}] {snippet.strip()}")
    return "\n\n".join(chunks)


def knowledge_block(state: DebateState) -> str:
    parts: list[str] = []
    docs = list(state.get("documents") or [])
    rag_on = state.get("rag_enabled", True)
    if rag_on:
        result = context_for_state(state)
        if result.block:
            parts.append(result.block)
        elif state.get("grounding") == "grounded":
            parts.append("No retrieved context. In grounded mode, say you lack evidence.")
    elif docs:
        turns = state.get("transcript") or []
        query = turns[-1]["content"] if turns else state.get("topic", "")
        hits = retrieve(docs, query)
        if hits:
            parts.append(f"Retrieved from uploaded docs:\n{hits}")
        else:
            names = ", ".join(doc.get("name", "doc") for doc in docs)
            parts.append(f"Uploaded documents (no keyword hit): {names}")
    memory = memory_block(state)
    if memory:
        parts.append(memory)
    if not parts:
        return ""
    return "\n\n" + "\n\n".join(parts)


def memory_block(state: DebateState) -> str:
    try:
        hits = relevant_decisions(
            str(state.get("topic") or ""),
            exclude_id=str(state.get("debate_id") or ""),
        )
    except Exception:  # noqa: BLE001
        return ""
    if not hits:
        return ""
    lines = [
        (
            f"- [{str(row.get('created_at') or '')[:10]}] {row.get('topic', '')}: "
            f"{row.get('recommendation') or '(no recommendation yet)'}"
        )
        for row in hits
    ]
    return "Related past decisions:\n" + "\n".join(lines)
