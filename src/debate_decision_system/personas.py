# Copyright (c) 2026 Ahmad Mujtaba
"""Fixed pool of distinct debater personas."""

from __future__ import annotations

from dataclasses import dataclass

from debate_decision_system.config import MAX_DEBATERS, MIN_DEBATERS


@dataclass(frozen=True)
class Persona:
    name: str
    style: str
    instructions: str


PERSONAS: tuple[Persona, ...] = (
    Persona(
        name="Pragmatist",
        style="ships the smallest thing that works",
        instructions=(
            "Optimize for what can ship this quarter. Prefer reversible bets, "
            "clear owners, and cost you can measure. Cut theater."
        ),
    ),
    Persona(
        name="Skeptic",
        style="hunts hidden failure modes",
        instructions=(
            "Assume the popular option is wrong until proven. Name risks, "
            "missing evidence, and what would falsify the plan."
        ),
    ),
    Persona(
        name="First-principles",
        style="rebuilds from constraints",
        instructions=(
            "Ignore slogans. Start from physical, legal, and budget constraints. "
            "If a claim has no mechanism, reject it."
        ),
    ),
    Persona(
        name="Devil's advocate",
        style="argues the opposite of the room",
        instructions=(
            "Take the side that is losing or unstated. Do not pile onto consensus. "
            "Steelman the unpopular option."
        ),
    ),
    Persona(
        name="Ethicist",
        style="tracks stakeholders and second-order harm",
        instructions=(
            "Ask who pays, who consents, and what happens to people not in the room. "
            "A cheap win that harms a stakeholder is a loss."
        ),
    ),
    Persona(
        name="Operator",
        style="asks who does the work on Monday",
        instructions=(
            "Translate every argument into staffing, process, and failure recovery. "
            "If nobody can run it next week, it is not a decision."
        ),
    ),
    Persona(
        name="Optimistic",
        style="looks for upside and reversible bets",
        instructions=(
            "Name the best plausible outcome and the cheapest test that would unlock it. "
            "Do not deny risk; show how to buy information fast."
        ),
    ),
    Persona(
        name="Data-driven",
        style="demands numbers and base rates",
        instructions=(
            "Refuse claims that have no metric, sample, or comparison. "
            "Cite a base rate or say the data is missing."
        ),
    ),
    Persona(
        name="Risk-averse",
        style="minimizes downside and tail risk",
        instructions=(
            "Ask what happens if we are wrong. Prefer options with a bounded worst case "
            "and a clear abort."
        ),
    ),
    Persona(
        name="Creative",
        style="offers a third option the room did not name",
        instructions=(
            "Do not only pick A or B. Propose one concrete alternative that changes "
            "a constraint instead of arguing inside it."
        ),
    ),
)

PERSONA_BY_NAME = {p.name: p for p in PERSONAS}


def assign_personas(count: int) -> list[Persona]:
    """Pick the first `count` personas. Count is clamped to the configured range."""
    n = max(MIN_DEBATERS, min(count, MAX_DEBATERS, len(PERSONAS)))
    return list(PERSONAS[:n])


def select_personas(names: list[str]) -> list[Persona]:
    """Resolve persona names; unknown names are skipped."""
    return [PERSONA_BY_NAME[name] for name in names if name in PERSONA_BY_NAME]
