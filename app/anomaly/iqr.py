"""
app/anomaly/iqr.py
==================
IQR (Tukey fence) anomaly detector.

For each numeric column, computes Q1, Q3, IQR, and Tukey fences
(Q1 − k×IQR, Q3 + k×IQR where k is configurable via settings).
Rows outside the fences are flagged as anomalies.

Score: normalised distance beyond the nearest fence, divided by IQR.
  - Values inside the fences receive a score of 0.0.
  - Values outside receive score = |distance_beyond_fence| / IQR.

Confidence: 0.80 (rule-based, deterministic method).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from app.models.pydantic import AnomalyResult, AnomalySummary, EvidenceObject
from config.settings import settings

logger = logging.getLogger(__name__)

_CONFIDENCE_FLAGGED = 0.80
_CONFIDENCE_OK = 0.80  # same — IQR is deterministic for both outcomes


def detect_iqr(
    df: pd.DataFrame,
    dataset_version: str,
    columns: list[str] | None = None,
) -> AnomalySummary:
    """
    Run IQR anomaly detection on numeric columns.

    Parameters
    ----------
    df:               Input DataFrame.
    dataset_version:  SHA-256 hash for traceability.
    columns:          Specific columns to analyse; defaults to all numeric cols.

    Returns
    -------
    AnomalySummary containing AnomalyResult for every (row, column) pair.
    Only flagged rows are included in the results list to keep output concise.
    """
    k = settings.iqr_fence_multiplier
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    target_cols = columns if columns is not None else numeric_cols
    target_cols = [c for c in target_cols if c in numeric_cols]

    all_results: list[AnomalyResult] = []

    for col in target_cols:
        try:
            col_results = _analyse_column(df, col, k, dataset_version)
            all_results.extend(col_results)
        except Exception as exc:
            logger.warning("IQR skipped for column '%s': %s", col, exc)

    flagged = [r for r in all_results if r.is_anomaly]
    logger.info(
        "IQR detection: %d flagged across %d col(s), dataset_version=%s",
        len(flagged),
        len(target_cols),
        dataset_version[:8],
    )
    return AnomalySummary(
        method="iqr",
        dataset_version=dataset_version,
        columns_analysed=target_cols,
        n_flagged=len(flagged),
        results=flagged,  # only return flagged rows; full scores available per-column if needed
    )


def _analyse_column(
    df: pd.DataFrame,
    col: str,
    k: float,
    dataset_version: str,
) -> list[AnomalyResult]:
    series = df[col].dropna()
    if len(series) < 4:
        logger.debug("IQR: skipping '%s' — fewer than 4 non-null values", col)
        return []

    arr = series.to_numpy(dtype=float)
    q1 = float(np.percentile(arr, 25))
    q3 = float(np.percentile(arr, 75))
    iqr = q3 - q1

    if iqr == 0.0:
        logger.debug("IQR: skipping '%s' — IQR is zero (constant column)", col)
        return []

    lower_fence = q1 - k * iqr
    upper_fence = q3 + k * iqr

    results: list[AnomalyResult] = []
    # Iterate over original DataFrame to preserve row indices
    for idx, val in df[col].items():
        if pd.isna(val):
            continue
        fval = float(val)
        is_anomaly = fval < lower_fence or fval > upper_fence

        if fval < lower_fence:
            distance = lower_fence - fval
        elif fval > upper_fence:
            distance = fval - upper_fence
        else:
            distance = 0.0

        score = round(distance / iqr, 6)

        if is_anomaly:
            calc = (
                f"Q1={q1:.4f}, Q3={q3:.4f}, IQR={iqr:.4f}, k={k}; "
                f"lower_fence=Q1−k×IQR={lower_fence:.4f}, "
                f"upper_fence=Q3+k×IQR={upper_fence:.4f}; "
                f"value={fval:.4f} is {'below lower' if fval < lower_fence else 'above upper'} fence; "
                f"score=|distance|/IQR={score:.4f}"
            )
            results.append(
                AnomalyResult(
                    column=col,
                    method="iqr",
                    is_anomaly=True,
                    score=score,
                    row_index=int(idx),
                    value=fval,
                    evidence=EvidenceObject(
                        metric="iqr_anomaly_score",
                        value=score,
                        calculation=calc,
                        source_tool="app.anomaly.iqr.detect_iqr",
                        dataset_version=dataset_version,
                        rows_used=len(series),
                        confidence=_CONFIDENCE_FLAGGED,
                    ),
                )
            )

    return results
