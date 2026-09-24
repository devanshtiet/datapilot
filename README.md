# DataPilot

> **Agentic AI data-analysis tool** — upload a CSV/Excel, get automated quality scoring, statistical profiling, anomaly detection, and (Mission 2+) LLM-powered root-cause explanations with every number traceable to its exact computation.

---

## Architecture

```
Upload → Quality Score → Descriptive Stats → Anomaly Detection (IQR + Z-score + Isolation Forest) → Insights (Mission 2+)
```

**Core rule:** the LLM never computes a metric. Every number originates from a deterministic Python/SQL tool call wrapped as a Pydantic `EvidenceObject`.

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
- [ ] **Mission 2** — LangGraph orchestration, hypothesis testing, root-cause analysis, evidence traceability
- [ ] **Mission 3** — NL querying, SQL validation, security guardrails, audit logging
- [ ] **Mission 4** — Human-in-the-loop feedback, benchmark suite
- [ ] **Mission 5** — Voice interface (Whisper + TTS)
