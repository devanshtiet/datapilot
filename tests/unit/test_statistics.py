"""
tests/unit/test_statistics.py
==============================
Unit tests for descriptive statistics module.
"""

import pandas as pd
import numpy as np
from app.analytics.statistics import compute_descriptive_stats


def test_compute_descriptive_stats():
    df = pd.DataFrame({
        "val": [10.0, 20.0, 30.0, 40.0, 50.0],
        "cat": ["a", "b", "c", "d", "e"],
    })
    stats = compute_descriptive_stats(df, "hash_stat")
    
    assert len(stats) == 1
    s = stats[0]
    assert s.column == "val"
    assert s.mean == 30.0
    assert s.median == 30.0
    assert s.min_val == 10.0
    assert s.max_val == 50.0
    assert s.evidence.rows_used == 5
    assert s.evidence.source_tool == "app.analytics.statistics.compute_descriptive_stats"
