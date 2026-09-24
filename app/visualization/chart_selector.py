"""
app/visualization/chart_selector.py
=====================================
Rule-based chart selector and Plotly renderer.

select_charts() inspects the QualityReport, stats, and anomaly results
and returns a list of ChartSpec objects describing what to render.
render_chart() turns a ChartSpec into a live Plotly Figure.

Rules (in priority order):
  1. Correlation heatmap — if ≥2 numeric columns exist.
  2. For each numeric column with flagged anomalies:
        a. Box plot (with anomaly points highlighted in red)
        b. Histogram (with KDE-style overlay via Plotly)
  3. For highly correlated pairs (|r| > 0.5): scatter plot.
  4. For categorical columns: bar chart of top-20 value counts.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.models.pydantic import (
    AnomalySummary,
    ChartSpec,
    CorrelationResult,
    DescriptiveStats,
    QualityReport,
)

logger = logging.getLogger(__name__)

# Colour palette
_NORMAL_COLOUR = "#4C9BE8"
_ANOMALY_COLOUR = "#FF4B4B"
_HEATMAP_COLOURSCALE = "RdBu"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def select_charts(
    df: pd.DataFrame,
    quality_report: QualityReport,
    anomaly_summaries: list[AnomalySummary],
    correlation_results: list[CorrelationResult],
    stats: list[DescriptiveStats],
) -> list[ChartSpec]:
    """
    Produce a list of ChartSpec objects for the dataset.

    Parameters
    ----------
    df:                   The parsed DataFrame.
    quality_report:       From score_quality().
    anomaly_summaries:    List of AnomalySummary (one per method).
    correlation_results:  From compute_correlation_matrix().
    stats:                From compute_descriptive_stats().

    Returns
    -------
    Ordered list of ChartSpec — the Streamlit UI renders them in this order.
    """
    specs: list[ChartSpec] = []
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    # ── 1. Correlation heatmap ───────────────────────────────────────────────
    if len(numeric_cols) >= 2 and correlation_results:
        specs.append(
            ChartSpec(
                chart_type="heatmap",
                title="Pearson Correlation Matrix",
                metadata={"colorscale": _HEATMAP_COLOURSCALE},
            )
        )

    # ── 2. Per-column: box + histogram for numeric cols with anomalies ───────
    # Build a lookup: column → set of flagged row indices (union across methods)
    flagged_by_col: dict[str, set[int]] = {}
    for summary in anomaly_summaries:
        for result in summary.results:
            col = result.column if result.column != "__multivariate__" else None
            if col and col in numeric_cols:
                flagged_by_col.setdefault(col, set()).add(result.row_index)

    for col in numeric_cols:
        anomaly_indices = sorted(flagged_by_col.get(col, set()))
        specs.append(
            ChartSpec(
                chart_type="box",
                title=f"Box Plot — {col}",
                column=col,
                anomaly_indices=anomaly_indices,
            )
        )
        specs.append(
            ChartSpec(
                chart_type="histogram",
                title=f"Distribution — {col}",
                column=col,
                anomaly_indices=anomaly_indices,
            )
        )

    # ── 3. Scatter for highly correlated pairs ───────────────────────────────
    high_corr = [r for r in correlation_results if abs(r.coefficient) > 0.5]
    # Collect multivariate IF anomaly row indices
    if_indices: set[int] = set()
    for summary in anomaly_summaries:
        if summary.method == "isolation_forest":
            if_indices = {r.row_index for r in summary.results}

    for corr in high_corr[:5]:  # cap at 5 scatter plots to avoid overwhelming UI
        specs.append(
            ChartSpec(
                chart_type="scatter",
                title=f"Scatter — {corr.col_a} vs {corr.col_b} (r={corr.coefficient:.2f})",
                x_col=corr.col_a,
                y_col=corr.col_b,
                anomaly_indices=sorted(if_indices),
            )
        )

    # ── 4. Bar charts for categorical columns ────────────────────────────────
    for col in cat_cols[:5]:  # cap at 5
        specs.append(
            ChartSpec(
                chart_type="bar",
                title=f"Value Counts — {col}",
                column=col,
            )
        )

    logger.info("Chart selector produced %d chart spec(s)", len(specs))
    return specs


def render_chart(spec: ChartSpec, df: pd.DataFrame) -> go.Figure:
    """
    Render a ChartSpec into a Plotly Figure.

    Parameters
    ----------
    spec: ChartSpec describing what to render.
    df:   The DataFrame to visualise.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    try:
        if spec.chart_type == "heatmap":
            return _render_heatmap(df, spec)
        if spec.chart_type == "box":
            return _render_box(df, spec)
        if spec.chart_type == "histogram":
            return _render_histogram(df, spec)
        if spec.chart_type == "scatter":
            return _render_scatter(df, spec)
        if spec.chart_type == "bar":
            return _render_bar(df, spec)
        raise ValueError(f"Unknown chart_type: {spec.chart_type}")
    except Exception as exc:
        logger.exception("Failed to render chart '%s': %s", spec.title, exc)
        fig = go.Figure()
        fig.add_annotation(text=f"Chart error: {exc}", x=0.5, y=0.5, showarrow=False)
        return fig


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _render_heatmap(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    numeric_df = df.select_dtypes(include="number")
    corr_matrix = numeric_df.corr(method="pearson")
    colorscale = spec.metadata.get("colorscale", _HEATMAP_COLOURSCALE)

    fig = go.Figure(
        go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns.tolist(),
            y=corr_matrix.index.tolist(),
            colorscale=colorscale,
            zmin=-1,
            zmax=1,
            text=corr_matrix.round(2).values,
            texttemplate="%{text}",
        )
    )
    fig.update_layout(
        title=spec.title,
        xaxis_title="",
        yaxis_title="",
        height=max(350, 40 * len(corr_matrix)),
    )
    return _apply_theme(fig)


def _render_box(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    col = spec.column
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not in DataFrame")

    series = df[col].dropna()
    normal_mask = ~series.index.isin(spec.anomaly_indices)
    anomaly_mask = series.index.isin(spec.anomaly_indices)

    fig = go.Figure()
    fig.add_trace(
        go.Box(
            y=series.values,
            name=col,
            marker_color=_NORMAL_COLOUR,
            boxpoints="outliers",
            jitter=0.3,
        )
    )
    if any(anomaly_mask):
        fig.add_trace(
            go.Scatter(
                y=series[anomaly_mask].values,
                mode="markers",
                marker=dict(color=_ANOMALY_COLOUR, size=10, symbol="x"),
                name="Flagged anomaly",
            )
        )
    fig.update_layout(title=spec.title, yaxis_title=col, showlegend=True)
    return _apply_theme(fig)


def _render_histogram(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    col = spec.column
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not in DataFrame")

    series = df[col].dropna()
    normal_vals = series[~series.index.isin(spec.anomaly_indices)]
    anomaly_vals = series[series.index.isin(spec.anomaly_indices)]

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=normal_vals.values,
            name="Normal",
            marker_color=_NORMAL_COLOUR,
            opacity=0.75,
        )
    )
    if len(anomaly_vals) > 0:
        fig.add_trace(
            go.Scatter(
                x=anomaly_vals.values,
                y=[0] * len(anomaly_vals),
                mode="markers",
                marker=dict(color=_ANOMALY_COLOUR, size=12, symbol="x"),
                name="Flagged anomaly",
            )
        )
    fig.update_layout(
        title=spec.title,
        xaxis_title=col,
        yaxis_title="Count",
        barmode="overlay",
        showlegend=True,
    )
    return _apply_theme(fig)


def _render_scatter(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    x_col, y_col = spec.x_col, spec.y_col
    if x_col not in df.columns or y_col not in df.columns:
        raise ValueError(f"Columns '{x_col}' or '{y_col}' not in DataFrame")

    pair = df[[x_col, y_col]].dropna()
    normal_mask = ~pair.index.isin(spec.anomaly_indices)
    anomaly_mask = pair.index.isin(spec.anomaly_indices)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=pair.loc[normal_mask, x_col],
            y=pair.loc[normal_mask, y_col],
            mode="markers",
            marker=dict(color=_NORMAL_COLOUR, opacity=0.7, size=6),
            name="Normal",
        )
    )
    if any(anomaly_mask):
        fig.add_trace(
            go.Scatter(
                x=pair.loc[anomaly_mask, x_col],
                y=pair.loc[anomaly_mask, y_col],
                mode="markers",
                marker=dict(color=_ANOMALY_COLOUR, size=10, symbol="x"),
                name="Flagged anomaly (IF)",
            )
        )
    fig.update_layout(title=spec.title, xaxis_title=x_col, yaxis_title=y_col, showlegend=True)
    return _apply_theme(fig)


def _render_bar(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    col = spec.column
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not in DataFrame")

    counts = df[col].value_counts().head(20)
    fig = go.Figure(
        go.Bar(
            x=counts.index.astype(str).tolist(),
            y=counts.values.tolist(),
            marker_color=_NORMAL_COLOUR,
        )
    )
    fig.update_layout(title=spec.title, xaxis_title=col, yaxis_title="Count")
    return _apply_theme(fig)


def _apply_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13),
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig
