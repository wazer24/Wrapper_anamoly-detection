#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  Phase 1 — The AI Diagnostician (Gemini-Powered)
=============================================================================
  Uses the google-genai SDK to analyze intercepted slow queries,
  schema context, and EXPLAIN plans. Outputs a structured JSON
  diagnosis with hypotheses for downstream phases.

  Prerequisites:
    pip install -U google-genai pydantic

  Environment:
    GEMINI_API_KEY  — your Google AI / Gemini API key
=============================================================================
"""

import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Force UTF-8 on Windows
# ---------------------------------------------------------------------------
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Dependency guard
# ---------------------------------------------------------------------------
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("[FATAL] google-genai not found. Install with:  pip install -U google-genai")
    sys.exit(1)

try:
    from pydantic import BaseModel, Field
except ImportError:
    print("[FATAL] pydantic not found. Install with:  pip install pydantic")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ARTIFACTS_DIR = Path(__file__).parent
INPUT_FILE = ARTIFACTS_DIR / "slow_query_input.json"
OUTPUT_FILE = ARTIFACTS_DIR / "phase_1_output.json"
SCHEMA_FILE = ARTIFACTS_DIR.parent / "prisma" / "schema.prisma"

MODEL_NAME = "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# Pydantic response schema  (used by Gemini structured output)
# ---------------------------------------------------------------------------
class Hypothesis(BaseModel):
    id: str = Field(description="Hypothesis identifier, e.g. H1, H2, H3")
    label: str = Field(description="Short human-readable label")
    type: str = Field(description="One of: INDEX_BTREE, INDEX_GIN, ORM_EAGER_LOAD, ORM_SELECTIVE_LOAD, DATALOADER_BATCH, CODE_REWRITE")
    rationale: str = Field(description="Detailed technical explanation of why this fix will work")
    fix_type: str = Field(description="One of: MIGRATION, CODE_REWRITE")
    expected_impact: str = Field(description="Estimated performance impact description")
    affected_layer: str = Field(description="One of: database, application")
    sql_equivalent: str = Field(description="The raw SQL this fix is equivalent to, or N/A")


class Diagnosis(BaseModel):
    root_cause_category: str = Field(description="One of: MISSING_INDEX, APPLICATION_LAYER_N_PLUS_1, FULL_TABLE_SCAN, SUBOPTIMAL_JOIN")
    is_database_index_problem: bool = Field(description="True if the fix requires a database index change")
    primary_bottleneck: str = Field(description="Detailed description of the primary bottleneck")
    secondary_bottleneck: str = Field(description="Detailed description of secondary issues, if any")
    estimated_baseline_execution_time_ms: float = Field(description="Estimated baseline latency in milliseconds")
    database_verdict: str = Field(description="Summary verdict on database health")
    required_fix_layer: str = Field(description="One of: DATABASE, APPLICATION_CODE, BOTH")


class WinningHypothesis(BaseModel):
    id: str
    label: str
    fix_type: str
    requires_database_migration: bool
    requires_index_change: bool
    projected_latency_ms: float
    latency_reduction_pct: float


class Phase1Output(BaseModel):
    diagnostician_version: str = Field(default="1.0.0")
    analysis_timestamp: str
    raw_query: str
    interception_source: str = Field(default="prisma_middleware")
    query_count_intercepted: int
    diagnosis: Diagnosis
    hypotheses: list[Hypothesis]
    winning_hypothesis: WinningHypothesis


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def log_info(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [PHASE-1] [INFO]  {msg}", flush=True)


def log_warn(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [PHASE-1] [WARN]  {msg}", flush=True)


def log_error(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [PHASE-1] [ERROR] {msg}", flush=True)


def read_schema() -> str:
    """Read the Prisma schema file for context."""
    if SCHEMA_FILE.exists():
        return SCHEMA_FILE.read_text(encoding="utf-8")
    log_warn(f"Schema file not found at {SCHEMA_FILE}")
    return "Schema not available."


def read_input() -> dict:
    """Read the slow query input payload."""
    if INPUT_FILE.exists():
        return json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    # Fallback: check for plain text input
    txt_file = ARTIFACTS_DIR / "slow_query_input.txt"
    if txt_file.exists():
        raw = txt_file.read_text(encoding="utf-8").strip()
        return {
            "raw_query": raw,
            "query_count": 1,
            "baseline_explain": "Not available — text input only.",
            "intercepted_code": "Not available — text input only."
        }

    log_error("No input file found! Expected slow_query_input.json or slow_query_input.txt")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main AI Diagnostician
# ---------------------------------------------------------------------------
def run_diagnostician():
    log_info("=" * 60)
    log_info("Phase 1 — AI Diagnostician Starting")
    log_info("=" * 60)

    # 1. Validate API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log_error("GEMINI_API_KEY is not set. Export it before running.")
        sys.exit(1)

    # 2. Read inputs
    log_info("Reading slow query input...")
    query_input = read_input()
    log_info(f"  Query count: {query_input.get('query_count', 'unknown')}")

    log_info("Reading Prisma schema for context...")
    schema_context = read_schema()
    log_info(f"  Schema length: {len(schema_context)} chars")

    # 3. Build the LLM prompt
    prompt = f"""You are an expert PostgreSQL Database Administrator and Node.js/Prisma backend architect.

A slow query was intercepted in production by our Prisma middleware. Analyze the following inputs and produce a structured diagnosis.

## Intercepted Slow Query Payload
```json
{json.dumps(query_input, indent=2)}
```

## Current Prisma Schema
```prisma
{schema_context}
```

## Your Task
1. Determine the ROOT CAUSE of the slowness. Is it a missing database index? Or is it an application-layer anti-pattern (N+1 queries, missing eager loading, etc.)?
2. Propose 2-3 concrete hypotheses to fix it, ranked by expected impact.
3. Select the single winning hypothesis.
4. Be specific: include exact SQL equivalents, Prisma code rewrites, or index definitions.
5. If the problem is N+1 queries, DO NOT recommend database index changes — instead recommend Prisma `include`, `select`, or DataLoader batching patterns.
6. Estimate the baseline and projected latency.
"""

    # 4. Call Gemini
    log_info(f"Calling Gemini ({MODEL_NAME}) for diagnosis...")
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Phase1Output,
            temperature=0.2,
        ),
    )

    log_info("Gemini response received. Parsing structured output...")

    # 5. Parse and validate
    try:
        result = json.loads(response.text)
    except json.JSONDecodeError:
        log_error("Failed to parse Gemini response as JSON.")
        log_error(f"Raw response: {response.text[:500]}")
        sys.exit(1)

    # 6. Write output
    OUTPUT_FILE.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    log_info(f"Diagnosis written to: {OUTPUT_FILE}")

    # 7. Summary
    diag = result.get("diagnosis", {})
    winner = result.get("winning_hypothesis", {})
    log_info("-" * 60)
    log_info(f"Root cause: {diag.get('root_cause_category', '?')}")
    log_info(f"Is DB index problem: {diag.get('is_database_index_problem', '?')}")
    log_info(f"Fix layer: {diag.get('required_fix_layer', '?')}")
    log_info(f"Winning fix: {winner.get('label', '?')}")
    log_info(f"Projected latency: {winner.get('projected_latency_ms', '?')}ms")
    log_info(f"Reduction: {winner.get('latency_reduction_pct', '?')}%")
    log_info("-" * 60)
    log_info("[OK] Phase 1 complete.")

    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_diagnostician()
