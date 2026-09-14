# Copyright (c) 2026 Ahmad Mujtaba
"""LangGraph node functions: moderator, debater, huddle, judge, structure.

Each `*_node(state) -> dict` here is called both by the compiled graph in
graph.py (unused by the app, see its docstring) and by graph.py's manual
`advance()` path (the one actually used). Shared contract: a node must never
raise out of its LLM call — every node wraps the call in try/except and, on
failure, returns a degraded-but-valid update (a fallback transcript line plus
an "errors" entry) so one bad provider call doesn't crash the debate. Read
moderator.py first; it decides who speaks and when the hearing ends.
"""

from __future__ import annotations
