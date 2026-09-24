"""
app/analytics/statistics.py
============================
Descriptive statistics for numeric columns.

Every statistic is returned as a DescriptiveStats Pydantic model containing
an EvidenceObject that names the exact pandas/scipy function used and the
computation performed. The LLM never computes these values.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from app.models.pydantic import DescriptiveStats, EvidenceObject

logger = logging.getLogger(__name__)


def compute_descriptive_stats(
    df: pd.DataFrame,
    dataset_version: str,
) -> list[DescriptiveStats]:
    """
    Compute descriptive statistics for every numeric column in `df`.

    Parameters
    ----------
    df:               Input DataFrame (all dtypes; only numeric cols processed).
    dataset_version:  SHA-256 hash from ingestion for traceability.

    Returns
    -------
    List of DescriptiveStats, one per numeric column.
    Columns with fewer than 2 non-null values get all stats set to None.
    """
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    results: list[DescriptiveStats] = []

    for col in numeric_cols:
        try:
            result = _compute_column_stats(df[col], col, dataset_version)
            results.append(result)
        except Exception as exc:
            logger.warning("Skipping stats for column '%s': %s", col, exc)

    logger.info(
        "Computed descriptive stats for %d numeric column(s), dataset_version=%s",
        len(results),
        dataset_version[:8],
    )
    return results


def _compute_column_stats(
    series: pd.Series,
    col: str,
    dataset_version: str,
) -> DescriptiveStats:
    non_null = series.dropna()
    n_valid = len(non_null)

    if n_valid < 2:
        return DescriptiveStats(
            column=col,
            n_valid=n_valid,
            evidence=EvidenceObject(
                metric="descriptive_stats",
                value="insufficient_data",
                calculation=f"Column '{col}' has only {n_valid} non-null value(s); stats require ≥2.",
                source_tool="app.analytics.statistics.compute_descriptive_stats",
                dataset_version=dataset_version,
                rows_used=n_valid,
                confidence=0.0,
            ),
        )

    arr = non_null.to_numpy(dtype=float)

    mean_val = float(np.mean(arr))
    median_val = float(np.median(arr))
    std_val = float(np.std(arr, ddof=1))  # sample std
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))
    q1_val = float(np.percentile(arr, 25))
    q3_val = float(np.percentile(arr, 75))
    skew_val = float(sp_stats.skew(arr, bias=True))
    kurt_val = float(sp_stats.kurtosis(arr, bias=True))  # excess kurtosis

    calculation = (
        f"n_valid={n_valid}; "
        f"mean=np.mean={mean_val:.6g}; "
        f"median=np.median={median_val:.6g}; "
        f"std=np.std(ddof=1)={std_val:.6g}; "
        f"min={min_val:.6g}; max={max_val:.6g}; "
        f"Q1=np.percentile(25)={q1_val:.6g}; "
        f"Q3=np.percentile(75)={q3_val:.6g}; "
        f"skewness=scipy.stats.skew={skew_val:.6g}; "
        f"kurtosis(excess)=scipy.stats.kurtosis={kurt_val:.6g}"
    )

    evidence = EvidenceObject(
        metric="descriptive_stats",
        value=mean_val,  # primary representative value
        calculation=calculation,
        source_tool="app.analytics.statistics.compute_descriptive_stats",
        dataset_version=dataset_version,
        rows_used=n_valid,
        confidence=1.0,
    )

    return DescriptiveStats(
        column=col,
        n_valid=n_valid,
        mean=round(mean_val, 6),
        median=round(median_val, 6),
        std=round(std_val, 6),
        min_val=round(min_val, 6),
        max_val=round(max_val, 6),
        q1=round(q1_val, 6),
        q3=round(q3_val, 6),
        skewness=round(skew_val, 6),
        kurtosis=round(kurt_val, 6),
        evidence=evidence,
    )
