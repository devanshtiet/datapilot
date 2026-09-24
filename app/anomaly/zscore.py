"""
app/anomaly/zscore.py
=====================
Z-score anomaly detector.

For each numeric column, standardises values using the column mean and
sample standard deviation. Values with |z| > threshold (default 3.0,
configurable via settings) are flagged as anomalies.

Score: the absolute z-score.
Confidence: 0.75 (parametric — assumes approximate normality).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from app.models.pydantic import AnomalyResult, AnomalySummary, EvidenceObject
from config.settings import settings

logger = logging.getLogger(__name__)

_CONFIDENCE_FLAGGED = 0.75


def detect_zscore(
    df: pd.DataFrame,
    dataset_version: str,
    columns: list[str] | None = None,
) -> AnomalySummary:
    """
    Run Z-score anomaly detection on numeric columns.

    Parameters
    ----------
    df:               Input DataFrame.
    dataset_version:  SHA-256 hash for traceability.
    columns:          Specific columns to analyse; defaults to all numeric cols.

    Returns
    -------
    AnomalySummary containing only flagged AnomalyResult rows.
    """
    threshold = settings.zscore_threshold
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    target_cols = columns if columns is not None else numeric_cols
    target_cols = [c for c in target_cols if c in numeric_cols]

    all_flagged: list[AnomalyResult] = []

    for col in target_cols:
        try:
            flagged = _analyse_column(df, col, threshold, dataset_version)
            all_flagged.extend(flagged)
        except Exception as exc:
            logger.warning("Z-score skipped for column '%s': %s", col, exc)

    logger.info(
        "Z-score detection: %d flagged across %d col(s), dataset_version=%s",
        len(all_flagged),
        len(target_cols),
        dataset_version[:8],
    )
    return AnomalySummary(
        method="zscore",
        dataset_version=dataset_version,
        columns_analysed=target_cols,
        n_flagged=len(all_flagged),
        results=all_flagged,
    )


def _analyse_column(
    df: pd.DataFrame,
    col: str,
    threshold: float,
    dataset_version: str,
) -> list[AnomalyResult]:
    series = df[col].dropna()
    if len(series) < 2:
        logger.debug("Z-score: skipping '%s' — fewer than 2 non-null values", col)
        return []

    arr = series.to_numpy(dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))

    if std == 0.0:
        logger.debug("Z-score: skipping '%s' — std is zero (constant column)", col)
        return []

    flagged: list[AnomalyResult] = []
    for idx, val in df[col].items():
        if pd.isna(val):
            continue
        fval = float(val)
        z = (fval - mean) / std
        abs_z = abs(z)
        is_anomaly = abs_z > threshold

        if is_anomaly:
            calc = (
                f"mean={mean:.4f}, std(ddof=1)={std:.4f}; "
                f"z=(value−mean)/std=({fval:.4f}−{mean:.4f})/{std:.4f}={z:.4f}; "
                f"|z|={abs_z:.4f} > threshold={threshold}"
            )
            flagged.append(
                AnomalyResult(
                    column=col,
                    method="zscore",
                    is_anomaly=True,
                    score=round(abs_z, 6),
                    row_index=int(idx),
                    value=fval,
                    evidence=EvidenceObject(
                        metric="zscore_anomaly_score",
                        value=round(abs_z, 6),
                        calculation=calc,
                        source_tool="app.anomaly.zscore.detect_zscore",
                        dataset_version=dataset_version,
                        rows_used=len(series),
                        confidence=_CONFIDENCE_FLAGGED,
                    ),
                )
            )

    return flagged
