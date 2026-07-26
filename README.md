# Limier — AI-Powered AML Investigation Platform

<!--
  BANNER SPACE
  Replace the line below with your project banner image, e.g.:
  ![Limier Banner](./docs/banner.png)
-->
<p align="center">
 <img width="1774" height="887" alt="Image" src="https://github.com/user-attachments/assets/e897022c-5209-4547-9a02-f1c938260f3f" />
</p>

<p align="center">
  <b>An autonomous, explainable AI agent for anti-money laundering detection and investigation.</b>
</p>

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Screenshot](#screenshot)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Solution Approach](#solution-approach)
- [Dataset Information](#dataset-information)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Usage Examples](#usage-examples)
- [Data Sources](#data-sources)
- [Notes & Limitations](#notes--limitations)

---

## Problem Statement

<!--
  PROBLEM STATEMENT SPACE
  Paste the official hackathon problem statement text here, verbatim or
  lightly summarized. Suggested structure below — replace with your actual
  content.
-->

> **AI-Powered Suspicious Activity Detection**
>
> Financial institutions are required to run robust Anti-Money Laundering
> (AML) compliance programs, but traditional rule-based transaction
> monitoring systems generate a high volume of false positives, overwhelming
> compliance teams while sophisticated laundering techniques — structuring,
> smurfing, layering — continue to slip through.
>


---

## Screenshot

<!--
  SCREENSHOT SPACE
  Replace with an actual screenshot of the running dashboard, e.g.:
  ![Limier Dashboard](./docs/screenshot.png)
-->
<p align="center">
 <img width="1917" height="872" alt="Image" src="https://github.com/user-attachments/assets/1596d450-f694-4081-abbf-09581d8856c5" />
</p>

---

## Architecture

<!--
  ARCHITECTURE DIAGRAM SPACE
  Replace with a diagram showing: Frontend <-> FastAPI <-> (Rules Engine,
  Isolation Forest, XGBoost + SHAP, Hybrid Scorer) <-> LLM Agent (tool-calling
  loop) <-> SAR Generator. e.g.:
  ![Architecture Diagram](./docs/architecture.png)
-->
<p align="center">
      <img width="1024" height="1536" alt="Image" src="https://github.com/user-attachments/assets/0ab46e7a-b4ce-4a0c-940f-32ef7f2ae23b" />
</p>

At a high level, Limier is a **3-pillar hybrid detection engine** wrapped in
an autonomous LLM agent, sitting behind a FastAPI backend and a Next.js
dashboard:

---

## Tech Stack

**Frontend**
- Next.js 16 (App Router), React 19, TypeScript
- Tailwind CSS v4
- Framer Motion (animation), Recharts (data visualization)
- Radix UI primitives, lucide-react (icons), react-markdown

**Backend**
- FastAPI + Uvicorn (ASGI)
- Python 3.11
- Pandas, NumPy (data processing)
- Scikit-learn (Isolation Forest), XGBoost 1.7.6 (supervised classification)
- SHAP (SHapley Additive exPlanations) for explainable AI
- MLflow, Optuna, Joblib (experiment tracking, tuning, model persistence)
- Pytest (testing)

**AI Agent / LLM Layer**
- Native tool-calling (ReAct-style loop) — no LangChain/CrewAI
- Supports Groq (Llama 3), xAI (Grok), and OpenAI-compatible endpoints via
  the `openai` SDK as a universal client wrapper

**Infrastructure**
- Docker & Docker Compose (single-command startup for both services)
- python-dotenv for environment configuration

---

## Solution Approach

Limier avoids relying on a single black-box model. It combines three
independent detection methodologies — each contributing a different kind of
signal — into one final, fully explainable risk score:

1. **Deterministic Rules Engine** — catches known AML typologies (structuring,
   rapid cash-out, round-tripping, velocity spikes, dormant-then-active
   accounts, high-risk geography, round-number bias) with zero uncertainty.
   Thresholds are config-driven, not hardcoded, and every rule produces a
   human-readable reason string. A high-severity rule firing **overrides**
   the ML score and immediately elevates a customer to High Risk.

2. **Unsupervised ML (Isolation Forest)** — detects novel, previously unseen
   anomalies in the transaction feature space without needing labeled data,
   catching laundering patterns that don't match a known rule.

3. **Supervised ML (XGBoost) + SHAP** — learns from labeled synthetic fraud
   patterns and produces per-transaction SHAP feature attributions, so every
   ML-driven flag can be traced back to the specific features that drove it.

These three signals are combined by the **Hybrid Scorer**, which blends the
Isolation Forest and XGBoost scores, applies the deterministic overrides, and
filters out immaterial micro-transactions to reduce noise before final
classification.

On top of this scoring engine sits an **LLM investigation agent** that
dynamically parses natural language queries (e.g. *"Find structuring patterns
in the last 30 days"* or *"Is customer 4521 suspicious?"*) and selectively
invokes only the tools needed to answer — full EDA for broad queries, a
single lookup for entity-specific ones — rather than running a fixed
pipeline every time. The agent is grounded to cite real transaction IDs from
the dataset to prevent hallucination, and can trigger automated **Suspicious
Activity Report (SAR)** generation, translating triggered rules and SHAP
values into a professional, plain-English narrative.

---

## Dataset Information

Since real banking transaction data is private and cannot be used, Limier
generates a **realistic synthetic dataset at startup**:

- **Scale:** ~2,000 customers, ~211,000 transactions
- **Realism mechanics:**
  - Log-normal transaction amount distributions (heavy-tailed, matching real
    financial data)
  - Poisson-process transaction timing, biased toward business hours
  - 80% counterparty "stickiness" (simulating recurring rent/salary/grocery
    payments rather than a random network)
  - Mostly domestic (US) activity with a realistic long tail of cross-border
    transfers
- **Typology injection:** a small subset of customers have explicitly
  planted AML patterns (structuring, rapid cash-out, round-tripping,
  dormant-then-active) with ground-truth labels (`is_planted_suspicious`,
  `planted_pattern`) used strictly for model evaluation — these labels are
  hidden from the feature builder to prevent target leakage.

No real customer or transaction data is used anywhere in this project.

---

## Quick Start

**Prerequisites:** Docker Desktop installed and running. Nothing else — no
local Python, Node, or package installs required.

### 1. Set up environment variables

This submission's zip includes an `env-vars.txt` file at the project root
containing all required environment variables.

**Copy its contents exactly into a new `.env` file** in the project root:

```bash
# from the project root
cp env-vars.txt .env
```

*(On Windows PowerShell: `Copy-Item env-vars.txt .env`)*

No values need to be edited — the provided file is ready to use as-is. If an
LLM API key is left blank, the agent automatically runs in a rule-based
fallback mode and the application remains fully functional.

### 2. Build and run

From the project root:

```bash
docker compose up --build
```

This single command builds and starts both the backend (FastAPI) and
frontend (Next.js) containers.

### 3. Open the app

Once both containers report as healthy:

- **Frontend dashboard:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **Health check:** [http://localhost:8000/health](http://localhost:8000/health)
  → should return `{"status": "ok", "cached": true}`

Startup includes generating the synthetic dataset and pre-scoring all
~211,000 transactions, which completes in a matter of seconds and is logged
to the backend container's console.

### To stop

```bash
docker compose down
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `LLM_PROVIDER` | No | `groq`, `xai`, or `openai` — selects the LLM backend for the agent |
| `LLM_API_KEY` | No | API key for the selected provider. If left blank, the agent runs in rule-based fallback mode with no LLM calls |
| `LLM_MODEL` | No | Model name/ID to use with the selected provider |
| `NEXT_PUBLIC_API_URL` | Yes | Backend URL as seen by the frontend (default: `http://localhost:8000`) |

All of the above are pre-filled in `env-vars.txt` included with this
submission — simply copy it to `.env` as shown above.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Returns API health and cache status |
| `GET` | `/eda` | Exploratory data analysis: distributions, breakdowns, missing values |
| `GET` | `/customers/{customer_id}/risk` | Pre-computed risk profile for a single customer |
| `POST` | `/score` | Score raw transactions, or filter cached data by customer/date/pattern |
| `POST` / `GET` | `/api/agent/query` | Streaming (SSE) endpoint for the LLM investigation agent |

Full request/response schemas are documented via FastAPI's interactive docs,
available once the backend is running at:
[http://localhost:8000/docs](http://localhost:8000/docs)

---

## Project Structure

```
Limier/
├── backend/
│   ├── src/
│   │   ├── api/              # FastAPI app, routes, request/response models
│   │   ├── agent/            # LLM query agent, tool definitions, SAR generator
│   │   ├── models/           # Rules engine, Isolation Forest, XGBoost, hybrid scorer
│   │   ├── features/         # Feature engineering (point-in-time, rolling windows)
│   │   ├── data/             # Synthetic data generator
│   │   └── utils/            # LLM client, data loader helpers
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/               # Next.js App Router pages
│   │   ├── components/        # Dashboard, chat panel, trace log, charts
│   │   └── lib/                # API client, types, SSE stream helper
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── env-vars.txt              # Copy to .env before first run
└── README.md
```

---

## Usage Examples

Once running, try asking the agent (via the dashboard chat panel):

- *"Give me an overview of this dataset"* → triggers broad EDA
- *"Find structuring patterns in the last 30 days"* → targeted pattern
  detection, skips full EDA
- *"Is customer 4521 suspicious?"* → single-entity lookup only
- *"Which customers should be reported?"* → filters by high risk level and
  can trigger SAR generation for flagged customers

---

## Data Sources

- All transaction and customer data used in this project is **synthetically
  generated** (see [Dataset Information](#dataset-information)) — no real or
  third-party proprietary data is used.
- AML typology definitions (structuring, layering, rapid cash-out, etc.) are
  based on publicly available regulatory guidance (e.g., FinCEN and FATF
  typology descriptions) used only as a reference for designing detection
  rules — no external datasets were downloaded or redistributed.

---

## Notes & Limitations

- This is a hackathon prototype built for demonstration purposes and is not
  intended for production use with real financial data.
- The synthetic dataset regenerates at each container startup; results may
  vary slightly between runs unless a fixed random seed is used.
- If no LLM API key is provided, the investigation agent runs in a
  rule-based fallback mode with reduced natural-language capability but
  full detection functionality.