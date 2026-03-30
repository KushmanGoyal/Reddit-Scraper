"""
parser.py — HTML parsing and data extraction logic.

Responsible for taking raw HTML (or a BeautifulSoup object) and extracting
structured seller data according to the configured CSS selectors.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from bs4 import BeautifulSoup, Tag

import config

logger = logging.getLogger("scraper.parser")


# ─── Helpers ──────────────────────────────────────────────────────────

def _clean_text(text: str | None) -> str:
    """Strip whitespace, collapse internal spaces, remove stray HTML entities."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _safe_select_one(card: Tag, selector: str) -> Tag | None:
    """Try each comma-separated selector and return the first match."""
    for sel in selector.split(","):
        sel = sel.strip()
        try:
            result = card.select_one(sel)
            if result:
                return result
        except Exception:
            continue
    return None


def _safe_select_all(card: Tag, selector: str) -> list[Tag]:
    """Try each comma-separated selector and return all matches."""
    results: list[Tag] = []
    for sel in selector.split(","):
        sel = sel.strip()
        try:
            found = card.select(sel)
            results.extend(found)
        except Exception:
            continue
    return results


# ─── Public API ───────────────────────────────────────────────────────

def parse_seller_card(card: Tag) -> dict[str, Any] | None:
    """
    Extract seller information from a single seller card element.

    Returns a dict with all available fields, or *None* if the card
    does not contain the minimum required data (seller_name).
    """
    selectors = config.SELECTORS

    # --- Required fields ---------------------------------------------------
    name_el = _safe_select_one(card, selectors["seller_name"])
    if not name_el:
        return None

    seller_name = _clean_text(name_el.get_text())
    if not seller_name:
        return None

    # Seller URL — prefer href on the element, fall back to parent <a>
    url_el = _safe_select_one(card, selectors["seller_url"])
    seller_url = ""
    if url_el:
        href = url_el.get("href", "")
        if href:
            seller_url = href if href.startswith("http") else f"https://www.reddit.com{href}"

    # --- Optional fields ---------------------------------------------------
    seller_id = ""
    id_el = _safe_select_one(card, selectors["seller_id"])
    if id_el:
        seller_id = _clean_text(id_el.get_text()) or id_el.get("data-id", "")

    seller_rating = ""
    rating_el = _safe_select_one(card, selectors["seller_rating"])
    if rating_el:
        seller_rating = _clean_text(rating_el.get_text())

    seller_review_count = ""
    review_el = _safe_select_one(card, selectors["seller_review_count"])
    if review_el:
        seller_review_count = _clean_text(review_el.get_text())

    seller_location = ""
    loc_el = _safe_select_one(card, selectors["seller_location"])
    if loc_el:
        seller_location = _clean_text(loc_el.get_text())

    seller_description = ""
    desc_el = _safe_select_one(card, selectors["seller_description"])
    if desc_el:
        seller_description = _clean_text(desc_el.get_text())

    seller_join_date = ""
    join_el = _safe_select_one(card, selectors["seller_join_date"])
    if join_el:
        seller_join_date = _clean_text(join_el.get_text())

    # --- Categories --------------------------------------------------------
    cat_elements = _safe_select_all(card, selectors["categories"])
    categories = list({_clean_text(c.get_text()) for c in cat_elements if _clean_text(c.get_text())})

    # --- Product count -----------------------------------------------------
    product_count = ""
    pc_el = _safe_select_one(card, selectors["product_count"])
    if pc_el:
        product_count = _clean_text(pc_el.get_text())

    return {
        "seller_name": seller_name,
        "seller_url": seller_url,
        "seller_id": seller_id,
        "seller_rating": seller_rating,
        "seller_review_count": seller_review_count,
        "seller_location": seller_location,
        "seller_description": seller_description,
        "seller_join_date": seller_join_date,
        "categories": "; ".join(sorted(categories)) if categories else "",
        "product_count": product_count,
    }


def parse_page(html: str) -> list[dict[str, Any]]:
    """
    Parse a full page of HTML and return a list of seller dicts.

    Deduplicates sellers by (seller_name, seller_url) within this page.
    """
    soup = BeautifulSoup(html, "lxml")
    cards = _safe_select_all(soup, config.SELECTORS["seller_card"])
    logger.debug("Found %d raw card elements on page", len(cards))

    seen: set[tuple[str, str]] = set()
    sellers: list[dict[str, Any]] = []
    skipped = 0

    for card in cards:
        data = parse_seller_card(card)
        if data is None:
            skipped += 1
            continue
        key = (data["seller_name"], data["seller_url"])
        if key in seen:
            continue
        seen.add(key)
        sellers.append(data)

    logger.info(
        "Parsed page: %d cards → %d sellers (%d skipped, %d dupes)",
        len(cards), len(sellers), skipped, len(cards) - skipped - len(sellers),
    )
    return sellers
