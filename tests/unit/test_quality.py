"""
tests/unit/test_quality.py
===========================
Unit tests for data quality scoring engine.
"""

import pandas as pd
import numpy as np
from app.data.quality import score_quality


def test_quality_score_clean_data():
    df = pd.DataFrame({
        "a": [1, 2, 3, 4, 5],
        "b": [10.0, 20.0, 30.0, 40.0, 50.0],
        "c": ["cat", "dog", "bird", "fish", "lion"],
    })
    report = score_quality(df, "dummy_hash_123", "clean.csv")
    
    assert report.composite_score >= 90.0
    assert len(report.dimensions) == 4
    for dim in report.dimensions:
        assert dim.evidence.metric.endswith("_score")
        assert dim.evidence.dataset_version == "dummy_hash_123"


def test_quality_score_messy_data():
    df_clean = pd.DataFrame({
        "a": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "b": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
    })
    
    df_messy = pd.DataFrame({
        "a": [1, 2, np.nan, np.nan, 5, 5, 5, 5, 5, 5],  # missing + constant values
        "b": [10.0, 20.0, 30.0, 40.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0],  # duplicate rows
    })
    
    rep_clean = score_quality(df_clean, "hash1", "clean.csv")
    rep_messy = score_quality(df_messy, "hash2", "messy.csv")
    
    # Messy dataset must score lower than clean dataset
    assert rep_messy.composite_score < rep_clean.composite_score
