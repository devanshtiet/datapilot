"""
app/models/pydantic.py
======================
Central data-contract definitions for DataPilot.

ARCHITECTURAL RULE: Every tool function's return type must be one of these
Pydantic models — never a bare dict or raw LLM string. The LLM never
computes a metric; every number must originate from a tool that returns one
of these models.

Models are extended across missions; do NOT remove or rename fields without
updating all downstream tools.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Core evidence primitive
# =============================================================================


class EvidenceObject(BaseModel):
    """
    Immutable record of *how* a single metric was produced.
    Every numeric value shown to the user must have exactly one EvidenceObject
    attached. The LLM receives these objects and is forbidden from inventing
    numbers that are not backed by one.
    """

    metric: str = Field(description="Human-readable name of the metric (e.g. 'mean', 'iqr_score')")
    value: float | int | str = Field(description="The computed value")
    calculation: str = Field(
        description=(
            "Human-readable description of the exact computation performed, "
            "including any parameters used (e.g. 'IQR = Q3 - Q1 = 7.2 - 3.1 = 4.1; "
            "lower_fence = Q1 - 1.5×IQR = 3.1 - 6.15 = -3.05')"
        )
    )
    source_tool: str = Field(description="Fully qualified function name that produced this value")
    dataset_version: str = Field(description="SHA-256 content hash of the source dataset")
    rows_used: int = Field(description="Number of rows the computation was applied to", ge=0)
    confidence: float = Field(
        description="Confidence in this metric, 0.0 (low) to 1.0 (high)",
        ge=0.0,
        le=1.0,
    )


# =============================================================================
# Data ingestion
# =============================================================================


class IngestionResult(BaseModel):
    """Returned by load_file() after successfully parsing an upload."""

    filename: str
    dataset_version: str = Field(description="SHA-256 hex digest of raw file bytes")
    n_rows: int = Field(ge=0)
    n_cols: int = Field(ge=0)
    column_names: list[str]
    dtypes: dict[str, str] = Field(description="Column name → pandas dtype string")
    file_size_bytes: int = Field(ge=0)


# =============================================================================
# Data quality
# =============================================================================


class ColumnProfile(BaseModel):
    """Per-column summary produced during quality scoring."""

    column_name: str
    dtype: str
    n_missing: int = Field(ge=0)
    pct_missing: float = Field(ge=0.0, le=100.0)
    n_unique: int = Field(ge=0)
    pct_unique: float = Field(ge=0.0, le=100.0)
    sample_values: list[str] = Field(
        description="Up to 5 representative non-null values cast to str for display"
    )


class QualityDimension(BaseModel):
    """
    One of the four quality dimensions (completeness / uniqueness /
    validity / consistency). Score is 0–100.
    """

    name: Literal["completeness", "uniqueness", "validity", "consistency"]
    score: float = Field(ge=0.0, le=100.0)
    reason: str = Field(
        description=(
            "Plain-English rule-generated explanation of why this score was assigned, "
            "e.g. '17.3% of values in column revenue are missing.'"
        )
    )
    evidence: EvidenceObject


class QualityReport(BaseModel):
    """Full quality report returned by score_quality()."""

    dataset_version: str
    filename: str
    n_rows: int = Field(ge=0)
    n_cols: int = Field(ge=0)
    composite_score: float = Field(ge=0.0, le=100.0)
    dimensions: list[QualityDimension]
    column_profiles: list[ColumnProfile]


# =============================================================================
# Statistical profiling
# =============================================================================


class DescriptiveStats(BaseModel):
    """
    Descriptive statistics for one numeric column.
    All values are None if the column has fewer than 2 non-null entries.
    """

    column: str
    n_valid: int = Field(description="Number of non-null values used in computation", ge=0)
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    min_val: float | None = None
    max_val: float | None = None
    q1: float | None = None
    q3: float | None = None
    skewness: float | None = None
    kurtosis: float | None = None
    evidence: EvidenceObject


class CorrelationResult(BaseModel):
    """Pearson correlation between a pair of numeric columns."""

    col_a: str
    col_b: str
    method: Literal["pearson"] = "pearson"
    coefficient: float = Field(ge=-1.0, le=1.0)
    evidence: EvidenceObject


# =============================================================================
# Anomaly detection
# =============================================================================


class AnomalyResult(BaseModel):
    """
    Anomaly finding for a single observation.
    is_anomaly=True means the observation was flagged; False means it was
    scored but not flagged (included so callers can inspect the score
    distribution for non-anomalous points if needed).
    """

    column: str
    method: Literal["iqr", "zscore", "isolation_forest"]
    is_anomaly: bool
    score: float = Field(
        description=(
            "Method-specific anomaly score (higher = more anomalous). "
            "IQR: normalised distance beyond fence. "
            "Z-score: absolute z-score. "
            "Isolation Forest: negated decision_function value (higher = more anomalous)."
        )
    )
    row_index: int = Field(description="0-based positional index in the original DataFrame", ge=0)
    value: float | int | str = Field(description="The raw value at this row/column")
    evidence: EvidenceObject


class AnomalySummary(BaseModel):
    """Aggregate anomaly results for a full dataset pass."""

    method: Literal["iqr", "zscore", "isolation_forest"]
    dataset_version: str
    columns_analysed: list[str]
    n_flagged: int = Field(ge=0)
    results: list[AnomalyResult]


# =============================================================================
# Visualisation
# =============================================================================


class ChartSpec(BaseModel):
    """
    Declarative specification for a single Plotly chart.
    chart_selector.py produces these; render_chart() consumes them.
    """

    chart_type: Literal["histogram", "box", "scatter", "heatmap", "bar"]
    title: str
    column: str | None = None
    x_col: str | None = None
    y_col: str | None = None
    anomaly_indices: list[int] = Field(
        default_factory=list,
        description="Row indices to highlight as anomalies on the chart",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional extra parameters passed to the renderer (e.g. colorscale for heatmap)",
    )


# =============================================================================
# Mission 2+ placeholders (defined here so imports don't break; fleshed out later)
# =============================================================================


class AgentInsight(BaseModel):
    """Narrative summary generated from deterministic analysis evidence."""

    summary: str
    findings: list[str] = Field(default_factory=list)
    generation_mode: Literal["deterministic", "llm"] = "deterministic"
    provider: str | None = None
    notice: str | None = None


class HypothesisResult(BaseModel):
    """Placeholder — populated in Mission 2."""

    hypothesis: str
    p_value: float | None = None
    test_used: str | None = None
    conclusion: str | None = None
    evidence: EvidenceObject | None = None


class RootCauseResult(BaseModel):
    """Placeholder — populated in Mission 2."""

    segment: str
    contribution: float | None = None
    evidence: EvidenceObject | None = None


class InsightResult(BaseModel):
    """Placeholder — populated in Mission 2."""

    text: str
    supporting_evidence: list[EvidenceObject] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
