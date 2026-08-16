# Copyright (c) 2026 Ahmad Mujtaba
"""Analytics dashboard, quality report, and simulation."""

from __future__ import annotations

import uuid
from collections import Counter

import pandas as pd
import streamlit as st

from debate_decision_system import config
from debate_decision_system.analytics import (
    persona_win_rates,
    quality_report,
    reset_for_rerun,
    run_until_done,
    strength_series,
)
from debate_decision_system.graph import advance
from debate_decision_system.history import list_debates, load_debate, save_debate

st.title("Debate analytics")
st.caption("Win rates, circular speech, participation, and multi-run simulation.")

records = list_debates()
decided = [row for row in records if row.get("status") == "decided"]

if not records:
    st.info("No debates stored yet. Run one hearing first.", icon=":material/info:")
    st.stop()

wins = persona_win_rates(decided)
if wins:
    st.subheader("Who wins")
    st.bar_chart(pd.Series(wins, name="wins"))

conf_by_day: dict[str, list[int]] = {}
for row in decided:
    day = str(row.get("created_at") or "")[:10]
    if row.get("confidence") is None:
        continue
    conf_by_day.setdefault(day, []).append(int(row["confidence"]))
if conf_by_day:
    st.subheader("Confidence over time")
    st.line_chart(
        pd.Series({day: sum(vals) / len(vals) for day, vals in sorted(conf_by_day.items())})
    )

labels = [f"{row['created_at'][:10]} · {row['topic'][:60]}" for row in records]
pick = st.selectbox("Inspect a debate", range(len(records)), format_func=lambda i: labels[i])
chosen = records[pick]
state = load_debate(chosen["debate_id"])
report = quality_report(state)

st.subheader("Debate quality report")
st.markdown(report["summary"])
if report["participation"]:
    st.bar_chart(pd.Series(report["participation"], name="turns"))
if report["circular"]:
    st.warning(
        "Circular pairs: "
        + ", ".join(f"{p['left']}→{p['right']} ({p['overlap']})" for p in report["circular"]),
        icon=":material/sync:",
    )
series = report["strength_series"] or strength_series(state)
if series:
    st.subheader("Argument strength")
    st.line_chart(pd.Series(series, name="strength"))

st.subheader("Simulate / re-run")
runs = st.slider("Runs", 2, 5, 2)
model_pool = list(config.models_for_provider("OpenAI")) + list(config.GOOGLE_MODELS)
local = []
try:
    local = config.list_ollama_models()
except Exception:  # noqa: BLE001
    local = []
choices = local or model_pool
models = st.multiselect("Models to compare", choices, default=choices[:1] if choices else [])
if st.button("Run simulation", type="primary", icon=":material/science:"):
    if not models:
        st.error("Pick at least one model.", icon=":material/error:")
    else:
        batch = uuid.uuid4().hex[:8]
        outcomes: list[str] = []
        with st.status("Simulation running", expanded=True) as status:
            for model in models:
                for i in range(runs):
                    status.write(f"{model} run {i + 1}")
                    trial = reset_for_rerun(state, model=model, batch_id=batch)
                    finished = run_until_done(trial, advance)
                    save_debate(finished)
                    outcomes.append(str((finished.get("verdict") or {}).get("winner") or "n/a"))
            status.update(label="Simulation complete", state="complete")
        st.bar_chart(pd.Series(Counter(outcomes), name="wins"))
        st.caption(f"Batch {batch}. Results are in Decision history.")
