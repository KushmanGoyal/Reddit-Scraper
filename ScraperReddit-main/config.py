"""
config.py — Central configuration for the Marketplace Seller Data Extraction Tool.

All tuneable parameters live here so the scraper can be adapted
to any marketplace by editing a single file.
"""

import logging
import os

# ─── Logging ──────────────────────────────────────────────────────────
# Log file is written next to the output CSV for easy access.
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "scraper.log")
LOG_LEVEL = logging.INFO

# ─── Target Marketplace ──────────────────────────────────────────────
# Base URL of the marketplace seller listing page.
# Change this to point at whatever marketplace you want to scrape.
# Default: Reddit subreddit (posts act as "sellers" for demo purposes)
BASE_URL = "https://www.reddit.com/r/Entrepreneur/"

# ─── Selectors ────────────────────────────────────────────────────────
# CSS selectors used to locate elements on the page.
# Adjust these when targeting a different marketplace.

SELECTORS = {
    # Container that wraps a single seller card / row on the listing page
    "seller_card": "shreddit-post, div[data-testid='post-container'], article",

    # Within a seller card — required fields
    "seller_name": "a[slot='title'], a[data-testid='post-title'], h3 a",
    "seller_url": "a[slot='title'], a[data-testid='post-title'], h3 a",

    # Within a seller card — optional fields
    "seller_id": "[data-testid='post-id']",
    "seller_rating": "[data-testid='rating'], .rating",
    "seller_review_count": "[data-testid='review-count'], .review-count",
    "seller_location": "[data-testid='location'], .seller-location",
    "seller_description": "[data-testid='description'], .seller-bio",
    "seller_join_date": "[data-testid='join-date'], .join-date",

    # Category & product information
    "categories": "span.flair, flair-pill",
    "product_count": "[data-testid='product-count'], .product-count",

    # Pagination
    "next_page_button": "button[aria-label='Next'], a.next, .pagination-next",
    "load_more_button": "button:has-text('Load More'), button:has-text('Show more')",
}

# ─── Pagination ───────────────────────────────────────────────────────
# Maximum number of pages to traverse (safety limit).
MAX_PAGES = 10

# Type of pagination the marketplace uses.
# Options: "url_param", "infinite_scroll", "load_more", "next_button"
PAGINATION_TYPE = "infinite_scroll"

# URL parameter name for URL-based pagination (only used when PAGINATION_TYPE == "url_param").
PAGE_PARAM = "page"

# ─── Timing & Delays ─────────────────────────────────────────────────
# Seconds to wait for page content to load before scraping.
PAGE_LOAD_WAIT = 5

# Seconds to wait between page navigations (be respectful to the server).
REQUEST_DELAY = 3

# Timeout (ms) for waiting for dynamic elements to appear.
ELEMENT_TIMEOUT = 10000

# ─── Output ───────────────────────────────────────────────────────────
# Path for the exported CSV file.
OUTPUT_CSV = "output/sellers.csv"

# ─── Browser ──────────────────────────────────────────────────────────
# Run the browser in headless mode (True) or visible mode (False).
HEADLESS = True

# User agent to identify the scraper.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
