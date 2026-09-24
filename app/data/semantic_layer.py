"""
app/data/semantic_layer.py
===========================
Semantic layer mapping columns to business entities and domain semantics.
STUB — expanded in Mission 2 & 3.
"""

from __future__ import annotations
from typing import Any
import pandas as pd


def infer_column_semantics(df: pd.DataFrame) -> dict[str, str]:
    """
    Infer basic semantic type for each column (e.g. identifier, metric, dimension, temporal).
    """
    semantics = {}
    for col in df.columns:
        dtype = str(df[col].dtype)
        if "int" in dtype or "float" in dtype:
            semantics[col] = "metric"
        elif "date" in dtype or "time" in dtype:
            semantics[col] = "temporal"
        else:
            semantics[col] = "dimension"
    return semantics
