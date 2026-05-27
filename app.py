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

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Paths — resolved relative to this file so it works inside Docker too
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent
ARTIFACTS_DIR = ROOT_DIR / "optimization_artifacts"
INPUT_JSON = ARTIFACTS_DIR / "slow_query_input.json"
PHASE1_SCRIPT = ARTIFACTS_DIR / "run_phase_1.py"
PHASE2_SCRIPT = ARTIFACTS_DIR / "run_phase_2.py"
PHASE3_SCRIPT = ARTIFACTS_DIR / "run_phase_3.py"
PHASE1_OUTPUT = ARTIFACTS_DIR / "phase_1_output.json"
PHASE2_OUTPUT = ARTIFACTS_DIR / "phase_2_output.json"
PHASE3_OUTPUT = ARTIFACTS_DIR / "phase_3_output.json"
PRISMA_INSTRUCTIONS = ARTIFACTS_DIR / "PRISMA_INSTRUCTIONS.md"
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
# Session-state defaults
# ---------------------------------------------------------------------------
if "run_history" not in st.session_state:
    st.session_state.run_history = []
if "last_run_result" not in st.session_state:
    st.session_state.last_run_result = None


# ---------------------------------------------------------------------------
# Helper: run a single pipeline phase via subprocess
# ---------------------------------------------------------------------------
def _run_phase(script_path: Path, label: str, env: dict) -> dict:
    """
    Execute a single phase script and return a result dict with
    stdout, stderr, return code, and wall-clock duration.
    """
    if not script_path.exists():
        return {
            "phase": label,
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Script not found: {script_path}",
            "duration_s": 0.0,
        }

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            env=env,
            cwd=str(ROOT_DIR),
        )
        duration = time.perf_counter() - t0
        return {
            "phase": label,
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_s": round(duration, 2),
        }
    except subprocess.TimeoutExpired:
        return {
            "phase": label,
            "success": False,
            "returncode": -2,
            "stdout": "",
            "stderr": "Timed out after 300 seconds.",
            "duration_s": 300.0,
        }
    except Exception as exc:
        return {
            "phase": label,
            "success": False,
            "returncode": -3,
            "stdout": "",
            "stderr": str(exc),
            "duration_s": round(time.perf_counter() - t0, 2),
        }


# ---------------------------------------------------------------------------
# Helper: safely read JSON from file
# ---------------------------------------------------------------------------
def _read_json(path: Path) -> dict | None:
    try:
        if path.exists() and path.stat().st_size > 0:
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


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
        st.warning("⚠️ `GEMINI_API_KEY` is not set.  Phase 1 will fail unless you export it before launching Streamlit.")

    st.divider()
    st.markdown("## 📜 Run History")

    if st.session_state.run_history:
        for i, entry in enumerate(reversed(st.session_state.run_history)):
            status_icon = "✅" if entry.get("all_success") else "⚠️"
            ts = entry.get("timestamp", "")
            st.caption(f"{status_icon}  Run #{len(st.session_state.run_history) - i}  —  {ts}")
    else:
        st.caption("_No runs yet._")

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
        skip_phase2 = st.checkbox(
            "Skip Phase 2 (HypoPG)",
            value=False,
            help="Check this if you don't have a live PostgreSQL instance with HypoPG. Phase 2 will be skipped gracefully.",
        )

st.markdown("")
run_clicked = st.button("🚀  Optimize Query", use_container_width=True, type="primary")


# ---------------------------------------------------------------------------
# Execution pipeline
# ---------------------------------------------------------------------------
if run_clicked:
    # ── Validation ────────────────────────────────────────────────────────
    if not sql_input.strip():
        st.toast("⚠️ Please paste a SQL query before running.", icon="⚠️")
        st.warning("Please enter a slow SQL query in the left panel.")
        st.stop()

    # ── Build the JSON payload (same schema as Phase 1 expects) ───────────
    payload = {
        "raw_query": sql_input.strip(),
        "query_count": query_count,
        "baseline_explain": {
            "Analysis": "Submitted via Streamlit dashboard.",
            "Execution Time": baseline_ms,
            "Execution Time Unit": "ms",
        },
        "intercepted_code": "Submitted manually via the AI DB Optimizer dashboard.",
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    INPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Also write the schema context to prisma/schema.prisma if user pasted one
    if schema_input.strip():
        PRISMA_SCHEMA.parent.mkdir(parents=True, exist_ok=True)
        PRISMA_SCHEMA.write_text(schema_input.strip(), encoding="utf-8")

    # ── Env for subprocesses ──────────────────────────────────────────────
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    # ── Phase execution with progress ─────────────────────────────────────
    phases = [
        ("Phase 1 — AI Diagnostician (Gemini)", PHASE1_SCRIPT, False),
        ("Phase 2 — HypoPG Cost Evaluator", PHASE2_SCRIPT, skip_phase2),
        ("Phase 3 — ORM Translator", PHASE3_SCRIPT, False),
    ]

    results = []
    progress_bar = st.progress(0, text="Initializing pipeline…")

    for idx, (label, script, should_skip) in enumerate(phases):
        step_frac = (idx) / len(phases)
        progress_bar.progress(step_frac, text=f"Running {label}…")

        if should_skip:
            results.append({
                "phase": label,
                "success": True,
                "returncode": 0,
                "stdout": "Skipped by user (no live DB).",
                "stderr": "",
                "duration_s": 0.0,
                "skipped": True,
            })
            continue

        with st.spinner(f"⏳ {label}"):
            result = _run_phase(script, label, env)
            results.append(result)

        if not result["success"]:
            progress_bar.progress(
                (idx + 1) / len(phases),
                text=f"❌ {label} failed — subsequent phases may be affected.",
            )
            # Don't hard-stop: let remaining phases attempt (they have their own error handling)

    progress_bar.progress(1.0, text="✅ Pipeline complete!")
    time.sleep(0.3)
    progress_bar.empty()

    # ── Record history ────────────────────────────────────────────────────
    run_record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "query_preview": sql_input.strip()[:80],
        "all_success": all(r["success"] for r in results),
        "phases": results,
    }
    st.session_state.run_history.append(run_record)
    st.session_state.last_run_result = run_record

    # ── Results section ───────────────────────────────────────────────────
    st.divider()
    st.markdown("## 📊 Pipeline Results")

    # Stat cards row
    total_time = sum(r["duration_s"] for r in results)
    phases_passed = sum(1 for r in results if r["success"])
    phases_total = len(results)

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="value">{phases_passed}/{phases_total}</div>
            <div class="label">Phases Passed</div>
        </div>
        """, unsafe_allow_html=True)
    with sc2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="value">{total_time:.1f}s</div>
            <div class="label">Total Runtime</div>
        </div>
        """, unsafe_allow_html=True)

    # Pull stats from Phase 1 output if available
    p1_data = _read_json(PHASE1_OUTPUT)
    if p1_data:
        root_cause = p1_data.get("diagnosis", {}).get("root_cause_category", "—")
        latency_drop = p1_data.get("winning_hypothesis", {}).get("latency_reduction_pct", "—")
        with sc3:
            display_cause = root_cause.replace("_", " ").title() if isinstance(root_cause, str) else root_cause
            st.markdown(f"""
            <div class="stat-card">
                <div class="value" style="font-size:1rem;">{display_cause}</div>
                <div class="label">Root Cause</div>
            </div>
            """, unsafe_allow_html=True)
        with sc4:
            st.markdown(f"""
            <div class="stat-card">
                <div class="value">{latency_drop}%</div>
                <div class="label">Latency Reduction</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        with sc3:
            st.markdown("""
            <div class="stat-card">
                <div class="value">—</div>
                <div class="label">Root Cause</div>
            </div>
            """, unsafe_allow_html=True)
        with sc4:
            st.markdown("""
            <div class="stat-card">
                <div class="value">—</div>
                <div class="label">Latency Reduction</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("")

    # Phase-level expanders with stdout/stderr
    for r in results:
        skipped = r.get("skipped", False)
        if skipped:
            icon = "⏭️"
            status_text = "SKIPPED"
        elif r["success"]:
            icon = "✅"
            status_text = f"OK  ({r['duration_s']}s)"
        else:
            icon = "❌"
            status_text = f"FAILED  (exit {r['returncode']})"

        with st.expander(f"{icon}  {r['phase']}  —  {status_text}", expanded=not r["success"] and not skipped):
            if r["stdout"].strip():
                st.code(r["stdout"], language="text")
            if r["stderr"].strip():
                st.error(f"**stderr:**\n```\n{r['stderr']}\n```")
            if skipped:
                st.info("This phase was skipped because the *Skip Phase 2* option was enabled.")

    # ── Rendered optimization report ──────────────────────────────────────
    st.divider()
    st.markdown("## 📋 AI Optimization Report")

    if PRISMA_INSTRUCTIONS.exists() and PRISMA_INSTRUCTIONS.stat().st_size > 0:
        try:
            report_md = PRISMA_INSTRUCTIONS.read_text(encoding="utf-8")
            st.markdown(
                '<div class="glass-card">',
                unsafe_allow_html=True,
            )
            st.markdown(report_md)
            st.markdown("</div>", unsafe_allow_html=True)

            # Download button
            st.download_button(
                label="⬇️  Download PRISMA_INSTRUCTIONS.md",
                data=report_md,
                file_name="PRISMA_INSTRUCTIONS.md",
                mime="text/markdown",
            )
        except Exception as exc:
            st.error(f"Failed to read optimization report: {exc}")
    else:
        st.warning(
            "No `PRISMA_INSTRUCTIONS.md` was generated.  "
            "Check the phase logs above for errors."
        )

    # ── Raw JSON artifacts (collapsible) ──────────────────────────────────
    with st.expander("🔬 Raw Phase Artifacts (JSON)", expanded=False):
        tab1, tab2, tab3 = st.tabs(["Phase 1 Output", "Phase 2 Output", "Phase 3 Output"])
        with tab1:
            d = _read_json(PHASE1_OUTPUT)
            st.json(d if d else {"status": "not available"})
        with tab2:
            d = _read_json(PHASE2_OUTPUT)
            st.json(d if d else {"status": "not available"})
        with tab3:
            d = _read_json(PHASE3_OUTPUT)
            st.json(d if d else {"status": "not available"})

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
