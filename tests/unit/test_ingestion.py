"""
tests/unit/test_ingestion.py
=============================
Unit tests for data ingestion module.
"""

import io
import pytest
import pandas as pd
from app.data.ingestion import load_file, IngestionError


def test_load_file_csv_bytes():
    csv_data = b"col1,col2\n1,10\n2,20\n3,30\n"
    df, result = load_file(csv_data, "test.csv")
    
    assert len(df) == 3
    assert len(df.columns) == 2
    assert result.n_rows == 3
    assert result.n_cols == 2
    assert len(result.dataset_version) == 64  # SHA-256 length


def test_load_file_unsupported_format():
    with pytest.raises(IngestionError, match="Unsupported file format"):
        load_file(b"some content", "test.txt")


def test_load_file_empty_csv():
    with pytest.raises(IngestionError):
        load_file(b"", "empty.csv")
