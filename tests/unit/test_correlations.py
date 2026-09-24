"""
tests/unit/test_correlations.py
================================
Unit tests for correlation matrix module.
"""

import pandas as pd
from app.analytics.correlations import compute_correlation_matrix


def test_compute_correlation_matrix():
    df = pd.DataFrame({
        "x": [1, 2, 3, 4, 5],
        "y": [2, 4, 6, 8, 10],  # perfect positive linear correlation
    })
    corrs = compute_correlation_matrix(df, "hash_corr")
    
    assert len(corrs) == 1
    c = corrs[0]
    assert c.col_a == "x"
    assert c.col_b == "y"
    assert abs(c.coefficient - 1.0) < 1e-5
    assert c.evidence.rows_used == 5
