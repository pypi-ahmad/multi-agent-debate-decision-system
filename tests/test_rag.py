# Copyright (c) 2026 Ahmad Mujtaba
from __future__ import annotations

from debate_decision_system.graph import initial_state
from debate_decision_system.memory import delete_decision, link_decisions, save_debate
from debate_decision_system.rag.embeddings import hashed_embed
from debate_decision_system.rag.pipeline import index_decision, index_documents, run_rag
from debate_decision_system.rag.reranker import llm_rerank
from debate_decision_system.rag.vectorstore import Chunk
from debate_decision_system.rag.vectorstore import stats as store_stats
from debate_decision_system.retrieve import knowledge_block, retrieve


def test_hashed_embed_is_deterministic_and_normalized() -> None:
    a = hashed_embed("sqlite local file")
    b = hashed_embed("sqlite local file")
    assert a == b
    assert len(a) == 256
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6


def test_index_and_hybrid_search_returns_citations(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("debate_decision_system.rag.vectorstore.STORE_PATH", tmp_path / "lancedb")
    index_documents(
        [{"name": "notes.md", "text": "Prefer SQLite for single-user history. No server."}],
        collection="longterm",
    )
    result = run_rag("Why SQLite for history?", documents=[])
    assert result.hits
    hit = result.hits[0]
    assert "SQLite" in hit.text
    assert hit.citation.startswith("[source:")
    assert "notes.md" in hit.citation
    assert result.rewritten_query
    assert store_stats()["engine"] == "lancedb"


def test_llm_rerank_uses_rank_fn() -> None:
    chunks = [
        Chunk("a", "document", "a", "a", "longterm", 0, "alpha", "h", "", "", "", [0.0], 0.1),
        Chunk("b", "document", "b", "b", "longterm", 0, "beta", "h", "", "", "", [0.0], 0.9),
    ]
    ranked = llm_rerank("q", chunks, rank_fn=lambda _q, _t: [0], limit=1)
    assert ranked[0].id == "a"


def test_incremental_index_skips_unchanged_text(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("debate_decision_system.rag.vectorstore.STORE_PATH", tmp_path / "lancedb")
    docs = [{"name": "a.md", "text": "alpha beta gamma " * 20}]
    first = index_documents(docs, collection="longterm")
    second = index_documents(docs, collection="longterm")
    assert first.upserted >= 1
    assert second.upserted == 0
    assert store_stats()["chunks"] == first.upserted


def test_metadata_filter_and_pin(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("debate_decision_system.rag.vectorstore.STORE_PATH", tmp_path / "lancedb")
    monkeypatch.setattr("debate_decision_system.memory.DB_PATH", tmp_path / "decisions.db")
    past = initial_state("Ship local mode", "Ollama", "m", 2, 1)
    past["verdict"] = {
        "recommendation": "Ship local-only first",
        "rationale": "Users need a no-key path.",
        "strongest_arguments": ["Ollama works offline"],
        "key_risks": ["Hosted users wait"],
        "outcome": "clear_winner",
        "winner": "Pragmatist",
        "confidence": 70,
    }
    save_debate(past)
    index_decision(past)
    index_documents([{"name": "other.md", "text": "Unrelated gardening notes about roses."}])
    filtered = run_rag(
        "Ship local",
        documents=[],
        source_types=("decision",),
    )
    assert filtered.hits
    assert all(h.source_type == "decision" for h in filtered.hits)
    pinned = run_rag(
        "roses",
        documents=[],
        pinned_ids=[str(past["debate_id"])],
    )
    assert any(h.source_id == past["debate_id"] for h in pinned.hits)


def test_knowledge_block_uses_rag_citations(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("debate_decision_system.rag.vectorstore.STORE_PATH", tmp_path / "lancedb")
    monkeypatch.setattr("debate_decision_system.memory.DB_PATH", tmp_path / "decisions.db")
    docs = [{"name": "spec.md", "text": "Grounded speeches must cite [spec.md] for budget."}]
    state = initial_state("What is the budget rule?", "Ollama", "m", 2, 1, documents=docs)
    block = knowledge_block(state)
    assert "[source:" in block
    assert "spec.md" in block
    state["rag_enabled"] = False
    off = knowledge_block(state)
    assert "Retrieved from uploaded docs" in off or "spec.md" in retrieve(docs, "budget")


def test_delete_decision_drops_vectors(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("debate_decision_system.rag.vectorstore.STORE_PATH", tmp_path / "lancedb")
    monkeypatch.setattr("debate_decision_system.memory.DB_PATH", tmp_path / "decisions.db")
    state = initial_state("Delete me", "Ollama", "m", 2, 1)
    state["verdict"] = {"recommendation": "Gone", "outcome": "split", "confidence": 10}
    save_debate(state)
    index_decision(state)
    assert store_stats()["chunks"] >= 1
    delete_decision(str(state["debate_id"]))
    assert store_stats()["chunks"] == 0


def test_multihop_follows_linked_decision(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("debate_decision_system.rag.vectorstore.STORE_PATH", tmp_path / "lancedb")
    monkeypatch.setattr("debate_decision_system.memory.DB_PATH", tmp_path / "decisions.db")
    first = initial_state("Pick storage", "Ollama", "m", 2, 1)
    first["verdict"] = {
        "recommendation": "Use SQLite",
        "rationale": "Single file.",
        "outcome": "clear_winner",
        "winner": "Pragmatist",
        "confidence": 80,
    }
    second = initial_state("Pick backup", "Ollama", "m", 2, 1)
    second["verdict"] = {
        "recommendation": "Copy the db file nightly",
        "rationale": "Follows the SQLite choice.",
        "outcome": "clear_winner",
        "winner": "Operator",
        "confidence": 75,
    }
    save_debate(first)
    save_debate(second)
    index_decision(first)
    index_decision(second)
    link_decisions(str(first["debate_id"]), str(second["debate_id"]))
    result = run_rag("Pick storage", documents=[], hops=1)
    ids = {h.source_id for h in result.hits}
    assert first["debate_id"] in ids
    assert second["debate_id"] in ids
