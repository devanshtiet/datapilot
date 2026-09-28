"""Deterministic repair candidates and previews for the repair copilot.

The model may explain or prioritize these candidates, but it never supplies
operations or values. Every applied change is recomputed from the uploaded CSV.
"""

from __future__ import annotations

import hashlib
import io
from typing import Any

import pandas as pd


def _candidate_id(kind: str, column: str = "") -> str:
    digest = hashlib.sha256(f"{kind}\0{column}".encode("utf-8")).hexdigest()[:12]
    return f"{kind}_{digest}"


def build_candidates(df: pd.DataFrame) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for column in df.columns:
        series = df[column]
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            text = series.astype("string")
            changed = text.notna() & text.ne(text.str.strip())
            count = int(changed.sum())
            if count:
                candidates.append({
                    "id": _candidate_id("trim_text", str(column)),
                    "kind": "trim_text",
                    "column": str(column),
                    "affected_rows": count,
                    "strategy": "Remove leading and trailing whitespace; keep letter case and internal spaces.",
                    "examples": _examples(df, column, changed, lambda value: value.strip()),
                })
            normalized = text.str.replace(r"\s+", " ", regex=True)
            changed_internal = text.notna() & text.ne(normalized)
            count = int(changed_internal.sum())
            if count:
                candidates.append({
                    "id": _candidate_id("normalize_whitespace", str(column)),
                    "kind": "normalize_whitespace",
                    "column": str(column),
                    "affected_rows": count,
                    "strategy": "Replace repeated spaces, tabs, and line breaks inside text with a single space.",
                    "examples": _examples(df, column, changed_internal, lambda value: " ".join(value.split())),
                })

        missing = series.isna() | (series.astype("string").str.strip() == "")
        count = int(missing.sum())
        if not count:
            continue
        non_missing = series[~missing]
        if non_missing.empty:
            continue
        if pd.api.types.is_numeric_dtype(series):
            fill_value = float(non_missing.median())
            strategy = "Fill blank cells with this column's median."
        else:
            modes = non_missing.mode(dropna=True)
            if modes.empty or len(modes) != 1:
                continue
            fill_value = modes.iloc[0]
            if not isinstance(fill_value, (str, int, float, bool)):
                continue
            strategy = "Fill blank cells with the unique most common value in this column."
        candidates.append({
            "id": _candidate_id("fill_missing", str(column)),
            "kind": "fill_missing",
            "column": str(column),
            "affected_rows": count,
            "strategy": strategy,
            "fill_value": fill_value.item() if hasattr(fill_value, "item") else fill_value,
            "examples": _examples(df, column, missing, lambda _value: fill_value),
        })

    duplicate_mask = df.duplicated(keep="first")
    duplicate_count = int(duplicate_mask.sum())
    if duplicate_count:
        candidates.append({
            "id": _candidate_id("drop_duplicates"),
            "kind": "drop_duplicates",
            "column": None,
            "affected_rows": duplicate_count,
            "strategy": "Remove rows that exactly repeat an earlier row across every column.",
            "examples": [],
        })
    return candidates


def _examples(df: pd.DataFrame, column: Any, mask: pd.Series, replacement) -> list[dict[str, Any]]:
    result = []
    for value in df.loc[mask, column].head(4).tolist():
        before = None if pd.isna(value) else str(value)
        after = replacement(value)
        result.append({"before": before, "after": str(after)})
    return result


def preview_repairs(df: pd.DataFrame, selected_ids: list[str]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    catalog = {item["id"]: item for item in build_candidates(df)}
    if not selected_ids:
        raise ValueError("Select at least one suggested repair.")
    if len(set(selected_ids)) != len(selected_ids):
        raise ValueError("A repair was selected more than once.")
    unknown = set(selected_ids) - set(catalog)
    if unknown:
        raise ValueError("A selected repair no longer matches this dataset. Ask the copilot again.")

    repaired = df.copy(deep=True)
    operations = []
    for candidate_id in selected_ids:
        candidate = catalog[candidate_id]
        if candidate["kind"] == "trim_text":
            column = candidate["column"]
            mask = repaired[column].notna()
            repaired.loc[mask, column] = repaired.loc[mask, column].astype("string").str.strip()
        elif candidate["kind"] == "normalize_whitespace":
            column = candidate["column"]
            mask = repaired[column].notna()
            repaired.loc[mask, column] = repaired.loc[mask, column].astype("string").str.replace(r"\s+", " ", regex=True)
        elif candidate["kind"] == "fill_missing":
            column = candidate["column"]
            mask = repaired[column].isna() | (repaired[column].astype("string").str.strip() == "")
            repaired.loc[mask, column] = candidate["fill_value"]
        elif candidate["kind"] == "drop_duplicates":
            repaired = repaired.drop_duplicates(keep="first").copy()
        operations.append({key: value for key, value in candidate.items() if key != "examples"})
    return repaired, operations


def csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.StringIO(newline="")
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8-sig")
