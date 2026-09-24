"""
app/anomaly/isolation_forest.py
================================
Isolation Forest anomaly detector (sklearn).

Trains on all numeric columns jointly, so it captures multivariate
anomalies that univariate methods (IQR, Z-score) may miss.

Score: negated decision_function output (higher = more anomalous).
  sklearn's decision_function returns negative values for anomalies
  (more negative = more anomalous), so we negate and shift so that
  normal points ≈ 0 and anomalies > 0.

Confidence: 0.85 for flagged rows, 0.65 for non-flagged.
  (Model is probabilistic; confidence reflects method reliability,
   not the individual sample probability.)
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.models.pydantic import AnomalyResult, AnomalySummary, EvidenceObject
from config.settings import settings

logger = logging.getLogger(__name__)

_CONFIDENCE_FLAGGED = 0.85
_CONFIDENCE_OK = 0.65


def detect_isolation_forest(
    df: pd.DataFrame,
    dataset_version: str,
    columns: list[str] | None = None,
) -> AnomalySummary:
    """
    Run Isolation Forest on all numeric columns (multivariate).

    Parameters
    ----------
    df:               Input DataFrame.
    dataset_version:  SHA-256 hash for traceability.
    columns:          Optional subset of numeric columns to use as features.
                      Defaults to all numeric columns.

    Returns
    -------
    AnomalySummary containing AnomalyResult for every flagged row.
    The 'column' field is set to '__multivariate__' since IF is row-level.
    """
    contamination = settings.isolation_forest_contamination
    n_estimators = settings.isolation_forest_n_estimators
    random_state = settings.isolation_forest_random_state

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    feature_cols = columns if columns is not None else numeric_cols
    feature_cols = [c for c in feature_cols if c in numeric_cols]

    if len(feature_cols) == 0:
        logger.warning("Isolation Forest: no numeric columns available, skipping.")
        return AnomalySummary(
            method="isolation_forest",
            dataset_version=dataset_version,
            columns_analysed=[],
            n_flagged=0,
            results=[],
        )

    try:
        # Drop rows where ALL feature columns are null
        feature_df = df[feature_cols].dropna(how="all")
        # For remaining nulls, impute with column mean (simple imputation for IF)
        feature_df = feature_df.fillna(feature_df.mean(numeric_only=True))

        n_rows, n_cols = feature_df.shape
        if n_rows < 10:
            logger.warning(
                "Isolation Forest: only %d rows after dropping all-null rows — skipping.", n_rows
            )
            return AnomalySummary(
                method="isolation_forest",
                dataset_version=dataset_version,
                columns_analysed=feature_cols,
                n_flagged=0,
                results=[],
            )

        clf = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
        )
        clf.fit(feature_df.values)

        preds = clf.predict(feature_df.values)          # 1 = normal, -1 = anomaly
        scores_raw = clf.decision_function(feature_df.values)  # more negative = more anomalous

        # Shift so that the maximum score (most normal) = 0 and anomalies are positive
        anomaly_scores = -(scores_raw - scores_raw.max())

        calc_template = (
            f"IsolationForest("
            f"contamination={contamination!r}, "
            f"n_estimators={n_estimators}, "
            f"random_state={random_state}) "
            f"trained on {n_rows} rows × {n_cols} numeric feature(s): "
            f"[{', '.join(feature_cols)}]"
        )

        results: list[AnomalyResult] = []
        for list_pos, (orig_idx, row) in enumerate(feature_df.iterrows()):
            is_anomaly = bool(preds[list_pos] == -1)
            score = float(round(anomaly_scores[list_pos], 6))

            if is_anomaly:
                calc = (
                    f"{calc_template}; "
                    f"row_index={int(orig_idx)}: "
                    f"decision_function={scores_raw[list_pos]:.6f}, "
                    f"anomaly_score(negated+shifted)={score:.6f}"
                )
                results.append(
                    AnomalyResult(
                        column="__multivariate__",
                        method="isolation_forest",
                        is_anomaly=True,
                        score=score,
                        row_index=int(orig_idx),
                        value=str(dict(row.round(4))),
                        evidence=EvidenceObject(
                            metric="isolation_forest_anomaly_score",
                            value=score,
                            calculation=calc,
                            source_tool="app.anomaly.isolation_forest.detect_isolation_forest",
                            dataset_version=dataset_version,
                            rows_used=n_rows,
                            confidence=_CONFIDENCE_FLAGGED,
                        ),
                    )
                )

        logger.info(
            "Isolation Forest: %d flagged out of %d rows, dataset_version=%s",
            len(results),
            n_rows,
            dataset_version[:8],
        )
        return AnomalySummary(
            method="isolation_forest",
            dataset_version=dataset_version,
            columns_analysed=feature_cols,
            n_flagged=len(results),
            results=results,
        )

    except Exception as exc:
        logger.exception("Isolation Forest failed for dataset_version=%s", dataset_version)
        raise RuntimeError(f"IsolationForest detection failed: {exc}") from exc
