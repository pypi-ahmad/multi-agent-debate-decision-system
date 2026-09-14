# Copyright (c) 2026 Ahmad Mujtaba
"""Debate tools: calculator, restricted code, Wikipedia, web search, docs."""

from __future__ import annotations

import ast
import json
import math
import operator
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from pydantic import BaseModel, Field

from debate_decision_system.llm import get_chat_model
from debate_decision_system.retrieve import retrieve
from debate_decision_system.state import DebaterSpec, DebateState
from debate_decision_system.teams import current_seat, public_voice

TOOL_NAMES = ("calculator", "code", "wikipedia", "web_search", "docs")
GROUNDED_TOOLS = frozenset({"calculator", "code", "docs"})
# calculator/run_code below deliberately do NOT use eval()/exec(): their input is
# an LLM's tool-call argument (from plan_tools' structured output), so only a
# fixed allowlist of AST node types, operators, and functions is walked by hand.
# No imports, no attribute access, no arbitrary calls — anything else raises.
_OPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UNARY: dict[type[ast.unaryop], Any] = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_CODE_FUNCS: dict[str, Any] = {
    name: getattr(math, name) for name in dir(math) if not name.startswith("_")
}
_CODE_FUNCS.update({"abs": abs, "min": min, "max": max, "sum": sum, "round": round, "len": len})


class ToolCall(BaseModel):
    name: str = Field(description="calculator | code | wikipedia | web_search | docs")
    input: str = Field(description="Expression, code, or search query")


class ToolPlan(BaseModel):
    tools: list[ToolCall] = Field(default_factory=list)


def allowed_tools(grounding: str) -> frozenset[str]:
    if grounding == "grounded":
        return GROUNDED_TOOLS
    return frozenset(TOOL_NAMES)


def calculator(expr: str) -> str:
    tree = ast.parse(expr, mode="eval")
    return str(_eval_num(tree.body))


def run_code(src: str) -> str:
    tree = ast.parse(src, mode="eval")
    return str(_eval_code(tree.body))


def wikipedia(query: str) -> str:
    title = query.strip().replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
    payload = _get_json(url)
    extract = payload.get("extract") or payload.get("detail") or ""
    page_url = (payload.get("content_urls") or {}).get("desktop", {}).get("page", url)
    if not extract:
        return f"No Wikipedia summary for {query!r}."
    return f"{extract}\n[source: {page_url}]"


def web_search(query: str) -> str:
    q = urllib.parse.urlencode({"q": query, "format": "json", "no_html": 1, "skip_disambig": 1})
    payload = _get_json(f"https://api.duckduckgo.com/?{q}")
    bits: list[str] = []
    abstract = payload.get("AbstractText") or ""
    if abstract:
        src = payload.get("AbstractURL") or "DuckDuckGo"
        bits.append(f"{abstract}\n[source: {src}]")
    for topic in payload.get("RelatedTopics") or []:
        if isinstance(topic, dict) and topic.get("Text"):
            bits.append(f"{topic['Text']}\n[source: {topic.get('FirstURL', 'DuckDuckGo')}]")
        if len(bits) >= 3:  # noqa: PLR2004
            break
    return "\n\n".join(bits) or f"No web snippet for {query!r}."


def execute_tool(name: str, raw_input: str, state: DebateState) -> str:
    if name == "calculator":
        return calculator(raw_input)
    if name == "code":
        return run_code(raw_input)
    if name == "wikipedia":
        return wikipedia(raw_input)
    if name == "web_search":
        return web_search(raw_input)
    if name == "docs":
        return retrieve(list(state.get("documents") or []), raw_input) or "No document hit."
    msg = f"Unknown tool: {name}"
    raise ValueError(msg)


def run_tool_calls(
    state: DebateState, calls: list[ToolCall]
) -> tuple[list[dict[str, str]], list[str]]:
    allowed = allowed_tools(str(state.get("grounding") or "open"))
    turns: list[dict[str, str]] = []
    errors: list[str] = []
    # The 2-tool cap is enforced here too, not just in plan_tools' prompt —
    # the planning LLM was only asked nicely, this is the actual guarantee.
    for call in calls[:2]:
        if call.name not in allowed:
            errors.append(f"tool:{call.name}: blocked in {state.get('grounding', 'open')} mode")
            continue
        try:
            result = execute_tool(call.name, call.input, state)
        except Exception as exc:  # noqa: BLE001
            # A single tool failing (bad expression, network error, etc.) must not
            # abort the debate turn: it becomes a visible transcript entry instead.
            result = f"error: {exc}"
            errors.append(f"tool:{call.name}: {exc}")
        turns.append(
            {
                "role": "tool",
                "name": f"tool:{call.name}",
                "content": f"**{call.name}** `{call.input}`\n\n{result}",
            }
        )
    return turns, errors


def plan_tools(state: DebateState, speaker: DebaterSpec) -> list[ToolCall]:
    allowed = ", ".join(sorted(allowed_tools(str(state.get("grounding") or "open"))))
    system = (
        f"You are {speaker.get('name', 'debater')} planning tools. "
        f"Allowed tools: {allowed}. "
        "Request at most 2 tools only if a number, citation, or fact is missing. "
        "Otherwise return an empty tools list."
    )
    human = f"Question: {state.get('topic', '')}\nLast context: {state.get('topic', '')}"
    turns = state.get("transcript") or []
    if turns:
        human += f"\nLast turn: {turns[-1]['name']}: {turns[-1]['content'][:400]}"
    try:
        llm = get_chat_model(
            speaker.get("provider") or state["provider"],
            speaker.get("model") or state["model"],
            temperature=0.0,
        )
        raw = llm.with_structured_output(ToolPlan).invoke([("system", system), ("human", human)])
        plan = raw if isinstance(raw, ToolPlan) else ToolPlan.model_validate(raw)
    except Exception:  # noqa: BLE001
        return []
    return list(plan.tools)[:2]


def tools_node(state: DebateState) -> dict:
    speaker = public_voice(current_seat(state))
    calls = plan_tools(state, speaker)
    turns, errors = run_tool_calls(state, calls)
    rag_turn = _rag_citation_turn(state)
    if rag_turn:
        turns = [*turns, rag_turn]
    update: dict[str, object] = {"awaiting_speech": True}
    if turns:
        update["transcript"] = turns
    if errors:
        update["errors"] = errors
    return update


def _rag_citation_turn(state: DebateState) -> dict[str, str] | None:
    if not state.get("rag_enabled", True):
        return None
    try:
        from debate_decision_system.rag.pipeline import context_for_state  # noqa: PLC0415
    except ImportError:
        return None
    result = context_for_state(state)
    if not result.block:
        return None
    return {"role": "tool", "name": "tool:rag", "content": result.block}


def _eval_num(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return float(_UNARY[type(node.op)](_eval_num(node.operand)))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return float(_OPS[type(node.op)](_eval_num(node.left), _eval_num(node.right)))
    msg = "calculator allows numbers and + - * / ** % only"
    raise ValueError(msg)


def _eval_code(node: ast.AST) -> object:  # noqa: PLR0911
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)):
        return node.value
    if isinstance(node, ast.Name) and node.id in _CODE_FUNCS:
        return _CODE_FUNCS[node.id]
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval_code(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_code(node.left), _eval_code(node.right))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        func = _CODE_FUNCS.get(node.func.id)
        if func is None or node.keywords:
            msg = "call not allowed"
            raise ValueError(msg)
        return func(*(_eval_code(arg) for arg in node.args))
    if isinstance(node, ast.List):
        return [_eval_code(elt) for elt in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_eval_code(elt) for elt in node.elts)
    msg = "code allows math expressions only (no import, no attributes)"
    raise ValueError(msg)


def _get_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(  # noqa: S310
        url,
        headers={"User-Agent": "debate-decision-system/0.3.0"},
    )
    with urllib.request.urlopen(req, timeout=8) as response:  # noqa: S310
        return json.loads(response.read().decode())
