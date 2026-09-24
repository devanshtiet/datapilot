"""
app/data/ingestion.py
=====================
Responsible for loading CSV / Excel files from disk (or a file-like object),
computing a stable dataset_version (SHA-256 of raw bytes), and returning a
parsed DataFrame alongside an IngestionResult Pydantic model.

Nothing in this module touches the LLM or makes network calls.
"""

from __future__ import annotations

import hashlib
import io
import logging
from pathlib import Path

import pandas as pd

from app.models.pydantic import IngestionResult
from config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class IngestionError(Exception):
    """Raised when a file cannot be ingested for any reason."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_file(
    source: str | Path | bytes | io.IOBase,
    filename: str,
) -> tuple[pd.DataFrame, IngestionResult]:
    """
    Load a CSV or Excel file and return a parsed DataFrame plus metadata.

    Parameters
    ----------
    source:
        One of:
        - A file path (str or Path) to read from disk.
        - Raw bytes (e.g. from an st.file_uploader buffer).
        - A file-like object (io.BytesIO / io.BufferedReader).
    filename:
        Original filename including extension — used to determine the parser.

    Returns
    -------
    (df, ingestion_result)
        df: pandas DataFrame with original dtypes preserved.
        ingestion_result: IngestionResult Pydantic model.

    Raises
    ------
    IngestionError
        If the file is too large, unreadable, or an unsupported format.
    """
    try:
        raw_bytes, file_size = _read_to_bytes(source, filename)
        _check_size(file_size, filename)
        dataset_version = _sha256(raw_bytes)
        df = _parse(raw_bytes, filename)
        result = IngestionResult(
            filename=filename,
            dataset_version=dataset_version,
            n_rows=len(df),
            n_cols=len(df.columns),
            column_names=list(df.columns),
            dtypes={col: str(df[col].dtype) for col in df.columns},
            file_size_bytes=file_size,
        )
        logger.info(
            "Ingested '%s': %d rows × %d cols, version=%s",
            filename,
            result.n_rows,
            result.n_cols,
            dataset_version[:8],
        )
        return df, result
    except IngestionError:
        raise
    except Exception as exc:
        logger.exception("Unexpected error ingesting '%s'", filename)
        raise IngestionError(f"Failed to ingest '{filename}': {exc}") from exc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_to_bytes(
    source: str | Path | bytes | io.IOBase,
    filename: str,
) -> tuple[bytes, int]:
    """Normalise any source type to raw bytes."""
    if isinstance(source, bytes):
        return source, len(source)
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise IngestionError(f"File not found: {path}")
        raw = path.read_bytes()
        return raw, len(raw)
    # file-like object
    source.seek(0)  # type: ignore[union-attr]
    raw = source.read()  # type: ignore[union-attr]
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    return raw, len(raw)


def _check_size(file_size: int, filename: str) -> None:
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if file_size > max_bytes:
        raise IngestionError(
            f"'{filename}' is {file_size / 1024 / 1024:.1f} MB, "
            f"which exceeds the {settings.max_upload_mb} MB limit."
        )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse(raw_bytes: bytes, filename: str) -> pd.DataFrame:
    """Choose the right parser based on file extension."""
    lower = filename.lower()
    buf = io.BytesIO(raw_bytes)

    if lower.endswith(".csv"):
        return _parse_csv(buf, filename)
    if lower.endswith(".xlsx"):
        return _parse_excel(buf, filename, engine="openpyxl")
    if lower.endswith(".xls"):
        return _parse_excel(buf, filename, engine="xlrd")
    raise IngestionError(
        f"Unsupported file format: '{filename}'. "
        "Supported formats: .csv, .xlsx, .xls"
    )


def _parse_csv(buf: io.BytesIO, filename: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(buf, low_memory=False)
    except pd.errors.EmptyDataError as exc:
        raise IngestionError(f"'{filename}' is empty or has no parseable data.") from exc
    except Exception as exc:
        raise IngestionError(f"CSV parse error in '{filename}': {exc}") from exc
    _validate_nonempty(df, filename)
    return df


def _parse_excel(buf: io.BytesIO, filename: str, engine: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(buf, engine=engine)
    except Exception as exc:
        raise IngestionError(f"Excel parse error in '{filename}': {exc}") from exc
    _validate_nonempty(df, filename)
    return df


def _validate_nonempty(df: pd.DataFrame, filename: str) -> None:
    if df.empty or len(df.columns) == 0:
        raise IngestionError(f"'{filename}' produced an empty DataFrame after parsing.")
