# Copyright (c) 2026 Ahmad Mujtaba
"""Keyword retrieval over uploaded documents. No vector store."""

from __future__ import annotations

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
    docs = list(state.get("documents") or [])
    if not docs:
        return ""
    turns = state.get("transcript") or []
    query = turns[-1]["content"] if turns else state.get("topic", "")
    hits = retrieve(docs, query)
    if not hits:
        names = ", ".join(doc.get("name", "doc") for doc in docs)
        return f"\n\nUploaded documents (no keyword hit): {names}"
    return f"\n\nRetrieved from uploaded docs:\n{hits}"
