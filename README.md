# DataPilot

> **Agentic AI data-analysis tool** — upload a CSV/Excel, get automated quality scoring, statistical profiling, anomaly detection, and (Mission 2+) LLM-powered root-cause explanations with every number traceable to its exact computation.

---

## Architecture

```
Upload → LangGraph profiling workflow → Quality, statistics, correlations, and anomaly tools → Evidence-grounded insights
```

**Core rule:** the LLM never computes a metric. Every number originates from a deterministic Python/SQL tool call wrapped as a Pydantic `EvidenceObject`.

## Agent Insights

The Streamlit app runs the profiling workflow through LangGraph. It always produces a local evidence-based summary. Optional hosted interpretation is available with `GROQ_API_KEY` or `OPENAI_API_KEY` configured in `.env`; set `LLM_PROVIDER` to `groq`, `openai`, or `auto` and restart Streamlit. Hosted interpretation is off by default and requires checking the opt-in in the sidebar. When enabled, only aggregate quality/statistical results and column names are sent to the selected provider; raw rows and sample values stay local. Model names can be overridden with `GROQ_MODEL` and `OPENAI_MODEL`.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI |
| Frontend | Streamlit |
| Agent orchestration | LangGraph (Mission 2) |
| Analytics | Pandas, NumPy, SciPy, scikit-learn |
| Large-file SQL | DuckDB |
| Database | PostgreSQL / SQLAlchemy (Mission 3) |
| LLM | Groq / OpenAI (provider-agnostic, Mission 2) |
| Visualisation | Plotly |
| Validation | Pydantic v2 |

---

## Quick Start

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd datapilot

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and configure environment variables
cp .env.example .env
# Edit .env — API keys only needed from Mission 2 onwards

# 5. Generate synthetic test data
python scripts/generate_synthetic_data.py

# 6. Run the Streamlit demo
streamlit run frontend/streamlit_app.py
```

---

## Running Tests

```bash
pytest tests/unit/ -v --cov=app --cov-report=term-missing
```

---

## Project Structure

```
datapilot/
  app/
    agents/           # LangGraph agents (Mission 2)
    analytics/        # statistics.py, correlations.py
    anomaly/          # iqr.py, zscore.py, isolation_forest.py
    data/             # ingestion.py, quality.py, semantic_layer.py
    database/         # models.py, session.py, schema.sql
    models/           # pydantic.py — Evidence Object + all I/O schemas
    tools/            # tool_registry.py
    services/         # sql_validator.py, security.py (Mission 3)
    reports/          # report_generator.py
    visualization/    # chart_selector.py
    api/              # FastAPI routes
  frontend/
    streamlit_app.py
  tests/
    unit/
    integration/
    benchmark/
  scripts/
    generate_synthetic_data.py
  config/
    settings.py
  requirements.txt
  README.md
```

---

## Benchmark Results

*Populated in Mission 4.*

| Dataset | Method | Precision | Recall | F1 |
|---|---|---|---|---|
| TBD | IQR | — | — | — |
| TBD | Z-score | — | — | — |
| TBD | Isolation Forest | — | — | — |

---

## Milestones

- [x] **Mission 1** — Ingestion, quality scoring, stats, three anomaly detectors, Streamlit demo
- [ ] **Mission 2 (in progress)** — LangGraph profiling workflow and optional LLM interpretation are implemented; hypothesis testing and deeper root-cause analysis remain planned
- [ ] **Mission 3** — NL querying, SQL validation, security guardrails, audit logging
- [ ] **Mission 4** — Human-in-the-loop feedback, benchmark suite
- [ ] **Mission 5** — Voice interface (Whisper + TTS)
