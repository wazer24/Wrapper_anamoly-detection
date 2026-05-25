# AI-Powered Database Optimization Pipeline 🚀

This repository implements an automated, autonomous database optimization pipeline designed for Node.js / Prisma (MERN stack) applications running on PostgreSQL. 

It proactively detects slow database queries, uses AI to diagnose whether the root cause is a missing index or an application-layer anti-pattern (like N+1 queries), and automatically generates the exact code or schema fix needed to resolve it.

## 🧠 How It Works: The 5 Phases

The pipeline is broken down into five distinct phases that simulate the workflow of a real Site Reliability Engineer (SRE) and Database Administrator (DBA).

### Phase 1: The Diagnostician (`run_phase_1.py` — Gemini AI)
*Responsible for ingesting slow queries and diagnosing the problem.*
- Uses the `google-genai` SDK to call Gemini 2.5 Flash with structured (Pydantic) output.
- Reads the intercepted query payload + Prisma schema context.
- Diagnoses if the bottleneck is due to missing indexes or application-level inefficient patterns (e.g., N+1 query cascades).
- Proposes 2-3 hypotheses ranked by impact, and selects a winning fix.

### Phase 2: The HypoPG Evaluator (`run_phase_2.py`)
*Responsible for safely testing hypotheses without altering production.*
- If an index is proposed, it uses the PostgreSQL `hypopg` extension to create "hypothetical" indexes in memory.
- Re-runs the `EXPLAIN` plan to prove mathematically whether the proposed index reduces query cost and by how much.
- Selects the winning hypothesis (or bypasses if it's an application code issue).

### Phase 3: The ORM Translator (`run_phase_3.py`)
*Responsible for translating raw SQL fixes into Prisma-native code.*
- Takes the mathematically proven raw SQL fix (or code fix instructions) and translates it.
- Generates `PRISMA_INSTRUCTIONS.md` to show developers exactly how to rewrite their Prisma query or how to update their `schema.prisma` file.

### Phase 4: The CI/CD Interceptor (`server.ts` & `.github/workflows`)
*Responsible for hooking into the application at development/testing time.*
- A custom Prisma Client Extension (`$extends`) intercepts every query inside the Express demo server.
- Measures execution time using `performance.now()`.
- If a query is slow (e.g., >500ms), it writes `slow_query_input.json` and automatically triggers the AI pipeline.
- Integrates with GitHub Actions to post the AI's optimization recommendations directly as Pull Request comments.

### Phase 5: The Always-On DBA Daemon (`always_on_dba.py`)
*Responsible for production monitoring.*
- A standalone Python background service that polls the PostgreSQL `pg_stat_statements` view continuously.
- Deduplicates slow queries using a 24-hour cache so the pipeline isn't spammed.
- When it finds anomalies, it writes to `slow_query_input.txt` and triggers the AI optimization pipeline.
- Capable of sending alerts to Slack/Discord via webhooks.

---

## 🛠️ Tech Stack
- **AI**: Google Gemini 2.5 Flash via `google-genai` SDK with Pydantic structured output
- **Database**: PostgreSQL with `pg_stat_statements` and `hypopg` extensions
- **Application ORM**: Prisma Client v5.22.0
- **Automation / Orchestration**: Python 3, Node.js (TypeScript)
- **CI/CD**: GitHub Actions (autonomous agent workflow)

---

## 🚧 What's Left to Add?

The core pipeline and agent infrastructure are now complete. Remaining stretch goals:

1. **LLM Integration for Phase 2 & 3**
   - **Current State:** Python scripts use deterministic logic and read from Phase 1 JSON.
   - **Stretch:** Connect `run_phase_2.py` and `run_phase_3.py` directly to the LLM for truly autonomous diagnosis on unseen schemas.

2. **Automated Application of Fixes**
   - **Current State:** The pipeline generates developer instructions (`PRISMA_INSTRUCTIONS.md`).
   - **Stretch:** Auto-apply fixes via `prisma migrate` or AST-based TypeScript rewriting when confidence exceeds a threshold.

3. **Production Daemon Deployment**
   - **Current State:** `always_on_dba.py` runs locally.
   - **Stretch:** Package as a Docker sidecar or Kubernetes CronJob for real production monitoring.

---

## 🧪 Running the Local Prototype

With the live `run_phase_1.py` script (powered by `google-genai` SDK) and the dummy Express API (`server.ts`), you can run the full AI pipeline locally.

### Prerequisites

1. **Python Dependencies**:
   ```bash
   pip install -U google-genai pydantic psycopg2-binary tabulate colorama requests
   ```
2. **Node.js Dependencies**:
   ```bash
   npm install
   npm install express @types/express ts-node typescript
   npx prisma generate
   ```
3. **Environment Variables**:
   ```bash
   # Linux / macOS
   export GEMINI_API_KEY="your_api_key_here"
   export DATABASE_URL="postgresql://postgres@localhost:5432/postgres"

   # Windows PowerShell
   $env:GEMINI_API_KEY="your_api_key_here"
   $env:DATABASE_URL="postgresql://postgres@localhost:5432/postgres"
   ```

### Execution Flow

1. **Start the Server**:
   ```bash
   npx ts-node server.ts
   ```
2. **Trigger the Bottleneck**:
   ```bash
   curl http://localhost:3000/api/posts
   ```
   This route executes an intentional N+1 anti-pattern (1 + N queries).

3. **Interception & AI Diagnosis**:
   - The Prisma middleware intercepts the slow query sequence
   - Writes `slow_query_input.json` with the execution context
   - Automatically triggers `run_phase_1.py` → `run_phase_2.py` → `run_phase_3.py`

4. **View the Results**:
   ```bash
   cat optimization_artifacts/phase_1_output.json   # AI diagnosis
   cat optimization_artifacts/PRISMA_INSTRUCTIONS.md # Fix instructions
   ```

5. **Compare with the Fix**:
   ```bash
   curl http://localhost:3000/api/posts/optimized
   ```
   This route uses Prisma `include` (the AI-recommended fix) — single JOIN, no N+1.

---

## 🤖 GitHub Actions — Autonomous AI Agent Deployment

The pipeline runs as an **autonomous AI agent** inside GitHub Actions. Every Pull Request is automatically analyzed for database performance issues.

### Architecture

```
PR Opened / Updated
        │
        ▼
┌─────────────────────────────┐
│  Job 1: Static Analysis     │
│  Scan .ts/.js for N+1       │
│  anti-patterns (grep-based) │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│  Job 2: AI Diagnostician Pipeline           │
│                                             │
│  ┌─────────────┐   PostgreSQL 16 Service    │
│  │  Postgres    │◄─ pg_stat_statements      │
│  │  (sidecar)   │◄─ hypopg (hypothetical)   │
│  └──────┬──────┘                            │
│         │                                   │
│  ┌──────▼──────┐                            │
│  │ Phase 1     │  google-genai SDK          │
│  │ Gemini AI   │──► phase_1_output.json     │
│  └──────┬──────┘                            │
│         │                                   │
│  ┌──────▼──────┐                            │
│  │ Phase 2     │  HypoPG / simulation       │
│  │ Evaluator   │──► phase_2_output.json     │
│  └──────┬──────┘                            │
│         │                                   │
│  ┌──────▼──────┐                            │
│  │ Phase 3     │  ORM Translation           │
│  │ Translator  │──► PRISMA_INSTRUCTIONS.md  │
│  └──────┬──────┘                            │
│         │                                   │
│  ┌──────▼──────────────────────┐            │
│  │ Post Report to PR Comment   │            │
│  │ Upload Artifacts (30 days)  │            │
│  │ Write Job Summary           │            │
│  └─────────────────────────────┘            │
└─────────────────────────────────────────────┘
```

### Setup Instructions

1. **Add your Gemini API key as a GitHub Secret**:
   - Go to your repo → **Settings** → **Secrets and variables** → **Actions**
   - Click **New repository secret**
   - Name: `GEMINI_API_KEY`
   - Value: your Google AI API key

2. **That's it.** The workflow is already in `.github/workflows/ai-db-optimizer.yml`. It will run automatically on every PR to `main`.

3. **Manual trigger** (optional):
   - Go to **Actions** tab → **AI Database Optimizer CI/CD Interceptor** → **Run workflow**
   - Optionally paste a raw SQL query to analyze

### What the Agent Does on Every PR

| Step | What Happens |
|---|---|
| **Scan** | Greps your codebase for N+1 patterns (for-loop + findUnique, findMany without include) |
| **Boot Postgres** | Spins up a PostgreSQL 16 sidecar with `pg_stat_statements` and `hypopg` |
| **Seed Data** | Inserts 100 customers + 500 orders for realistic testing |
| **Phase 1** | Calls Gemini AI to diagnose the slow query root cause |
| **Phase 2** | Tests index hypotheses using HypoPG (or bypasses for code-level fixes) |
| **Phase 3** | Translates the winning fix into Prisma-native instructions |
| **Report** | Posts a rich Markdown report as a PR comment with diagnosis table + fix instructions |
| **Artifacts** | Uploads all JSON outputs as downloadable artifacts (retained 30 days) |

### Example PR Comment Output

The bot posts a comment like this on your PR:

> ## ⚡ AI Database Optimization Report
>
> @developer, the AI Database Optimizer has analyzed this PR.
>
> ### 🧠 AI Diagnosis (Phase 1 — Gemini)
> | Metric | Value |
> |---|---|
> | Root Cause | `APPLICATION_LAYER_N_PLUS_1` |
> | Is DB Index Problem | No |
> | Fix Layer | `APPLICATION_CODE` |
> | Winning Fix | Prisma `include` Eager Loading |
> | Projected Latency | 50ms |
> | Latency Reduction | 96% |
>
> ### 📋 Fix Instructions
> *(expandable section with full PRISMA_INSTRUCTIONS.md)*

---

## 📁 Project Structure

```
.
├── .github/workflows/
│   └── ai-db-optimizer.yml        # GitHub Actions autonomous agent
├── optimization_artifacts/
│   ├── run_phase_1.py             # Phase 1: AI Diagnostician (Gemini)
│   ├── run_phase_2.py             # Phase 2: HypoPG Evaluator
│   ├── run_phase_3.py             # Phase 3: ORM Translator
│   ├── phase_1_output.json        # AI diagnosis output
│   ├── phase_2_output.json        # Index evaluation output
│   ├── phase_3_output.json        # Translation output
│   ├── PRISMA_INSTRUCTIONS.md     # Developer-facing fix guide
│   ├── apply_index_migration.sql  # Raw SQL migration
│   └── slow_query_input.json      # Intercepted query payload
├── prisma/
│   └── schema.prisma              # Prisma schema with optimized indexes
├── src/
│   ├── prisma-slow-query-extension.ts  # Prisma middleware interceptor
│   └── prisma-slow-query-extension.js  # Compiled JS version
├── server.ts                      # Demo Express API (N+1 bait + fix)
├── always_on_dba.py               # Phase 5: Production monitoring daemon
├── test-middleware.js              # Local test harness
└── package.json
```
