"""
tests/unit/test_iqr.py
======================
Unit tests for IQR anomaly detector.
"""

import pandas as pd
from app.anomaly.iqr import detect_iqr


def test_detect_iqr_injected_outlier():
    # Normal distribution around 10, with one 999 outlier
    values = [10.0, 11.0, 9.5, 10.5, 10.2, 9.8, 10.1, 10.4, 9.9, 999.0]
    df = pd.DataFrame({"val": values})
    
    summary = detect_iqr(df, "hash_iqr")
    assert summary.n_flagged == 1
    assert summary.results[0].row_index == 9
    assert summary.results[0].value == 999.0
    assert summary.results[0].is_anomaly is True
    assert summary.results[0].evidence.confidence == 0.80
