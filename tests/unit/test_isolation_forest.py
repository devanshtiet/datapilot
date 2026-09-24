"""
tests/unit/test_isolation_forest.py
====================================
Unit tests for Isolation Forest anomaly detector.
"""

import numpy as np
import pandas as pd
from app.anomaly.isolation_forest import detect_isolation_forest


def test_detect_isolation_forest():
    np.random.seed(42)
    x = np.random.normal(0, 1, 100)
    y = np.random.normal(0, 1, 100)
    
    # Inject 2 extreme multivariate outliers
    x[10] = 50.0
    y[10] = 50.0
    x[50] = -40.0
    y[50] = -40.0
    
    df = pd.DataFrame({"feat_x": x, "feat_y": y})
    summary = detect_isolation_forest(df, "hash_if")
    
    assert summary.n_flagged > 0
    flagged_rows = [r.row_index for r in summary.results]
    assert 10 in flagged_rows or 50 in flagged_rows
