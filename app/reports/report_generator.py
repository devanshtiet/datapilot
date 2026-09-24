"""
app/reports/report_generator.py
================================
Report generator module.
STUB — expanded in Mission 2 & 4.
"""

from __future__ import annotations
from typing import Any
from app.models.pydantic import QualityReport, AnomalySummary


def generate_executive_summary(
    quality_report: QualityReport,
    anomaly_summaries: list[AnomalySummary],
) -> str:
    """
    Generate a simple text summary of dataset profiling & anomalies.
    """
    total_anomalies = sum(s.n_flagged for s in anomaly_summaries)
    return (
        f"Dataset '{quality_report.filename}' profiled with quality score "
        f"{quality_report.composite_score:.1f}/100 across {quality_report.n_rows} rows and "
        f"{quality_report.n_cols} columns. A total of {total_anomalies} anomaly instances were flagged."
    )
