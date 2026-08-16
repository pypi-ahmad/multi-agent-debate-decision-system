# Copyright (c) 2026 Ahmad Mujtaba
"""Save and load debates as JSON under data/debates/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from debate_decision_system.config import PROJECT_ROOT
from debate_decision_system.state import DebateState

HISTORY_DIR = PROJECT_ROOT / "data" / "debates"


def save_debate(state: DebateState) -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    debate_id = str(state.get("debate_id") or "untitled")
    path = HISTORY_DIR / f"{debate_id}.json"
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return path


def load_debate(debate_id: str) -> DebateState:
    path = HISTORY_DIR / f"{debate_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return cast(DebateState, payload)


def list_debates() -> list[dict[str, Any]]:
    if not HISTORY_DIR.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(
        HISTORY_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True
    ):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rows.append(
            {
                "debate_id": payload.get("debate_id", path.stem),
                "topic": payload.get("topic", ""),
                "phase": payload.get("phase", ""),
            }
        )
    return rows
