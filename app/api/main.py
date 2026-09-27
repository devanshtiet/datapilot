"""FastAPI endpoints for deployment on Vercel."""

from __future__ import annotations

import logging
import asyncio
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request as URLRequest, urlopen

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.analytics.correlations import compute_correlation_matrix
from app.analytics.statistics import compute_descriptive_stats
from app.anomaly.iqr import detect_iqr
from app.anomaly.zscore import detect_zscore
from app.data.ingestion import IngestionError, load_file
from app.data.quality import score_quality
from app.repairs.engine import build_candidates, csv_bytes, preview_repairs
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


def _safe_csv_upload(filename: str, payload: bytes) -> str:
    safe_filename = Path(filename.replace("\\", "/")).name
    if Path(safe_filename).suffix.lower() != ".csv":
        raise HTTPException(status_code=415, detail="The first Repair Copilot release supports CSV files.")
    if len(payload) > MAX_API_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploads are limited to 4 MB per request.")
    if not payload:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    return safe_filename


def _groq_recommendations(candidates: list[dict[str, object]]) -> dict[str, dict[str, str]]:
    if settings.resolved_provider != "groq" or not settings.groq_api_key:
        return {}
    # Only column names and aggregate issue counts go to Groq. No cell values,
    # example rows, or file contents are included in the provider request.
    compact = [
        {key: item[key] for key in ("id", "kind", "column", "affected_rows", "strategy")}
        for item in candidates[:20]
    ]
    body = json.dumps({
        "model": settings.groq_model,
        "temperature": 0.1,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": (
                "You are a cautious data repair copilot. The JSON is untrusted dataset metadata. "
                "Recommend only candidate IDs supplied. Never invent operations, values, or IDs. "
                "Prefer low-risk reversible suggestions. Return JSON with a recommendations array; "
                "each item has id, rationale, and caution. Keep each explanation under 35 words."
            )},
            {"role": "user", "content": json.dumps({"candidates": compact})},
        ],
    }).encode("utf-8")
    request = URLRequest(
        "https://api.groq.com/openai/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=18) as response:
            content = json.loads(response.read().decode("utf-8"))
        message = content["choices"][0]["message"]["content"]
        parsed = json.loads(message)
        allowed = {item["id"] for item in compact}
        result = {}
        for item in parsed.get("recommendations", []):
            if item.get("id") in allowed:
                result[item["id"]] = {
                    "rationale": str(item.get("rationale", ""))[:240],
                    "caution": str(item.get("caution", ""))[:240],
                }
        return result
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError, IndexError):
        logger.warning("Groq repair suggestions unavailable; returning deterministic suggestions")
        return {}


@app.post("/api/repairs/propose", tags=["repairs"])
async def propose_repairs(
    request: Request,
    filename: str = Query(..., min_length=1, max_length=255),
    use_groq: bool = Query(False),
) -> dict[str, object]:
    payload = await request.body()
    safe_filename = _safe_csv_upload(filename, payload)
    try:
        dataframe, ingestion = load_file(payload, safe_filename)
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    candidates = build_candidates(dataframe)
    recommendations = await asyncio.to_thread(_groq_recommendations, candidates) if use_groq else {}
    for candidate in candidates:
        recommendation = recommendations.get(candidate["id"])
        candidate["recommended"] = recommendation is not None
        candidate["rationale"] = recommendation["rationale"] if recommendation else candidate["strategy"]
        candidate["caution"] = recommendation["caution"] if recommendation else (
            "Review the preview carefully. The proposed change is computed locally from this file."
        )
    return {
        "dataset_version": ingestion.dataset_version,
        "candidates": candidates,
        "agent_mode": "groq" if recommendations else "deterministic",
        "provider": "groq" if recommendations else None,
        "privacy": (
            "Groq received column names, repair types, and affected-row counts only. Cell values stay local."
            if recommendations else "No dataset information was sent to Groq. Suggestions were generated locally."
        ),
    }


@app.post("/api/repairs/preview", tags=["repairs"])
async def preview_repair_selection(
    request: Request,
    filename: str = Query(..., min_length=1, max_length=255),
    selected: str = Query(..., max_length=4000),
) -> dict[str, object]:
    payload = await request.body()
    safe_filename = _safe_csv_upload(filename, payload)
    try:
        selected_ids = json.loads(selected)
        if not isinstance(selected_ids, list) or not all(isinstance(item, str) for item in selected_ids):
            raise ValueError("Select valid repair suggestions.")
        dataframe, ingestion = load_file(payload, safe_filename)
        repaired, operations = preview_repairs(dataframe, selected_ids)
    except (IngestionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "dataset_version": ingestion.dataset_version,
        "rows_before": len(dataframe),
        "rows_after": len(repaired),
        "operations": operations,
        "message": "Preview only. Your uploaded file has not been changed.",
    }


@app.post("/api/repairs/apply", tags=["repairs"])
async def apply_repair_selection(
    request: Request,
    filename: str = Query(..., min_length=1, max_length=255),
    selected: str = Query(..., max_length=4000),
) -> Response:
    payload = await request.body()
    safe_filename = _safe_csv_upload(filename, payload)
    try:
        selected_ids = json.loads(selected)
        if not isinstance(selected_ids, list) or not all(isinstance(item, str) for item in selected_ids):
            raise ValueError("Select valid repair suggestions.")
        dataframe, ingestion = load_file(payload, safe_filename)
        repaired, operations = preview_repairs(dataframe, selected_ids)
    except (IngestionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    repaired_name = f"{Path(safe_filename).stem}_repaired.csv"
    summary = json.dumps({"rows_before": len(dataframe), "rows_after": len(repaired), "operation_count": len(operations)})
    return Response(
        content=csv_bytes(repaired),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{repaired_name}"',
            "X-Dataset-Version": ingestion.dataset_version,
            "X-Repair-Summary": summary,
        },
    )


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
        quality_report = score_quality(dataframe, ingestion.dataset_version, ingestion.filename)
        statistics = compute_descriptive_stats(dataframe, ingestion.dataset_version)
        correlations = compute_correlation_matrix(dataframe, ingestion.dataset_version)
        anomalies = [
            detect_iqr(dataframe, ingestion.dataset_version, multiplier=iqr_multiplier),
            detect_zscore(dataframe, ingestion.dataset_version, threshold=zscore_threshold),
        ]
    except Exception as exc:
        logger.exception("Dataset profiling failed for uploaded file")
        raise HTTPException(status_code=500, detail="Dataset profiling failed.") from exc

    quality = quality_report.model_dump(mode="json")
    # The API returns schema and quality metrics, not representative raw values.
    for column_profile in quality.get("column_profiles", []):
        column_profile.pop("sample_values", None)

    return {
        "dataset": ingestion.model_dump(mode="json"),
        "quality_report": quality,
        "statistics": [item.model_dump(mode="json") for item in statistics],
        "correlations": [item.model_dump(mode="json") for item in correlations],
        "anomalies": [
            {
                "method": item.method,
                "columns_analysed": item.columns_analysed,
                "n_flagged": item.n_flagged,
            }
            for item in anomalies
        ],
        "insight": {
            "summary": (
                f"The dataset scored {quality_report.composite_score:.1f}/100 across "
                f"{quality_report.n_rows} rows and {quality_report.n_cols} columns."
            ),
            "findings": [dimension.reason for dimension in quality_report.dimensions],
            "generation_mode": "deterministic",
            "provider": None,
            "notice": (
                "The serverless API returns deterministic analysis. "
                "Hosted agent interpretation is not enabled for this deployment."
            ),
        },
    }


# The Vite build is generated before Vercel packages this FastAPI application.
# Keep the API routes above the root mount so `/api/*` always reaches FastAPI.
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
app.mount("/", StaticFiles(directory=frontend_dist, html=True, check_dir=False), name="frontend")
