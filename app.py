#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  AI-Powered Prisma / PostgreSQL Query Optimizer — Streamlit Dashboard
=============================================================================
  Wraps the existing 3-phase AI optimization pipeline into a live,
  interactive web UI.  No existing scripts are modified.

  Usage:
    streamlit run app.py
    streamlit run app.py --server.port=8501

  Environment:
    GEMINI_API_KEY   — required by run_phase_1.py
    PG_HOST / PG_PORT / PG_DBNAME / PG_USER / PG_PASSWORD
                     — required by run_phase_2.py (optional if no live DB)
=============================================================================
"""

import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from agent_tools.langgraph_agent import agent_app, write_memory
import streamlit as st

load_dotenv()

ROOT_DIR = Path(__file__).parent
ARTIFACTS_DIR = ROOT_DIR / "optimization_artifacts"
PRISMA_SCHEMA = ROOT_DIR / "prisma" / "schema.prisma"

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI DB Optimizer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — premium dark theme with glassmorphism accents
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ── Global ────────────────────────────────────────────────────────────── */
html, body, [class*="st-"] {
    font-family: 'Inter', sans-serif;
}

/* ── Header hero section ───────────────────────────────────────────────── */
.hero-header {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    border-radius: 16px;
    padding: 2.5rem 2rem;
    margin-bottom: 2rem;
    border: 1px solid rgba(255,255,255,.08);
    box-shadow: 0 8px 32px rgba(0,0,0,.45);
}
.hero-header h1 {
    color: #fff;
    font-weight: 800;
    font-size: 2.1rem;
    margin: 0 0 0.4rem 0;
    letter-spacing: -0.5px;
}
.hero-header p {
    color: rgba(255,255,255,.65);
    font-size: 1.05rem;
    margin: 0;
    line-height: 1.55;
}

/* ── Glass card ────────────────────────────────────────────────────────── */
.glass-card {
    background: rgba(255,255,255,.04);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 24px rgba(0,0,0,.25);
}

/* ── Phase step chips ──────────────────────────────────────────────────── */
.phase-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.85rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.3px;
    margin-right: 0.5rem;
}
.phase-chip.running { background: #2563eb33; color: #60a5fa; border: 1px solid #2563eb55; }
.phase-chip.done    { background: #16a34a22; color: #4ade80; border: 1px solid #16a34a44; }
.phase-chip.error   { background: #dc262622; color: #f87171; border: 1px solid #dc262644; }
.phase-chip.pending { background: #52525b22; color: #a1a1aa; border: 1px solid #52525b44; }

/* ── Stat cards ────────────────────────────────────────────────────────── */
.stat-card {
    background: linear-gradient(145deg, rgba(99,102,241,.12), rgba(139,92,246,.08));
    border: 1px solid rgba(139,92,246,.18);
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
}
.stat-card .value {
    font-size: 1.8rem;
    font-weight: 800;
    color: #a78bfa;
    line-height: 1;
}
.stat-card .label {
    font-size: 0.78rem;
    font-weight: 500;
    color: rgba(255,255,255,.5);
    margin-top: 0.35rem;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}

/* ── Sidebar polish ────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0c29 0%, #1a1a2e 100%);
}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #c4b5fd !important;
}

/* ── Submit button ─────────────────────────────────────────────────────── */
div.stButton > button[kind="primary"],
div.stButton > button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    padding: 0.75rem 2rem !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 14px rgba(99,102,241,.35) !important;
}
div.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(139,92,246,.5) !important;
}

/* ── Text areas ────────────────────────────────────────────────────────── */
textarea {
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace !important;
    font-size: 0.88rem !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.caption("Environment variables are read at runtime.")

    api_key_present = bool(os.environ.get("GEMINI_API_KEY"))
    db_host = os.environ.get("PG_HOST", "localhost")
    db_port = os.environ.get("PG_PORT", "5432")
    db_name = os.environ.get("PG_DBNAME", "postgres")

    st.markdown(f"""
    | Variable | Status |
    |---|---|
    | `GEMINI_API_KEY` | {"✅ Set" if api_key_present else "❌ **Not set**"} |
    | `PG_HOST` | `{db_host}` |
    | `PG_PORT` | `{db_port}` |
    | `PG_DBNAME` | `{db_name}` |
    """)

    if not api_key_present:
        st.warning("⚠️ `GEMINI_API_KEY` is not set.  The AI agent will fail unless you export it before launching Streamlit.")

    st.divider()
    st.markdown(
        "<div style='text-align:center;color:rgba(255,255,255,.3);font-size:0.7rem;'>"
        "AI DB Optimizer v1.0 · Built with Streamlit"
        "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="hero-header">
    <h1>⚡ AI-Powered Database Optimizer</h1>
    <p>
        Paste a slow SQL query and your Prisma schema below.
        The AI agent will diagnose the root cause, mathematically validate
        index hypotheses via HypoPG, and generate production-ready
        Prisma code rewrites — all in seconds.
    </p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------
col_sql, col_schema = st.columns(2, gap="large")

with col_sql:
    st.markdown("### 🔍 Raw Slow SQL Query")
    sql_input = st.text_area(
        "Paste the intercepted SQL or Prisma query pattern here",
        height=220,
        placeholder=(
            "SELECT id, title, author_id FROM posts WHERE status = 'PUBLISHED';\n"
            "[+500 individual SELECT id, name, email FROM authors WHERE id = ?]"
        ),
        key="sql_input",
        label_visibility="collapsed",
    )

with col_schema:
    st.markdown("### 📐 Prisma Schema Context")

    # Pre-fill with actual schema if it exists
    default_schema = ""
    if PRISMA_SCHEMA.exists():
        try:
            default_schema = PRISMA_SCHEMA.read_text(encoding="utf-8")
        except Exception:
            pass

    schema_input = st.text_area(
        "Paste or edit your Prisma schema (auto-loaded from prisma/schema.prisma)",
        value=default_schema,
        height=220,
        placeholder="model User {\n  id   Int    @id @default(autoincrement())\n  name String\n}",
        key="schema_input",
        label_visibility="collapsed",
    )

# Advanced options
with st.expander("⚙️ Advanced Options", expanded=False):
    adv_col1, adv_col2, adv_col3 = st.columns(3)
    with adv_col1:
        query_count = st.number_input(
            "Estimated query count",
            min_value=1, max_value=100_000, value=501,
            help="How many individual DB queries this pattern triggers (e.g., 501 for an N+1 with 500 rows).",
        )
    with adv_col2:
        baseline_ms = st.number_input(
            "Baseline latency (ms)",
            min_value=1, max_value=600_000, value=1250,
            help="Observed total execution time in milliseconds.",
        )
    with adv_col3:
        pass

st.markdown("")
run_clicked = st.button("🚀  Optimize Query", use_container_width=True, type="primary")


# ---------------------------------------------------------------------------
# Execution pipeline
# ---------------------------------------------------------------------------
if run_clicked:
    if not sql_input.strip():
        st.toast("⚠️ Please paste a SQL query before running.", icon="⚠️")
        st.warning("Please enter a slow SQL query in the left panel.")
        st.stop()

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    if schema_input.strip():
        PRISMA_SCHEMA.parent.mkdir(parents=True, exist_ok=True)
        PRISMA_SCHEMA.write_text(schema_input.strip(), encoding="utf-8")

    initial_state = {
        "tenant_id": "streamlit_user",
        "query_text": sql_input.strip(),
        "params": {},
        "duration_ms": str(baseline_ms),
        "schema_context": schema_input.strip(),
        "table_stats": {},
        "explain_plan": {},
        "hypotheses": [],
        "current_iteration": 0,
        "memory_match_found": False,
        "memory_match_id": None,
        "proposed_fix": "",
        "validated_cost_reduction": 0.0,
        "risk_level": 0,
        "approval_status": "PENDING",
        "approval_request_id": None,
    }
    thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    with st.status("🧠 AI Agent Thinking...", expanded=True) as status:
        for event in agent_app.stream(initial_state, thread_config):
            for node_name, state_update in event.items():
                st.write(f"✅ Completed: **{node_name}**")
        status.update(label="✅ Optimization Complete!", state="complete", expanded=False)

    try:
        final_state = agent_app.get_state(thread_config).values
    except Exception:
        final_state = None

    if final_state:
        try:
            write_memory(final_state)
        except Exception:
            pass

    st.divider()
    st.markdown("## 📊 Optimization Results")

    reduction = final_state.get("validated_cost_reduction", 0.0) if final_state else 0.0
    hypotheses = final_state.get("hypotheses", []) if final_state else []
    root_cause = hypotheses[0].get("label", "Unknown") if hypotheses else "Unknown"
    latency_reduction = f"{reduction:.1f}%"
    memory_status = "Memory Hit! 🚀" if (final_state and final_state.get("memory_match_found")) else "Fresh Analysis"
    approval = final_state.get("approval_status", "N/A") if final_state else "N/A"

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="value">{latency_reduction}</div>
            <div class="label">Latency Reduction</div>
        </div>
        """, unsafe_allow_html=True)
    with sc2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="value" style="font-size:1rem;">{root_cause}</div>
            <div class="label">Root Cause</div>
        </div>
        """, unsafe_allow_html=True)
    with sc3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="value" style="font-size:1rem;">{memory_status}</div>
            <div class="label">Analysis Source</div>
        </div>
        """, unsafe_allow_html=True)
    with sc4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="value" style="font-size:1rem;">{approval}</div>
            <div class="label">Approval Status</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    proposed_fix = final_state.get("proposed_fix", "") if final_state else ""
    if proposed_fix:
        st.divider()
        st.markdown("## 📋 Proposed Fix")
        st.markdown(
            '<div class="glass-card">',
            unsafe_allow_html=True,
        )
        st.markdown(proposed_fix)
        st.markdown("</div>", unsafe_allow_html=True)

        st.download_button(
            label="⬇️  Download Proposed Fix",
            data=proposed_fix,
            file_name="proposed_fix.md",
            mime="text/markdown",
        )
    else:
        st.warning("No fix was proposed by the agent.")

    with st.expander("🔬 Raw Agent State (JSON)", expanded=False):
        if final_state:
            st.json(final_state)
        else:
            st.json({"status": "not available"})

# ---------------------------------------------------------------------------
# Footer — always visible
# ---------------------------------------------------------------------------
st.markdown("")
st.markdown(
    "<div style='text-align:center;padding:2rem 0 1rem;color:rgba(255,255,255,.25);font-size:0.75rem;'>"
    "AI-Powered Database Optimizer · Gemini 2.5 Flash · HypoPG · Prisma ORM"
    "</div>",
    unsafe_allow_html=True,
)
