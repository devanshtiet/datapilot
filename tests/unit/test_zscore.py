"""
tests/unit/test_zscore.py
=========================
Unit tests for Z-score anomaly detector.
"""

import pandas as pd
from app.anomaly.zscore import detect_zscore


def test_detect_zscore_injected_outlier():
    # 50 values near 0, one extreme outlier 500
    values = [1.0] * 50 + [500.0]
    df = pd.DataFrame({"val": values})
    
    summary = detect_zscore(df, "hash_zs")
    assert summary.n_flagged >= 1
    flagged_indices = [r.row_index for r in summary.results]
    assert 50 in flagged_indices
