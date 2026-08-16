# Copyright (c) 2026 Ahmad Mujtaba
"""Streamlit entry: debate workspace and decision history."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Multi-agent debate",
    page_icon=":material/balance:",
    layout="wide",
)

page = st.navigation(
    {
        "Workspace": [
            st.Page(
                "app_pages/debate.py",
                title="Debate",
                icon=":material/campaign:",
                default=True,
            ),
            st.Page(
                "app_pages/history.py",
                title="Decision history",
                icon=":material/history:",
            ),
            st.Page(
                "app_pages/analytics.py",
                title="Analytics",
                icon=":material/insights:",
            ),
        ]
    }
)
page.run()
