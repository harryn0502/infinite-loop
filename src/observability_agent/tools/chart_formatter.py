"""Utilities for preparing clean chart-friendly data."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence
from langchain_core.tools import StructuredTool

NUMERIC_HINTS = [
    "latency_ms",
    "latency",
    "duration",
    "count",
    "total",
    "value",
    "score",
    "avg",
]

LABEL_HINTS = [
    "tool_name",
    "tool",
    "name",
    "run_id",
    "category",
    "type",
    "status",
]


def _is_numeric(value: Any) -> bool:
    """Return True for ints/floats (but not bool)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _select_key(
    rows: Sequence[Dict[str, Any]],
    preferred: Optional[Iterable[str]],
    hints: Iterable[str],
    predicate,
) -> Optional[str]:
    """Select the first column that satisfies predicate, with hint priority."""
    if not rows:
        return None

    def _match(columns: Iterable[str], candidates: Iterable[str]) -> Optional[str]:
        lower_columns = {col.lower(): col for col in columns}
        for candidate in candidates:
            if candidate.lower() in lower_columns:
                return lower_columns[candidate.lower()]
        return None

    first_row = rows[0]
    columns_order = list(first_row.keys())

    if preferred:
        selection = _match(columns_order, preferred)
        if selection:
            return selection

    selection = _match(columns_order, hints)
    if selection:
        return selection

    for column in columns_order:
        if predicate(first_row.get(column)):
            return column
    return None


def _select_value_key(rows: Sequence[Dict[str, Any]], preferred: Optional[List[str]]) -> Optional[str]:
    return _select_key(rows, preferred, NUMERIC_HINTS, _is_numeric)


def _select_label_key(rows: Sequence[Dict[str, Any]], preferred: Optional[List[str]]) -> Optional[str]:
    def _is_label(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    return _select_key(rows, preferred, LABEL_HINTS, _is_label)


def prepare_chart_data(
    rows: List[Dict[str, Any]],
    *,
    value_key: Optional[str] = None,
    label_key: Optional[str] = None,
    preferred_value_keys: Optional[List[str]] = None,
    preferred_label_keys: Optional[List[str]] = None,
    max_rows: int = 20,
) -> Dict[str, Any]:
    """
    Clean and normalize rows so the frontend can render consistent charts.

    Returns:
        {
            "rows": [{"label": "...", "value": 123.4}, ...],
            "metadata": {
                "label_field": "label",
                "value_field": "value",
                "label_source_column": "...",
                "value_source_column": "...",
                "rows_considered": len(rows),
                "rows_returned": <int>,
                "suggested_chart": "bar",
            }
        }
    """
    if not rows:
        return {
            "rows": [],
            "metadata": {
                "label_field": "label",
                "value_field": "value",
                "rows_considered": 0,
                "rows_returned": 0,
                "suggested_chart": "bar",
            },
        }

    value_key = value_key or _select_value_key(rows, preferred_value_keys)
    label_key = label_key or _select_label_key(rows, preferred_label_keys)

    cleaned_rows: List[Dict[str, Any]] = []
    for idx, row in enumerate(sorted(rows, key=lambda r: r.get(value_key, 0) or 0, reverse=True)):
        if idx >= max_rows:
            break
        value = row.get(value_key) if value_key else None
        if value is None or not _is_numeric(value):
            continue

        label_value = row.get(label_key) if label_key else None
        label = str(label_value) if label_value else f"Row {idx + 1}"

        cleaned_rows.append(
            {
                "label": label,
                "value": float(value),
            }
        )

    metadata = {
        "label_field": "label",
        "value_field": "value",
        "label_source_column": label_key,
        "value_source_column": value_key,
        "rows_considered": len(rows),
        "rows_returned": len(cleaned_rows),
        "suggested_chart": "bar",
    }

    # If we couldn't materialize chart rows, fall back to the originals.
    if not cleaned_rows:
        cleaned_rows = rows[:max_rows]
        metadata["label_field"] = label_key or "label"
        metadata["value_field"] = value_key or "value"
        metadata["suggested_chart"] = "table"

    return {
        "rows": cleaned_rows,
        "metadata": metadata,
    }


def _prepare_chart_data_tool(
    rows: List[Dict[str, Any]],
    value_key: Optional[str] = None,
    label_key: Optional[str] = None,
    preferred_value_keys: Optional[List[str]] = None,
    preferred_label_keys: Optional[List[str]] = None,
    max_rows: int = 20,
) -> Dict[str, Any]:
    return prepare_chart_data(
        rows,
        value_key=value_key,
        label_key=label_key,
        preferred_value_keys=preferred_value_keys,
        preferred_label_keys=preferred_label_keys,
        max_rows=max_rows,
    )


prepare_chart_data_tool = StructuredTool.from_function(
    func=_prepare_chart_data_tool,
    name="prepare_chart_data",
    description="Normalize tabular rows for charting (returns cleaned rows and metadata).",
)
