# Copyright (c) 2026 Ahmad Mujtaba
from __future__ import annotations

import io
import zipfile

import pytest

from debate_decision_system.documents import load_upload
from debate_decision_system.graph import initial_state, next_action
from debate_decision_system.tools import (
    ToolCall,
    ToolPlan,
    allowed_tools,
    calculator,
    run_code,
    run_tool_calls,
    tools_node,
)


def test_calculator_and_safe_code() -> None:
    assert calculator("2 + 3 * 4") == "14.0"
    assert run_code("round(sqrt(16) + 1)") == "5"
    with pytest.raises(ValueError, match="only"):
        calculator("__import__('os')")
    with pytest.raises(ValueError, match="only"):
        run_code("os.system('x')")


def test_grounded_blocks_web() -> None:
    assert "web_search" not in allowed_tools("grounded")
    assert "docs" in allowed_tools("grounded")
    assert "wikipedia" in allowed_tools("open")
    state = initial_state("Q", "Ollama", "m", 2, 1, grounding="grounded")
    turns, errors = run_tool_calls(state, [ToolCall(name="web_search", input="x")])
    assert turns == []
    assert errors
    assert "blocked" in errors[0]


def test_docs_tool_and_zip_loader() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("notes/spec.md", "The latency budget is 200ms.")
    docs = load_upload("pack.zip", buf.getvalue())
    assert docs[0]["name"] == "notes/spec.md"
    assert "200ms" in docs[0]["text"]
    state = initial_state("Q", "Ollama", "m", 2, 1, documents=docs, grounding="grounded")
    turns, errors = run_tool_calls(state, [ToolCall(name="docs", input="latency budget")])
    assert not errors
    assert "200ms" in turns[0]["content"]
    assert turns[0]["role"] == "tool"


def test_tools_node_sets_awaiting_speech(monkeypatch) -> None:
    state = initial_state("Q", "Ollama", "m", 2, 1)

    class _Plan:
        def with_structured_output(self, _cls):
            return self

        def invoke(self, _messages):
            return ToolPlan(tools=[ToolCall(name="calculator", input="1+1")])

    monkeypatch.setattr("debate_decision_system.tools.get_chat_model", lambda *_a, **_k: _Plan())
    out = tools_node(state)
    assert out["awaiting_speech"] is True
    assert out["transcript"][0]["role"] == "tool"
    assert "2.0" in out["transcript"][0]["content"]
    mid = initial_state("Q", "Ollama", "m", 2, 1)
    mid["transcript"] = [{"role": "moderator", "name": "Moderator", "content": "go"}]
    assert next_action(mid) == "tools"
