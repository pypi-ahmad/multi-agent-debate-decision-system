# Copyright (c) 2026 Ahmad Mujtaba
"""Streamlit UI for the Phase 3 debate system."""

from __future__ import annotations

import streamlit as st

from debate_decision_system import __version__, config
from debate_decision_system.export import debate_to_markdown, timeline_mermaid
from debate_decision_system.graph import (
    advance,
    debate_done,
    initial_state,
    inject_human,
    request_evidence,
)
from debate_decision_system.history import list_debates, load_debate, save_debate
from debate_decision_system.personas import PERSONAS
from debate_decision_system.state import DebateState, Document, Turn

st.set_page_config(
    page_title="Multi-agent debate",
    page_icon=":material/balance:",
    layout="wide",
)

AVATARS = {
    "moderator": ":material/campaign:",
    "debater": ":material/person:",
    "judge": ":material/balance:",
    "human": ":material/face:",
}

EXAMPLES = (
    "Should we ship the local-only mode before adding a hosted fallback?",
    "Is a two-week freeze worth it to pay down the test debt?",
    "Should we replace the weekly review with a written RFC?",
)

PERSONA_NAMES = [p.name for p in PERSONAS]
OUTCOME_COLOR = {"clear_winner": "green", "consensus": "blue", "split": "gray"}

st.session_state.setdefault("transcript", [])
st.session_state.setdefault("verdict", {})
st.session_state.setdefault("errors", [])
st.session_state.setdefault("debate", None)
st.session_state.setdefault("auto_run", False)
st.session_state.setdefault("human_note", "")


@st.cache_data(ttl="30s", max_entries=4)
def _ollama_models() -> list[str]:
    return config.list_ollama_models()


def _model_options(provider: str) -> list[str]:
    if provider == "Ollama":
        return _ollama_models()
    return list(config.models_for_provider(provider))


def _pick_provider_model(
    label: str, key: str, default_provider: str, allowed: tuple[str, ...]
) -> tuple[str, str]:
    provider = st.selectbox(
        f"{label} provider",
        list(allowed),
        index=list(allowed).index(default_provider) if default_provider in allowed else 0,
        key=f"{key}_provider",
    )
    options = _model_options(provider)
    model = st.selectbox(f"{label} model", options, key=f"{key}_model") if options else ""
    return provider, model


def _providers_missing(providers: set[str]) -> str | None:
    for item in providers:
        key = config.required_key(item)
        if key and not getattr(config, key, ""):
            return key
    return None


def _sync(state: DebateState) -> None:
    st.session_state.debate = state
    st.session_state.transcript = list(state.get("transcript") or [])
    st.session_state.verdict = dict(state.get("verdict") or {})
    st.session_state.errors = list(state.get("errors") or [])
    save_debate(state)


def _render_turn(turn: Turn) -> None:
    avatar = AVATARS.get(turn["role"], ":material/chat:")
    with st.chat_message(turn["role"], avatar=avatar):
        st.markdown(f"**{turn['name']}**")
        st.markdown(turn["content"])


def _read_uploads(files: list) -> list[Document]:
    docs: list[Document] = []
    for uploaded in files:
        text = uploaded.read().decode("utf-8", errors="replace")[:20_000]
        docs.append({"name": uploaded.name, "text": text})
    return docs


st.title("Multi-agent debate")
st.caption("Structured decisions, local-only, history, and a live timeline.")

with st.sidebar:
    local_only = st.toggle("Fully local", value=False, help="Force every seat onto Ollama.")
    allowed = ("Ollama",) if local_only else config.PROVIDERS
    default_provider = st.segmented_control(
        "Default provider",
        list(allowed),
        default=allowed[0],
        required=True,
        key="provider",
        width="stretch",
    )
    if default_provider not in allowed:
        default_provider = allowed[0]
    default_options = _model_options(default_provider)
    if default_provider == "Ollama" and not default_options:
        st.warning(
            "No local Ollama models found. Pull a 7B-8B model, then refresh.",
            icon=":material/warning:",
        )
        default_model = ""
    else:
        default_model = (
            st.selectbox("Default model", default_options, key="model") if default_options else ""
        )
    if default_provider == "OpenAI":
        st.caption("Effort is fixed at medium for gpt-5.6-luna and gpt-5.6-terra.")
    if default_provider == "Agnes AI":
        st.caption("Fixed model: agnes-2.5-flash")

    mode = st.segmented_control(
        "Mode",
        ["open", "structured"],
        default="open",
        required=True,
        key="mode",
        width="stretch",
    )
    if mode not in {"open", "structured"}:
        mode = "open"

    st.subheader("Debate")
    debater_count = st.slider(
        "Debaters",
        min_value=config.MIN_DEBATERS,
        max_value=config.MAX_DEBATERS,
        value=config.DEFAULT_DEBATERS,
    )
    max_rounds = st.slider(
        "Rounds",
        min_value=config.MIN_ROUNDS,
        max_value=config.MAX_ROUNDS,
        value=config.DEFAULT_ROUNDS,
        help="Each round gives every debater one turn.",
    )
    temperature = st.slider(
        "Temperature",
        min_value=config.MIN_TEMPERATURE,
        max_value=config.MAX_TEMPERATURE,
        value=config.DEFAULT_TEMPERATURE,
        step=0.1,
    )
    speaking_order = st.segmented_control(
        "Speaking order",
        list(config.SPEAKING_ORDERS),
        default=config.DEFAULT_SPEAKING_ORDER,
        required=True,
        key="speaking_order",
        width="stretch",
    )
    if speaking_order not in config.SPEAKING_ORDERS:
        speaking_order = config.DEFAULT_SPEAKING_ORDER

    persona_names: list[str] = []
    seat_models: list[tuple[str, str]] = []
    used_providers: set[str] = {default_provider}
    with st.expander("Seats", expanded=True):
        for i in range(debater_count):
            st.markdown(f"**Seat {i + 1}**")
            persona = st.selectbox(
                "Persona",
                PERSONA_NAMES,
                index=i % len(PERSONA_NAMES),
                key=f"persona_{i}",
            )
            seat_provider, seat_model = _pick_provider_model(
                "Seat", f"seat_{i}", default_provider, allowed
            )
            if not seat_model:
                seat_provider, seat_model = default_provider, default_model
            persona_names.append(persona)
            seat_models.append((seat_provider, seat_model))
            used_providers.add(seat_provider)

    with st.expander("Moderator and judge"):
        mod_provider, mod_model = _pick_provider_model(
            "Moderator", "mod", default_provider, allowed
        )
        judge_provider, judge_model = _pick_provider_model(
            "Judge", "judge", default_provider, allowed
        )
        if not mod_model:
            mod_provider, mod_model = default_provider, default_model
        if not judge_model:
            judge_provider, judge_model = default_provider, default_model
        used_providers.add(mod_provider)
        used_providers.add(judge_provider)

    uploads = st.file_uploader(
        "Documents",
        type=["txt", "md", "csv", "json"],
        accept_multiple_files=True,
    )
    past = list_debates()
    if past:
        choices = ["(new)", *[f"{row['debate_id']} — {row['topic'][:48]}" for row in past[:12]]]
        chosen = st.selectbox("History", choices, key="history_pick")
        if chosen != "(new)" and st.button("Load debate", icon=":material/history:"):
            loaded = load_debate(chosen.split(" — ", 1)[0])
            _sync(loaded)
            st.session_state.auto_run = False
            st.rerun()

    st.caption(f"debate-decision-system {__version__}")

topic = st.text_area(
    "Decision question",
    placeholder=EXAMPLES[0],
    height=100,
    key="topic",
)
if not st.session_state.transcript:
    picked = st.pills("Try a question", EXAMPLES, label_visibility="collapsed")
    if picked and picked != st.session_state.topic:
        st.session_state.topic = picked
        st.rerun()

missing_key = None if local_only else _providers_missing(used_providers)
seats_ok = all(model for _provider, model in seat_models) and bool(mod_model) and bool(judge_model)
if missing_key:
    st.error(
        f"{missing_key} is not set. Copy `.env.example` to `.env` and add the key.",
        icon=":material/error:",
    )

debate: DebateState | None = st.session_state.debate
running = debate is not None and not debate_done(debate)

if debate is not None:
    st.markdown(timeline_mermaid(debate))
    if debate.get("options"):
        st.caption("Options: " + " · ".join(debate["options"]))

with st.container(horizontal=True):
    start = st.button(
        "Start debate",
        type="primary",
        icon=":material/play_arrow:",
        disabled=not str(st.session_state.topic).strip() or not seats_ok or bool(missing_key),
    )
    pause = st.button("Pause", icon=":material/pause:", disabled=not running)
    step = st.button("One turn", icon=":material/skip_next:", disabled=not running)
    resume = st.button("Run remaining", icon=":material/fast_forward:", disabled=not running)

if start:
    state = initial_state(
        str(st.session_state.topic).strip(),
        default_provider,
        default_model,
        debater_count,
        max_rounds,
        temperature=temperature,
        speaking_order=speaking_order,
        persona_names=persona_names,
        seat_models=seat_models,
        moderator_provider=mod_provider,
        moderator_model=mod_model,
        judge_provider=judge_provider,
        judge_model=judge_model,
        mode=mode,
        local_only=local_only,
        documents=_read_uploads(list(uploads or [])),
    )
    _sync(state)
    st.session_state.auto_run = True
    st.rerun()

if pause:
    st.session_state.auto_run = False

if step and debate is not None:
    st.session_state.auto_run = False
    _sync(advance(debate))
    st.rerun()

if resume and debate is not None:
    st.session_state.auto_run = True
    st.rerun()

if running and debate is not None:
    with st.container(horizontal=True, vertical_alignment="bottom"):
        note = st.text_input("Inject a human note", key="human_note")
        if st.button("Inject", icon=":material/chat:", disabled=not str(note).strip()):
            st.session_state.auto_run = False
            _sync(inject_human(debate, note))
            st.session_state.human_note = ""
            st.rerun()
        if st.button("Ask for evidence", icon=":material/help:"):
            st.session_state.auto_run = False
            _sync(request_evidence(debate))
            st.rerun()

if st.session_state.auto_run and debate is not None and not debate_done(debate):
    _sync(advance(debate))
    if debate_done(st.session_state.debate):
        st.session_state.auto_run = False
    st.rerun()

for turn in st.session_state.transcript:
    _render_turn(turn)

verdict = st.session_state.verdict
if verdict:
    with st.container(border=True):
        st.subheader("Decision report")
        outcome = verdict.get("outcome", "split")
        st.badge(
            outcome.replace("_", " "),
            icon=":material/balance:",
            color=OUTCOME_COLOR.get(outcome, "gray"),
        )
        st.badge(verdict.get("winner", "Split"), color="green")
        if verdict.get("confidence") is not None:
            st.metric("Confidence", f"{verdict.get('confidence')}%")
        st.markdown(verdict.get("recommendation", ""))
        st.caption(verdict.get("rationale", ""))
        args = verdict.get("strongest_arguments") or []
        risks = verdict.get("key_risks") or []
        if args:
            st.markdown("**Strongest arguments**")
            for item in args:
                st.markdown(f"- {item}")
        if risks:
            st.markdown("**Key risks**")
            for item in risks:
                st.markdown(f"- {item}")
        scores = verdict.get("scores") or []
        if scores:
            st.dataframe(scores, hide_index=True)

if st.session_state.debate is not None and st.session_state.transcript:
    st.download_button(
        "Download markdown",
        data=debate_to_markdown(st.session_state.debate),
        file_name="debate.md",
        mime="text/markdown",
        icon=":material/download:",
    )

debater_turns = [t for t in st.session_state.transcript if t["role"] == "debater"]
speakers = list(dict.fromkeys(t["name"] for t in debater_turns))
if len(speakers) >= config.MIN_DEBATERS:
    st.subheader("Compare arguments")
    left, right = st.columns(2)
    with left:
        a = st.selectbox("Left", speakers, index=0, key="cmp_left")
    with right:
        b = st.selectbox("Right", speakers, index=1, key="cmp_right")
    col_a, col_b = st.columns(2)
    for column, name in ((col_a, a), (col_b, b)):
        with column, st.container(border=True):
            st.markdown(f"**{name}**")
            for turn in debater_turns:
                if turn["name"] == name:
                    st.markdown(turn["content"])

if st.session_state.errors:
    with st.expander("Warnings", icon=":material/warning:"):
        for err in st.session_state.errors:
            st.caption(err)
