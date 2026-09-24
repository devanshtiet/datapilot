"""
app/analytics/correlations.py
==============================
Pearson correlation matrix for numeric columns.

Returns a flat list of CorrelationResult objects (all pairs, both
directions omitted — upper triangle only). The full matrix can be
reconstructed in the UI from this list.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

from app.models.pydantic import CorrelationResult, EvidenceObject

logger = logging.getLogger(__name__)


def compute_correlation_matrix(
    df: pd.DataFrame,
    dataset_version: str,
) -> list[CorrelationResult]:
    """
    Compute Pearson correlations for all unique numeric column pairs.

    Parameters
    ----------
    df:               Input DataFrame.
    dataset_version:  SHA-256 hash for traceability.

    Returns
    -------
    List of CorrelationResult (upper-triangle pairs only, i.e. col_a < col_b
    in column order). Returns empty list if fewer than 2 numeric columns.
    """
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    results: list[CorrelationResult] = []

    if len(numeric_cols) < 2:
        logger.info(
            "Fewer than 2 numeric columns — skipping correlation matrix for %s",
            dataset_version[:8],
        )
        return results

    for i, col_a in enumerate(numeric_cols):
        for col_b in numeric_cols[i + 1 :]:
            try:
                result = _pair_correlation(df, col_a, col_b, dataset_version)
                if result is not None:
                    results.append(result)
            except Exception as exc:
                logger.warning("Skipping correlation (%s, %s): %s", col_a, col_b, exc)

    logger.info(
        "Computed %d Pearson correlation(s) for dataset_version=%s",
        len(results),
        dataset_version[:8],
    )
    return results


def _pair_correlation(
    df: pd.DataFrame,
    col_a: str,
    col_b: str,
    dataset_version: str,
) -> CorrelationResult | None:
    """Compute Pearson r for one column pair, dropping rows where either is null."""
    pair = df[[col_a, col_b]].dropna()
    n_valid = len(pair)

    if n_valid < 3:
        logger.debug(
            "Skipping (%s, %s): only %d valid joint observations", col_a, col_b, n_valid
        )
        return None

    arr_a = pair[col_a].to_numpy(dtype=float)
    arr_b = pair[col_b].to_numpy(dtype=float)

    # Use scipy for p-value access (future use) and NaN safety
    r, p_value = pearsonr(arr_a, arr_b)
    r_rounded = round(float(r), 6)

    evidence = EvidenceObject(
        metric="pearson_r",
        value=r_rounded,
        calculation=(
            f"scipy.stats.pearsonr(df['{col_a}'].dropna_jointly, df['{col_b}'].dropna_jointly) "
            f"on n={n_valid} joint observations → r={r_rounded:.6f}, p={p_value:.4g}"
        ),
        source_tool="app.analytics.correlations.compute_correlation_matrix",
        dataset_version=dataset_version,
        rows_used=n_valid,
        confidence=_pearson_confidence(n_valid, abs(r)),
    )

    return CorrelationResult(
        col_a=col_a,
        col_b=col_b,
        method="pearson",
        coefficient=r_rounded,
        evidence=evidence,
    )


def _pearson_confidence(n: int, abs_r: float) -> float:
    """
    Heuristic confidence: higher n and higher |r| both increase confidence.
    Not a formal statistical confidence interval — that's added in Mission 2.
    """
    n_factor = min(1.0, n / 100)       # saturates at n=100
    r_factor = abs_r                    # |r| itself is 0–1
    return round(0.5 * n_factor + 0.5 * r_factor, 3)
