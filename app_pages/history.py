# Copyright (c) 2026 Ahmad Mujtaba
"""Search, filter, resume, tag, archive, and export past decisions."""

from __future__ import annotations

import streamlit as st

from debate_decision_system.analytics import reset_for_rerun
from debate_decision_system.export import debate_to_markdown
from debate_decision_system.memory import (
    archive_decision,
    delete_decision,
    link_decisions,
    list_categories,
    list_debates,
    list_tags,
    load_debate,
    related_ids,
    search_decisions,
    update_decision_meta,
)

st.title("Decision history")
st.caption("Local SQLite. Search why you chose something, then resume or export.")

query = st.text_input("Search", placeholder="Why did we decide X last month?")
status = st.segmented_control(
    "Status",
    ["any", "decided", "in_progress", "archived"],
    default="any",
    key="hist_status",
)
outcome = st.selectbox("Outcome", ["any", "clear_winner", "consensus", "split"])
min_conf = st.slider("Min confidence", 0, 100, 0)
span = st.date_input("Date range", value=(), key="hist_dates")
known_tags = list_tags()
tag = st.selectbox("Tag", ["any", *known_tags], key="hist_tag")
known_cats = list_categories()
category = st.selectbox("Category", ["any", *known_cats], key="hist_category")

# st.date_input with a range can return (), a single date, or a 2-tuple
# depending on how many endpoints the user has picked so far — handle all three.
dates = (
    [item.isoformat() for item in span if item]
    if isinstance(span, tuple)
    else ([span.isoformat()] if span else [])
)
since = dates[0] if dates else ""
# `until` is a bare date string; memory.py's _until_bound() treats it as
# inclusive of that whole day, not an exclusive instant at midnight.
until = dates[1] if len(dates) > 1 else ""

status_value = "" if status == "any" else str(status)
rows = search_decisions(
    query,
    outcome="" if outcome == "any" else outcome,
    status=status_value,
    since=since,
    until=until,
    tag="" if tag == "any" else str(tag),
    category="" if category == "any" else str(category),
    min_confidence=None if min_conf == 0 else min_conf,
    include_archived=status_value == "archived",
)

if not rows:
    st.info("No decisions yet. Run a debate first.", icon=":material/info:")
    st.stop()

labels = [f"{row['created_at'][:10]} · {row['topic'][:72]}" for row in rows]
pick = st.selectbox("Results", range(len(rows)), format_func=lambda i: labels[i])
record = rows[pick]
state = load_debate(record["debate_id"])

st.subheader(record["topic"])
st.caption(
    f"{record['decision_id']} · {record['status']}"
    f"{' · archived' if record['archived'] else ''} · {record['created_at']} · "
    f"{', '.join(record['participants'])}"
)
if record["recommendation"]:
    st.markdown(f"**Recommendation:** {record['recommendation']}")
if record["confidence"] is not None:
    st.metric("Confidence", f"{record['confidence']}%")
if record["arguments_for"]:
    st.markdown("**Arguments for**")
    for item in record["arguments_for"]:
        st.markdown(f"- {item}")
if record["arguments_against"]:
    st.markdown("**Arguments against**")
    for item in record["arguments_against"]:
        st.markdown(f"- {item}")
if record["key_arguments"] and not record["arguments_for"] and not record["arguments_against"]:
    st.markdown("**Key arguments**")
    for item in record["key_arguments"]:
        st.markdown(f"- {item}")
if record["rationale"]:
    st.caption(record["rationale"])
if record["agent_models"]:
    with st.expander("Models by seat", icon=":material/memory:"):
        for name, model in record["agent_models"].items():
            st.caption(f"{name}: {model}")

with st.expander("Full transcript", icon=":material/forum:", expanded=False):
    for turn in state.get("transcript") or []:
        st.markdown(f"**{turn.get('name', '')}** ({turn.get('role', '')})")
        st.markdown(turn.get("content", ""))

with st.form("decision_meta"):
    notes = st.text_area("Notes", value=str(record.get("notes") or ""), height=100)
    tags = st.multiselect(
        "Tags",
        options=sorted(set(known_tags) | set(record.get("tags") or [])),
        default=list(record.get("tags") or []),
        accept_new_options=True,
    )
    category_value = st.text_input("Category", value=str(record.get("category") or ""))
    if st.form_submit_button("Save notes and tags", icon=":material/save:"):
        update_decision_meta(
            record["debate_id"],
            notes=notes,
            tags=[str(item).strip() for item in tags if str(item).strip()],
            category=category_value.strip(),
        )
        st.rerun()

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
    # Manually mirrors debate.py's _sync()/session_state keys rather than
    # importing it (a private helper of that page) — keep these keys in sync
    # with debate.py if that page's session_state contract changes.
    if st.button("Continue debate", type="primary", icon=":material/play_arrow:"):
        st.session_state.debate = state
        st.session_state.transcript = list(state.get("transcript") or [])
        st.session_state.verdict = dict(state.get("verdict") or {})
        st.session_state.errors = list(state.get("errors") or [])
        st.session_state.auto_run = False
        st.switch_page("app_pages/debate.py")
    if st.button("Re-run with new settings", icon=":material/replay:"):
        fresh = reset_for_rerun(state)
        st.session_state.debate = fresh
        st.session_state.transcript = []
        st.session_state.verdict = {}
        st.session_state.errors = []
        st.session_state.auto_run = False
        st.session_state.topic = fresh.get("topic", "")
        st.switch_page("app_pages/debate.py")
    st.download_button(
        "Export record",
        data=debate_to_markdown(state),
        file_name=f"{record['debate_id']}.md",
        mime="text/markdown",
        icon=":material/download:",
    )

with st.container(horizontal=True):
    if record["archived"]:
        if st.button("Unarchive", icon=":material/unarchive:"):
            archive_decision(record["debate_id"], archived=False)
            st.rerun()
    elif st.button("Archive", icon=":material/archive:"):
        archive_decision(record["debate_id"])
        st.rerun()
    confirm = st.toggle("Confirm delete", key="hist_confirm_delete")
    if st.button("Delete", icon=":material/delete:", disabled=not confirm):
        delete_decision(record["debate_id"])
        st.rerun()
