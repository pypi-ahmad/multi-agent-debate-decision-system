# Copyright (c) 2026 Ahmad Mujtaba
"""Search, filter, resume, link, and export past decisions."""

from __future__ import annotations

import streamlit as st

from debate_decision_system.analytics import reset_for_rerun
from debate_decision_system.export import debate_to_markdown
from debate_decision_system.history import (
    link_decisions,
    list_debates,
    load_debate,
    related_ids,
    search_decisions,
)

st.title("Decision history")
st.caption("Local SQLite. Search why you chose something, then resume or export.")

query = st.text_input("Search", placeholder="Why did we choose X last month?")
status = st.segmented_control(
    "Status",
    ["any", "decided", "in_progress"],
    default="any",
    key="hist_status",
)
outcome = st.selectbox("Outcome", ["any", "clear_winner", "consensus", "split"])
min_conf = st.slider("Min confidence", 0, 100, 0)
since = st.text_input("Since (ISO date)", placeholder="2026-01-01")

rows = search_decisions(
    query,
    outcome="" if outcome == "any" else outcome,
    status="" if status == "any" else str(status),
    since=since.strip(),
    min_confidence=None if min_conf == 0 else min_conf,
)

if not rows:
    st.info("No decisions yet. Run a debate first.", icon=":material/info:")
    st.stop()

labels = [f"{row['created_at'][:10]} · {row['topic'][:72]}" for row in rows]
pick = st.selectbox("Results", range(len(rows)), format_func=lambda i: labels[i])
record = rows[pick]

st.subheader(record["topic"])
st.caption(
    f"{record['debate_id']} · {record['status']} · {record['created_at']} · "
    f"{', '.join(record['participants'])}"
)
if record["recommendation"]:
    st.markdown(f"**Recommendation:** {record['recommendation']}")
if record["confidence"] is not None:
    st.metric("Confidence", f"{record['confidence']}%")
if record["key_arguments"]:
    st.markdown("**Key arguments**")
    for item in record["key_arguments"]:
        st.markdown(f"- {item}")
if record["rationale"]:
    st.caption(record["rationale"])

linked = related_ids(record["debate_id"])
if linked:
    st.markdown("**Related**")
    for other in linked:
        st.caption(other)

others = [row for row in list_debates() if row["debate_id"] != record["debate_id"]]
if others:
    target = st.selectbox(
        "Link to",
        others,
        format_func=lambda row: f"{row['topic'][:60]} ({row['debate_id']})",
        key="link_target",
    )
    if st.button("Link decisions", icon=":material/link:"):
        link_decisions(record["debate_id"], target["debate_id"])
        st.rerun()

with st.container(horizontal=True):
    if st.button("Continue debate", type="primary", icon=":material/play_arrow:"):
        state = load_debate(record["debate_id"])
        st.session_state.debate = state
        st.session_state.transcript = list(state.get("transcript") or [])
        st.session_state.verdict = dict(state.get("verdict") or {})
        st.session_state.errors = list(state.get("errors") or [])
        st.session_state.auto_run = False
        st.switch_page("app_pages/debate.py")
    if st.button("Re-run with new settings", icon=":material/replay:"):
        fresh = reset_for_rerun(load_debate(record["debate_id"]))
        st.session_state.debate = fresh
        st.session_state.transcript = []
        st.session_state.verdict = {}
        st.session_state.errors = []
        st.session_state.auto_run = False
        st.session_state.topic = fresh.get("topic", "")
        st.switch_page("app_pages/debate.py")
    state = load_debate(record["debate_id"])
    st.download_button(
        "Export record",
        data=debate_to_markdown(state),
        file_name=f"{record['debate_id']}.md",
        mime="text/markdown",
        icon=":material/download:",
    )
