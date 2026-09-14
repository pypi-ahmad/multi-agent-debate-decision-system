# Copyright (c) 2026 Ahmad Mujtaba
"""Team seats: templates, leader, huddle members."""

from __future__ import annotations

from typing import cast

from debate_decision_system.personas import PERSONA_BY_NAME
from debate_decision_system.state import DebaterSpec, DebateState, Provider, TeamMember

TEAM_TEMPLATES: dict[str, tuple[str, ...]] = {
    "Engineering": ("Pragmatist", "First-principles", "Operator"),
    "Product": ("Optimistic", "Data-driven", "Creative"),
    "Business": ("Pragmatist", "Risk-averse", "Operator"),
    "Security": ("Skeptic", "Risk-averse", "First-principles"),
    "Devil's Advocate": ("Devil's advocate", "Skeptic", "Ethicist"),
}


def is_team(seat: DebaterSpec) -> bool:
    return seat.get("kind") == "team"


def current_seat(state: DebateState) -> DebaterSpec:
    return state["debaters"][int(state.get("next_speaker", 0))]


def huddle_members(seat: DebaterSpec) -> list[TeamMember]:
    return [member for member in seat.get("members") or [] if not member.get("is_leader")]


def leader_member(seat: DebaterSpec) -> TeamMember:
    """Prefer the explicit is_leader flag; fall back to the first member, then
    to a synthetic leader built from the seat itself. The fallbacks exist
    because a team seat can be constructed (e.g. from a template, or by
    graph.py's _normalize_seat) without any member ever marked as leader."""
    members = list(seat.get("members") or [])
    for member in members:
        if member.get("is_leader"):
            return member
    if members:
        return members[0]
    return cast(
        TeamMember,
        {
            "name": seat.get("name") or "Leader",
            "style": seat.get("style") or "",
            "instructions": seat.get("instructions") or "",
            "provider": seat.get("provider") or "Ollama",
            "model": seat.get("model") or "",
            "is_leader": True,
        },
    )


def public_voice(seat: DebaterSpec) -> DebaterSpec:
    """What the transcript/UI shows for this seat. For a team, only the leader's
    persona ever speaks on the public floor — other members are heard only in
    huddle.py's private notes and are never named individually in the debate."""
    if not is_team(seat):
        return seat
    lead = leader_member(seat)
    return cast(
        DebaterSpec,
        {
            "name": seat.get("name") or "Team",
            "style": lead.get("style") or "team lead",
            "instructions": lead.get("instructions") or "State the team's public position.",
            "provider": lead.get("provider") or seat.get("provider") or "Ollama",
            "model": lead.get("model") or seat.get("model") or "",
            "kind": "team",
        },
    )


def members_from_template(team_name: str, provider: str, model: str) -> list[TeamMember]:
    names = TEAM_TEMPLATES.get(team_name, ("Pragmatist", "Skeptic"))
    members: list[TeamMember] = []
    for i, name in enumerate(names):
        persona = PERSONA_BY_NAME.get(name)
        if persona is None:
            continue
        members.append(
            {
                "name": persona.name,
                "style": persona.style,
                "instructions": persona.instructions,
                "provider": cast(Provider, provider),
                "model": model,
                "is_leader": i == 0,
            }
        )
    return members
