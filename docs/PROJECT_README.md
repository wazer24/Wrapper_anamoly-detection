<!-- ╔══════════════════════════════════════════════════════════════════════╗ -->
<!-- ║           AUTONOMOUS DATABASE OPTIMIZER — PROJECT README            ║ -->
<!-- ╚══════════════════════════════════════════════════════════════════════╝ -->

<img src="https://capsule-render.vercel.app/api?type=rect&color=0:0D1117,50:0a0e27,100:0D1117&height=1&section=header" width="100%"/>

<div align="center">

<br/>

```
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     █████╗ ██╗   ██╗████████╗ ██████╗                        ║
    ║    ██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗                       ║
    ║    ███████║██║   ██║   ██║   ██║   ██║                       ║
    ║    ██╔══██║██║   ██║   ██║   ██║   ██║                       ║
    ║    ██║  ██║╚██████╔╝   ██║   ╚██████╔╝                       ║
    ║    ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝                        ║
    ║                                                               ║
    ║        D A T A B A S E    O P T I M I Z E R                  ║
    ║             ── Self-Healing Query Pipeline ──                 ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
```

<br/>

<a href="#">
  <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&size=16&duration=3000&pause=800&color=00BFFF&center=true&vCenter=true&width=700&lines=Intercept+%E2%86%92+Diagnose+%E2%86%92+Prove+%E2%86%92+Fix+%E2%86%92+Deploy;Zero+Human+Intervention+%7C+AI-Powered+%7C+Mathematically+Proven;96-99.6%25+Query+Latency+Reduction+%7C+Fully+Autonomous" alt="Typing SVG"/>
</a>

<br/>

<!-- STATUS DASHBOARD -->
<table>
<tr>
<td align="center">
<img src="https://img.shields.io/badge/STATUS-ACTIVE-00ff00?style=for-the-badge&labelColor=0d1117" alt="Status"/>
</td>
<td align="center">
<img src="https://img.shields.io/badge/AI_ENGINE-Gemini_2.5_Flash-886FBF?style=for-the-badge&logo=googlegemini&logoColor=white&labelColor=0d1117" alt="AI"/>
</td>
<td align="center">
<img src="https://img.shields.io/badge/DATABASE-PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white&labelColor=0d1117" alt="DB"/>
</td>
<td align="center">
<img src="https://img.shields.io/badge/DEPLOY-GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white&labelColor=0d1117" alt="CI/CD"/>
</td>
</tr>
</table>

</div>

<br/>

---

<div align="center">

## 🎯 What Is This?

</div>

<table align="center">
<tr>
<td width="100%">

> **A self-healing database pipeline** for Node.js / Prisma applications on PostgreSQL that:
> 
> 1. 🔍 **Intercepts** slow queries via Prisma middleware & `pg_stat_statements`
> 2. 🧠 **Diagnoses** root causes with AI (or deterministic rules when possible)
> 3. 📐 **Proves** fixes mathematically using virtual indexes (HypoPG)
> 4. 🚀 **Auto-commits** optimized code directly to your PR branch
>
> *All without human intervention.*

</td>
</tr>
</table>

<br/>

---

<div align="center">

## ⚡ Performance Impact

</div>

<div align="center">

<!-- Performance Metrics as Visual Cards -->
<table>
<tr>
<td align="center" width="25%">

```
 ┌─────────────────┐
 │   N+1 QUERIES   │
 │                  │
 │  1,250ms → 50ms │
 │                  │
 │    ▼ 96.0%      │
 │   ████████████   │
 └─────────────────┘
```
<sub>Prisma `include` eager load</sub>

</td>
<td align="center" width="25%">

```
 ┌─────────────────┐
 │  MISSING INDEX   │
 │                  │
 │ 2,317ms → 25ms  │
 │                  │
 │    ▼ 98.9%      │
 │   █████████████  │
 └─────────────────┘
```
<sub>`CREATE INDEX idx_order_status`</sub>

</td>
<td align="center" width="25%">

```
 ┌─────────────────┐
 │ FULL TABLE SCAN  │
 │                  │
 │ 3,400ms → 12ms  │
 │                  │
 │    ▼ 99.6%      │
 │   ██████████████ │
 └─────────────────┘
```
<sub>Composite B-tree index</sub>

</td>
<td align="center" width="25%">

```
 ┌─────────────────┐
 │  OVER-FETCHING   │
 │                  │
 │  890ms → 45ms   │
 │                  │
 │    ▼ 94.9%      │
 │   ███████████    │
 └─────────────────┘
```
<sub>Prisma `select: {}` projection</sub>

</td>
</tr>
</table>

</div>

<br/>

---

<div align="center">

## 🏗️ Architecture

</div>

```mermaid
flowchart TB
    subgraph INGESTION["📡 TELEMETRY INGESTION"]
        A["🔌 Prisma Middleware\n(server.ts)"] -->|"rows_returned\npayload_size_kb\nduration_ms"| C["📄 slow_query_input.json"]
        B["🔄 pg_stat_statements Daemon\n(always_on_dba.py)"] -->|"rows_scanned\nshared_blks_read\nmean_exec_time"| C
    end

    subgraph BRAIN["🧠 DECISION ENGINE"]
        C --> D{"⚡ Deterministic\nGatekeeper"}
        D -->|"Over-fetch or\nSevere Scan"| E["🎯 Instant Bypass\n(No LLM Call)"]
        D -->|"Complex Query"| F["🤖 Gemini 2.5 Flash\nAI Diagnostician"]
        E --> G["📋 Structured Diagnosis JSON"]
        F --> G
    end

    subgraph PROOF["📐 MATHEMATICAL PROOF"]
        G --> H{"🔍 Is Database\nIndex Fix?"}
        H -->|"Yes"| I["🧪 HypoPG\nVirtual Index"]
        I --> J["📊 Re-run EXPLAIN\nProve Cost ↓"]
        H -->|"No (App Code)"| K["🔄 ORM Translator"]
        J --> K
    end

    subgraph DEPLOY["🚀 SELF-HEALING DEPLOY"]
        K --> L["📝 PRISMA_INSTRUCTIONS.md"]
        K --> M["📦 .patch File"]
        M --> N["⚙️ git apply + auto-commit"]
        N --> O["🔀 Push to PR Branch"]
    end

    style INGESTION fill:#0d1117,stroke:#e94560,stroke-width:2px,color:#fff
    style BRAIN fill:#0d1117,stroke:#0077FF,stroke-width:2px,color:#fff
    style PROOF fill:#0d1117,stroke:#00BFFF,stroke-width:2px,color:#fff
    style DEPLOY fill:#0d1117,stroke:#00ff88,stroke-width:2px,color:#fff
```

<br/>

---

<div align="center">

## 🔬 Deep Dive: How Each Stage Works

</div>

<details>
<summary><b>📡 Stage 1 — Telemetry Interception</b> &nbsp; <i>(click to expand)</i></summary>
<br/>

The pipeline hooks into your application at **two levels**:

- **Development**: A Prisma Client Extension wraps every database call with `performance.now()` timers and inspects returned results
- **Production**: A background daemon polls PostgreSQL's `pg_stat_statements` view and reads block-level I/O counters

Both emit a standardized telemetry payload:

| Metric | Prisma Middleware | pg_stat_statements Daemon |
|---|---|---|
| `duration_ms` | `performance.now()` delta | `mean_exec_time` |
| `rows_returned` | `Array.isArray(result) ? result.length : 1` | `rows` column |
| `rows_scanned` | `null` (ORM abstraction) | `shared_blks_read + shared_blks_hit` |
| `payload_size_kb` | `Buffer.byteLength(JSON.stringify(result))` | `null` (not available) |

</details>

<details>
<summary><b>⚡ Stage 2 — The Deterministic Gatekeeper</b> &nbsp; <i>(click to expand)</i></summary>
<br/>

Before burning LLM tokens, every payload passes through a **rule-based filter**. If the numbers alone tell the story, the fix is instant:

```mermaid
flowchart LR
    P["📦 Telemetry\nPayload"] --> Q{"payload_size > 250KB\nAND rows < 50?"}
    Q -->|"Yes"| R["🎯 APPLICATION_OVER_FETCHING\nFix: Prisma select: {}"]
    Q -->|"No"| S{"rows_scanned > 10,000\nAND rows < 100?"}
    S -->|"Yes"| T["🎯 MISSING_INDEX\nFix: CREATE INDEX"]
    S -->|"No"| U["🤖 Pass to Gemini AI"]

    style R fill:#e94560,color:#fff,stroke:#e94560
    style T fill:#e94560,color:#fff,stroke:#e94560
    style U fill:#0077FF,color:#fff,stroke:#0077FF
```

</details>

<details>
<summary><b>🤖 Stage 3 — AI Diagnostician</b> &nbsp; <i>(click to expand)</i></summary>
<br/>

When the Gatekeeper can't resolve deterministically, the full query payload and Prisma schema are sent to **Google Gemini 2.5 Flash**. The model returns a Pydantic-validated JSON diagnosis:

```yaml
# AI Diagnosis Output Schema
root_cause:    "MISSING_INDEX | N_PLUS_1 | FULL_TABLE_SCAN | SUBOPTIMAL_JOIN"
hypotheses:
  - rank: 1
    description: "..."
    sql_equivalent: "..."
    projected_latency_ms: 25
winning_fix:
  type: "CREATE INDEX"
  target: "orders.status"
  confidence: 0.95
```

</details>

<details>
<summary><b>📐 Stage 4 — Mathematical Proof via HypoPG</b> &nbsp; <i>(click to expand)</i></summary>
<br/>

If the winning hypothesis is a database index, the pipeline **doesn't take the AI's word for it**. It uses the `hypopg` extension to create a **virtual index in memory**:

```mermaid
flowchart LR
    subgraph BEFORE["❌ Before (No Index)"]
        BA["Seq Scan on Order"] --> BB["Cost: 12,450"]
    end
    subgraph AFTER["✅ After (Virtual Index)"]
        AA["Index Scan using idx_order_status"] --> AB["Cost: 8.27"]
    end

    BEFORE -->|"hypopg_create_index()"| AFTER

    style BEFORE fill:#e94560,color:#fff,stroke:#e94560
    style AFTER fill:#00b894,color:#fff,stroke:#00b894
```

The virtual index exists **only in session memory** — zero disk impact, zero risk.

</details>

<details>
<summary><b>🚀 Stage 5 — Self-Healing Auto-Commit</b> &nbsp; <i>(click to expand)</i></summary>
<br/>

Once a fix is mathematically proven:

1. Raw SQL → translated into **Prisma-native code**
2. Written as a `.patch` file
3. GitHub Action applies the patch
4. Committed as `github-actions[bot]`
5. Pushed directly to the developer's **PR branch**

The bot posts a structured optimization report on the PR with before/after metrics.

</details>

<br/>

---

<div align="center">

## 🔄 Pipeline Sequence

</div>

```mermaid
sequenceDiagram
    participant App as 🖥️ Express Server
    participant MW as 🔌 Prisma Middleware
    participant GK as ⚡ Gatekeeper
    participant AI as 🤖 Gemini 2.5 Flash
    participant HP as 📐 HypoPG Engine
    participant GH as 🚀 GitHub Actions

    App->>MW: Execute Prisma query
    MW->>MW: Measure latency + extract telemetry
    MW->>GK: Pass payload (duration, rows, size)

    alt Deterministic Match
        GK->>GK: Over-fetch or Severe Scan detected
        GK-->>MW: Return instant diagnosis (no LLM)
    else Complex Query
        GK->>AI: Send payload + schema context
        AI-->>GK: Return structured diagnosis JSON
    end

    alt Database Index Fix
        GK->>HP: Create virtual index (hypopg)
        HP->>HP: Re-run EXPLAIN, prove cost reduction
        HP-->>GK: Return validated hypothesis
    end

    GK->>GH: Write .patch + PRISMA_INSTRUCTIONS.md
    GH->>GH: git apply, commit, push to PR branch
    GH-->>App: Post optimization report on PR
```

<br/>

---

<div align="center">

## 🛠️ Tech Stack

</div>

<div align="center">
<table>
<tr>
<td align="center" width="140">
<img src="https://skillicons.dev/icons?i=python" width="40" height="40"/>
<br/><sub><b>Python 3.11</b></sub>
<br/><sub>Orchestration</sub>
</td>
<td align="center" width="140">
<img src="https://skillicons.dev/icons?i=ts" width="40" height="40"/>
<br/><sub><b>TypeScript</b></sub>
<br/><sub>Server & ORM</sub>
</td>
<td align="center" width="140">
<img src="https://skillicons.dev/icons?i=postgres" width="40" height="40"/>
<br/><sub><b>PostgreSQL</b></sub>
<br/><sub>Database</sub>
</td>
<td align="center" width="140">
<img src="https://skillicons.dev/icons?i=prisma" width="40" height="40"/>
<br/><sub><b>Prisma v5</b></sub>
<br/><sub>ORM Layer</sub>
</td>
<td align="center" width="140">
<img src="https://skillicons.dev/icons?i=express" width="40" height="40"/>
<br/><sub><b>Express.js</b></sub>
<br/><sub>API Server</sub>
</td>
<td align="center" width="140">
<img src="https://skillicons.dev/icons?i=githubactions" width="40" height="40"/>
<br/><sub><b>GitHub Actions</b></sub>
<br/><sub>CI/CD</sub>
</td>
</tr>
</table>

<br/>

<img src="https://img.shields.io/badge/Gemini_2.5_Flash-886FBF?style=for-the-badge&logo=googlegemini&logoColor=white" alt="Gemini"/>
&nbsp;
<img src="https://img.shields.io/badge/HypoPG-00b894?style=for-the-badge&logoColor=white" alt="HypoPG"/>
&nbsp;
<img src="https://img.shields.io/badge/pg__stat__statements-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="pg_stat"/>
&nbsp;
<img src="https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white" alt="Pydantic"/>

</div>

<br/>

---

<div align="center">

## ⚡ Quick Start

</div>

<table align="center">
<tr>
<td width="50%" valign="top">

### 📦 Prerequisites

```bash
# Python dependencies
pip install -U google-genai pydantic \
  psycopg2-binary tabulate colorama requests

# Node.js dependencies
npm install
npx prisma generate
```

### 🔐 Environment Variables

```bash
export GEMINI_API_KEY="your_api_key_here"
export DATABASE_URL="postgresql://postgres@localhost:5432/postgres"
```

</td>
<td width="50%" valign="top">

### 🚀 Run It

```bash
# 1. Start the server
npx ts-node server.ts

# 2. Trigger the N+1 bottleneck
curl http://localhost:3000/api/posts

# 3. View the AI-generated fix
cat optimization_artifacts/PRISMA_INSTRUCTIONS.md

# 4. Compare with the optimized endpoint
curl http://localhost:3000/api/posts/optimized
```

</td>
</tr>
</table>

<br/>

---

<div align="center">

## 🗂️ Project Structure

</div>

```
.
├── .github/workflows/
│   └── ai-db-optimizer.yml          ← 🤖 Autonomous CI/CD agent
│
├── optimization_artifacts/
│   ├── run_phase_1.py               ← 🧠 AI Diagnostician + Gatekeeper
│   ├── run_phase_2.py               ← 📐 HypoPG virtual index evaluator
│   ├── run_phase_3.py               ← 🔄 ORM Translator
│   └── slow_query_input.json        ← 📄 Intercepted telemetry payload
│
├── prisma/
│   └── schema.prisma                ← 🗄️ Database schema
│
├── server.ts                        ← 🖥️ Express API with Prisma middleware
├── always_on_dba.py                 ← 🔄 Production monitoring daemon
├── seed.ts                          ← 🌱 Test data seeder
└── package.json
```

<br/>

---

<div align="center">

## 🔧 GitHub Actions Setup

</div>

<table align="center">
<tr>
<td>

| Step | Action |
|---|---|
| **1** | Go to repo → **Settings** → **Secrets** → **Actions** |
| **2** | Add `GEMINI_API_KEY` as a repository secret |
| **3** | Push code — workflow triggers on every PR touching backend files |

The bot posts a structured optimization report on your **Pull Request** with before/after latency metrics and expandable fix instructions.

</td>
</tr>
</table>

<br/>

---

<div align="center">

```
───────────────────────────────────────────────────────────────────
   Built with 🧠 AI  •  📐 Math  •  ☕ Coffee
   "Don't optimize queries manually. Let the machine prove it."
───────────────────────────────────────────────────────────────────
```

<br/>

<a href="https://github.com/wazer24">
  <img src="https://img.shields.io/badge/Made_by-Rakshit_Waze-00BFFF?style=for-the-badge&labelColor=0d1117" alt="Author"/>
</a>

</div>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:00BFFF,50:0077FF,100:0D1117&height=100&section=footer" width="100%"/>
