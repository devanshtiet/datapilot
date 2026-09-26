"""FastAPI endpoints for deployment on Vercel."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request

from app.agents.planner import run_analysis_agent
from app.data.ingestion import IngestionError, load_file
from config.settings import settings

logger = logging.getLogger(__name__)

# Vercel Function request bodies are capped at 4.5 MB. Leave room for request
# framing and multipart clients by enforcing a slightly smaller raw-file limit.
MAX_API_UPLOAD_BYTES = 4 * 1024 * 1024
ALLOWED_SUFFIXES = {".csv", ".xlsx", ".xls"}

app = FastAPI(
    title="DataPilot API",
    description="Deterministic dataset profiling and anomaly analysis.",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@app.get("/api", tags=["system"])
async def api_root() -> dict[str, str]:
    return {
        "name": "DataPilot API",
        "health": "/api/health",
        "profile": "POST /api/profile?filename=dataset.csv",
        "docs": "/api/docs",
    }


@app.get("/api/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "datapilot-api"}


@app.post("/api/profile", tags=["analysis"])
async def profile_dataset(
    request: Request,
    filename: str = Query(..., min_length=1, max_length=255),
    zscore_threshold: float = Query(3.0, ge=1.5, le=5.0),
    iqr_multiplier: float = Query(1.5, ge=1.0, le=3.0),
) -> dict[str, object]:
    """Profile a CSV/XLS/XLSX sent as the raw request body.

    Send the file bytes with Content-Type: application/octet-stream and set
    `filename` to the original file name in the query string.
    """
    safe_filename = Path(filename.replace("\\", "/")).name
    suffix = Path(safe_filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Upload a CSV, XLS, or XLSX file.")

    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_API_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Vercel uploads are limited to 4 MB per request.")

    payload = await request.body()
    if len(payload) > MAX_API_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Vercel uploads are limited to 4 MB per request.")
    if not payload:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        dataframe, ingestion = load_file(payload, safe_filename)
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        analysis = run_analysis_agent(
            dataframe,
            ingestion.dataset_version,
            ingestion.filename,
            zscore_threshold=zscore_threshold,
            iqr_multiplier=iqr_multiplier,
            use_hosted_llm=False,
        )
    except Exception as exc:
        logger.exception("Dataset profiling failed for uploaded file")
        raise HTTPException(status_code=500, detail="Dataset profiling failed.") from exc

    quality = analysis["quality_report"].model_dump(mode="json")
    # The API returns schema and quality metrics, not representative raw values.
    for column_profile in quality.get("column_profiles", []):
        column_profile.pop("sample_values", None)

    return {
        "dataset": ingestion.model_dump(mode="json"),
        "quality_report": quality,
        "statistics": [item.model_dump(mode="json") for item in analysis["stats"]],
        "correlations": [item.model_dump(mode="json") for item in analysis["correlations"]],
        "anomalies": [
            {
                "method": item.method,
                "columns_analysed": item.columns_analysed,
                "n_flagged": item.n_flagged,
            }
            for item in analysis["anomaly_summaries"]
        ],
        "insight": analysis["insight"].model_dump(mode="json"),
    }
