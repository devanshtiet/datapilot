"""
app/data/quality.py
===================
Data quality scoring engine.

Produces a QualityReport with four scored dimensions:
  - Completeness  (weight 40%): fraction of non-missing values
  - Uniqueness    (weight 20%): fraction of non-duplicate rows
  - Validity      (weight 25%): absence of type mismatches, constant cols, all-null cols
  - Consistency   (weight 15%): column name / type coherence checks

Every dimension carries an EvidenceObject so the user can inspect how the
score was derived. No LLM calls; all logic is deterministic Python.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import numpy as np
import pandas as pd

from app.models.pydantic import (
    ColumnProfile,
    EvidenceObject,
    QualityDimension,
    QualityReport,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Weights (must sum to 1.0)
# ---------------------------------------------------------------------------
_WEIGHTS = {
    "completeness": 0.40,
    "uniqueness": 0.20,
    "validity": 0.25,
    "consistency": 0.15,
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_quality(
    df: pd.DataFrame,
    dataset_version: str,
    filename: str,
) -> QualityReport:
    """
    Compute a composite quality score (0–100) and per-dimension sub-scores.

    Parameters
    ----------
    df:             The parsed DataFrame.
    dataset_version: SHA-256 content hash from ingestion.
    filename:        Original filename for display.

    Returns
    -------
    QualityReport Pydantic model.
    """
    try:
        n_rows, n_cols = df.shape
        dimensions: list[QualityDimension] = [
            _completeness(df, dataset_version, n_rows),
            _uniqueness(df, dataset_version, n_rows),
            _validity(df, dataset_version, n_rows),
            _consistency(df, dataset_version, n_rows),
        ]
        composite = sum(
            _WEIGHTS[dim.name] * dim.score for dim in dimensions
        )
        profiles = [_profile_column(df, col, dataset_version) for col in df.columns]
        report = QualityReport(
            dataset_version=dataset_version,
            filename=filename,
            n_rows=n_rows,
            n_cols=n_cols,
            composite_score=round(composite, 2),
            dimensions=dimensions,
            column_profiles=profiles,
        )
        logger.info(
            "Quality score for '%s': %.1f (C=%.1f U=%.1f V=%.1f Cons=%.1f)",
            filename,
            composite,
            dimensions[0].score,
            dimensions[1].score,
            dimensions[2].score,
            dimensions[3].score,
        )
        return report
    except Exception as exc:
        logger.exception("Error scoring quality for dataset_version=%s", dataset_version)
        raise RuntimeError(f"quality scoring failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Dimension scorers
# ---------------------------------------------------------------------------


def _completeness(df: pd.DataFrame, dv: str, n_rows: int) -> QualityDimension:
    """Score 0–100 based on mean missing-value rate across all columns."""
    null_counts = df.isnull().sum()
    total_cells = n_rows * len(df.columns)
    total_missing = int(null_counts.sum())
    missing_rate = total_missing / total_cells if total_cells > 0 else 0.0
    score = round(100.0 * (1.0 - missing_rate), 2)

    worst_cols = null_counts[null_counts > 0].sort_values(ascending=False)
    if worst_cols.empty:
        reason = "No missing values detected across all columns."
    else:
        top = worst_cols.head(3)
        parts = [f"'{c}' ({v / n_rows * 100:.1f}%)" for c, v in top.items()]
        reason = f"{missing_rate * 100:.1f}% of values are missing overall. Worst columns: {', '.join(parts)}."

    evidence = EvidenceObject(
        metric="completeness_score",
        value=score,
        calculation=(
            f"completeness = 100 × (1 − total_missing / total_cells) "
            f"= 100 × (1 − {total_missing} / {total_cells}) = {score:.2f}"
        ),
        source_tool="app.data.quality._completeness",
        dataset_version=dv,
        rows_used=n_rows,
        confidence=1.0,
    )
    return QualityDimension(name="completeness", score=score, reason=reason, evidence=evidence)


def _uniqueness(df: pd.DataFrame, dv: str, n_rows: int) -> QualityDimension:
    """Score 0–100 based on duplicate-row rate."""
    n_duplicates = int(df.duplicated().sum())
    n_unique_rows = n_rows - n_duplicates
    score = round(100.0 * n_unique_rows / n_rows, 2) if n_rows > 0 else 100.0

    if n_duplicates == 0:
        reason = "No duplicate rows detected."
    else:
        reason = (
            f"{n_duplicates} duplicate row(s) found "
            f"({n_duplicates / n_rows * 100:.1f}% of all rows)."
        )

    evidence = EvidenceObject(
        metric="uniqueness_score",
        value=score,
        calculation=(
            f"uniqueness = 100 × (n_unique_rows / n_rows) "
            f"= 100 × ({n_unique_rows} / {n_rows}) = {score:.2f}"
        ),
        source_tool="app.data.quality._uniqueness",
        dataset_version=dv,
        rows_used=n_rows,
        confidence=1.0,
    )
    return QualityDimension(name="uniqueness", score=score, reason=reason, evidence=evidence)


def _validity(df: pd.DataFrame, dv: str, n_rows: int) -> QualityDimension:
    """
    Score 0–100 penalising:
    - All-null columns         (severe: −20 pts each, max penalty 60)
    - Constant columns         (moderate: −10 pts each, max penalty 40)
    - Mixed-type object cols   (mild: −5 pts each, max penalty 30)
      (object col where >5% of non-null values are parseable as numeric)
    """
    issues: list[str] = []
    penalty = 0.0

    for col in df.columns:
        series = df[col]
        if series.isnull().all():
            issues.append(f"'{col}' is entirely null")
            penalty = min(penalty + 20, 60)
            continue
        if series.nunique(dropna=True) <= 1:
            issues.append(f"'{col}' is constant (only one unique value)")
            penalty = min(penalty + 10, 40 + penalty)
            continue
        if series.dtype == object:
            non_null = series.dropna()
            parseable = pd.to_numeric(non_null, errors="coerce").notna().sum()
            if len(non_null) > 0 and parseable / len(non_null) > 0.05:
                issues.append(
                    f"'{col}' is object-typed but {parseable / len(non_null) * 100:.1f}% "
                    "of values are numeric — possible type mismatch"
                )
                penalty = min(penalty + 5, 30 + penalty)

    score = max(0.0, round(100.0 - penalty, 2))
    reason = (
        "; ".join(issues) + "." if issues else "No validity issues detected."
    )

    evidence = EvidenceObject(
        metric="validity_score",
        value=score,
        calculation=(
            f"validity = max(0, 100 − penalty) where penalty = {penalty:.1f} "
            f"from {len(issues)} issue(s): [{'; '.join(issues) or 'none'}]"
        ),
        source_tool="app.data.quality._validity",
        dataset_version=dv,
        rows_used=n_rows,
        confidence=0.9,
    )
    return QualityDimension(name="validity", score=score, reason=reason, evidence=evidence)


# Patterns that suggest a column should contain dates
_DATE_HINTS = re.compile(r"date|time|timestamp|dt|day|month|year|created|updated", re.IGNORECASE)


def _consistency(df: pd.DataFrame, dv: str, n_rows: int) -> QualityDimension:
    """
    Score 0–100 penalising:
    - Columns whose name suggests dates but whose values don't parse as dates
      (−15 pts each, max penalty 45)
    - Object columns with suspicious high cardinality (>50% unique, >100 rows)
      that look like free-text leaking into a categorical field
      (−5 pts each, max penalty 20)
    """
    issues: list[str] = []
    penalty = 0.0

    for col in df.columns:
        series = df[col]
        # Date-name / non-date-value mismatch
        if _DATE_HINTS.search(col) and series.dtype == object:
            non_null = series.dropna()
            if len(non_null) > 0:
                parsed = pd.to_datetime(non_null, errors="coerce", infer_datetime_format=True)
                parse_rate = parsed.notna().sum() / len(non_null)
                if parse_rate < 0.5:
                    issues.append(
                        f"'{col}' name suggests dates but only "
                        f"{parse_rate * 100:.1f}% of values are parseable as dates"
                    )
                    penalty = min(penalty + 15, 45)

        # High-cardinality object col (possible free-text)
        if series.dtype == object and n_rows > 100:
            n_unique = series.nunique(dropna=True)
            if n_unique / n_rows > 0.5:
                issues.append(
                    f"'{col}' has very high cardinality "
                    f"({n_unique} unique values in {n_rows} rows — possible free-text)"
                )
                penalty = min(penalty + 5, 20)

    score = max(0.0, round(100.0 - penalty, 2))
    reason = "; ".join(issues) + "." if issues else "No consistency issues detected."

    evidence = EvidenceObject(
        metric="consistency_score",
        value=score,
        calculation=(
            f"consistency = max(0, 100 − penalty) where penalty = {penalty:.1f} "
            f"from {len(issues)} issue(s)"
        ),
        source_tool="app.data.quality._consistency",
        dataset_version=dv,
        rows_used=n_rows,
        confidence=0.85,
    )
    return QualityDimension(name="consistency", score=score, reason=reason, evidence=evidence)


# ---------------------------------------------------------------------------
# Column profile helper
# ---------------------------------------------------------------------------


def _profile_column(df: pd.DataFrame, col: str, dv: str) -> ColumnProfile:
    series = df[col]
    n_missing = int(series.isnull().sum())
    n_rows = len(series)
    n_unique = int(series.nunique(dropna=True))
    non_null = series.dropna()
    sample_raw = non_null.head(5).tolist() if not non_null.empty else []
    sample_values = [str(v) for v in sample_raw]
    return ColumnProfile(
        column_name=col,
        dtype=str(series.dtype),
        n_missing=n_missing,
        pct_missing=round(n_missing / n_rows * 100, 2) if n_rows > 0 else 0.0,
        n_unique=n_unique,
        pct_unique=round(n_unique / n_rows * 100, 2) if n_rows > 0 else 0.0,
        sample_values=sample_values,
    )
