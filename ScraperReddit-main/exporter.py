"""
exporter.py — Data export module.

Handles writing the extracted seller data to structured output formats.
Currently supports CSV (required by PRD) with Pandas.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import pandas as pd

import config

logger = logging.getLogger("scraper.exporter")


# ─── Column ordering (matches PRD output spec) ───────────────────────

COLUMNS = [
    "seller_name",
    "seller_url",
    "seller_id",
    "seller_rating",
    "seller_review_count",
    "seller_location",
    "seller_description",
    "seller_join_date",
    "categories",
    "product_count",
]


def export_to_csv(
    sellers: list[dict[str, Any]],
    output_path: str | None = None,
) -> str:
    """
    Export a list of seller dicts to a UTF-8 CSV file.

    Parameters
    ----------
    sellers : list[dict]
        Each dict must have at least ``seller_name`` and ``seller_url``.
    output_path : str, optional
        Destination file path.  Defaults to ``config.OUTPUT_CSV``.

    Returns
    -------
    str
        Absolute path to the written CSV file.
    """
    output_path = output_path or config.OUTPUT_CSV

    # Ensure the output directory exists.
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    df = pd.DataFrame(sellers)

    # Keep only columns that exist in the data; order to match spec.
    ordered_cols = [c for c in COLUMNS if c in df.columns]
    df = df[ordered_cols]

    # Drop exact duplicate rows.
    rows_before = len(df)
    df.drop_duplicates(subset=["seller_name", "seller_url"], keep="first", inplace=True)
    rows_after = len(df)
    if rows_before != rows_after:
        logger.info("Deduplication removed %d duplicate rows", rows_before - rows_after)

    # Replace NaN / None with empty string for cleanliness.
    df.fillna("", inplace=True)

    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    abs_path = os.path.abspath(output_path)
    logger.info("CSV written: %d rows → %s", len(df), abs_path)
    return abs_path


def preview_data(sellers: list[dict[str, Any]], max_rows: int = 10) -> pd.DataFrame:
    """Return a Pandas DataFrame preview (useful for debugging / display)."""
    df = pd.DataFrame(sellers)
    ordered_cols = [c for c in COLUMNS if c in df.columns]
    return df[ordered_cols].head(max_rows)
