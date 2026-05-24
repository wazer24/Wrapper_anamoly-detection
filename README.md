# AI-Powered Database Optimization Pipeline 🚀

This repository implements an automated, autonomous database optimization pipeline designed for Node.js / Prisma (MERN stack) applications running on PostgreSQL. 

It proactively detects slow database queries, uses AI to diagnose whether the root cause is a missing index or an application-layer anti-pattern (like N+1 queries), and automatically generates the exact code or schema fix needed to resolve it.

## 🧠 How It Works: The 5 Phases

The pipeline is broken down into five distinct phases that simulate the workflow of a real Site Reliability Engineer (SRE) and Database Administrator (DBA).

### Phase 1: The Diagnostician (Input Analysis)
*Responsible for ingesting slow queries and diagnosing the problem.*
- When a slow query is detected, it captures the raw SQL, EXPLAIN plan, and Prisma schema context.
- Diagnoses if the bottleneck is due to missing indexes or application-level inefficient patterns (e.g., N+1 query cascades).
- Proposes hypotheses (e.g., "Add B-Tree Index" or "Use Prisma \`include\`").

### Phase 2: The HypoPG Evaluator (`run_phase_2.py`)
*Responsible for safely testing hypotheses without altering production.*
- If an index is proposed, it uses the PostgreSQL `hypopg` extension to create "hypothetical" indexes in memory.
- Re-runs the `EXPLAIN` plan to prove mathematically whether the proposed index reduces query cost and by how much.
- Selects the winning hypothesis (or bypasses if it's an application code issue).

### Phase 3: The ORM Translator (`run_phase_3.py`)
*Responsible for translating raw SQL fixes into Prisma-native code.*
- Takes the mathematically proven raw SQL fix (or code fix instructions) and translates it.
- Generates `PRISMA_INSTRUCTIONS.md` to show developers exactly how to rewrite their Prisma query or how to update their `schema.prisma` file.

### Phase 4: The CI/CD Interceptor (`src/prisma-slow-query-extension.ts` & `.github/workflows`)
*Responsible for hooking into the application at development/testing time.*
- A custom Prisma Client Extension (`$extends`) intercepts every query.
- Measures execution time using `performance.now()`.
- If a query is slow (e.g., >500ms), it automatically synchronously triggers the AI pipeline.
- Integrates with GitHub Actions to post the AI's optimization recommendations directly as Pull Request comments.

### Phase 5: The Always-On DBA Daemon (`always_on_dba.py`)
*Responsible for production monitoring.*
- A standalone Python background service that polls the PostgreSQL `pg_stat_statements` view continuously.
- Deduplicates slow queries using a 24-hour cache so the pipeline isn't spammed.
- When it finds anomalies, it writes to `slow_query_input.txt` and triggers the AI optimization pipeline.
- Capable of sending alerts to Slack/Discord via webhooks.

---

## 🛠️ Tech Stack
- **Database**: PostgreSQL with `pg_stat_statements` and `hypopg` extensions
- **Application ORM**: Prisma Client v5.22.0
- **Automation / Orchestration**: Python 3, Node.js (TypeScript)
- **CI/CD**: GitHub Actions

---

## 🚧 What Part is Left to Add?

While the pipeline logic and orchestration are fully established, there are a few missing pieces to make it a fully plug-and-play product:

1. **Phase 1 Implementation (`run_phase_1.py`)**
   - **Current State:** The Phase 1 output (`phase_1_output.json`) is currently mocked/simulated for testing. 
   - **To Add:** Implement `run_phase_1.py` using an LLM API (e.g. Gemini or Claude) to dynamically parse the schema and raw SQL, build the `EXPLAIN` output, and dynamically generate the hypotheses.

2. **The Dummy API Application**
   - **Current State:** The repo contains the Prisma middleware and schema, but lacks a running API.
   - **To Add:** A simple Express.js or Fastify server that actually uses the Prisma client. This will allow us to hit HTTP endpoints (like `/api/posts`) to naturally trigger the N+1 queries or slow lookups and see the pipeline run in real-time.

3. **LLM Integration for Phase 2 & 3**
   - **Current State:** Python scripts heavily use static logic or simulated JSON inputs.
   - **To Add:** Connect `run_phase_2.py` and `run_phase_3.py` directly to the LLM to make the translation steps truly autonomous for unseen schemas.

4. **Automated Application of Fixes**
   - **Current State:** The pipeline provides developer instructions (`PRISMA_INSTRUCTIONS.md`).
   - **To Add:** Allow the AI to automatically run `prisma migrate` or rewrite the TypeScript files using AST manipulation if the confidence score is high enough.

---

## 🧪 Running the Local Prototype

With the recent completion of the live `run_phase_1.py` script using the `google-genai` SDK and the dummy Express API (`server.ts`), you can now run the AI pipeline locally!

### Prerequisites

1. **Python Dependencies**:
   Install the necessary AI and data validation libraries:
   ```bash
   pip install -U google-genai pydantic
   ```
2. **Node.js Setup**:
   Ensure you have installed standard Prisma and Express dependencies (`npm install`).
3. **Environment Variables**:
   Export your Gemini API key in your terminal before running the pipeline:
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```
   *(On Windows PowerShell, use `$env:GEMINI_API_KEY="your_api_key_here"`)*

### Execution Flow

1. **Start the Server**: 
   Launch the dummy Express API by running:
   ```bash
   npx ts-node server.ts
   ```
2. **Trigger the Bottleneck**:
   Send a request to the `/api/posts` endpoint (e.g., via `curl` or your browser). This route contains an intentional N+1 database bottleneck.
3. **Interception & AI Diagnosis**:
   - Our Prisma middleware automatically intercepts this inefficient query sequence.
   - It measures the latency and drops a `slow_query_input.json` payload containing the execution context.
   - The middleware then automatically executes the Python agent (`run_phase_1.py`).
4. **View the Results**:
   The agent's AI-generated diagnosis and resolution plan will immediately appear in the `optimization_artifacts/phase_1_output.json` file.
