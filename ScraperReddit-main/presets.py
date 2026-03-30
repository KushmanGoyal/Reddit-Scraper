"""
presets.py — Marketplace preset configurations.

Each preset contains the URL, CSS selectors, pagination type, and
any marketplace-specific settings needed to scrape that site.

Usage from CLI:
    python scraper.py --preset etsy
    python scraper.py --preset amazon
    python scraper.py --preset custom --url "https://example.com/sellers"

Usage from code:
    from presets import PRESETS, apply_preset
    apply_preset("etsy")
"""

from __future__ import annotations

# ─── Preset definitions ──────────────────────────────────────────────
# Each preset is a dict that overrides values in config.py at runtime.
# Add new marketplaces by adding entries here.

PRESETS: dict[str, dict] = {

    # ── Etsy (seller/shop listings) ──────────────────────────────────
    "etsy": {
        "description": "Etsy — Search results showing shops/sellers",
        "base_url": "https://www.etsy.com/search?q=handmade&explicit=1&ship_to=US",
        "pagination_type": "url_param",
        "page_param": "page",
        "selectors": {
            "seller_card": "div.v2-listing-card, div[data-listing-card], li.wt-list-unstyled",
            "seller_name": "a.shop-name, p.shop-name, span.v2-listing-card__shop, a[data-shop-name]",
            "seller_url": "a.shop-name, a[data-shop-name], a.listing-link",
            "seller_id": "[data-shop-id]",
            "seller_rating": "span.stars-svg, input.stars-svg, span[data-rating]",
            "seller_review_count": "span.review-count, span[data-reviews-count]",
            "seller_location": "span.shop-location, span[data-location]",
            "seller_description": ".shop-description, [data-shop-description]",
            "seller_join_date": "[data-join-date]",
            "categories": "a.listing-category, span.tag, a[data-category]",
            "product_count": "span.listing-count, [data-listing-count]",
            "next_page_button": "a[data-page-next], a.wt-action-group__item-container[rel='next']",
            "load_more_button": "button:has-text('Load more'), button:has-text('Show more')",
        },
    },

    # ── Amazon (third-party sellers on product pages) ────────────────
    "amazon": {
        "description": "Amazon — Marketplace sellers from product/offer listings",
        "base_url": "https://www.amazon.in/s?k=mobiles&rh=n%3A1389401031&ref=nb_sb_noss",
        "pagination_type": "url_param",
        "page_param": "startIndex",
        "selectors": {
            "seller_card": "div.a-row.a-spacing-mini.olpOffer, div[data-aod-seller-row], div.aod-information-block",
            "seller_name": "h3.olpSellerName a, a[aria-label*='seller'], #aod-offer-soldBy .a-fixed-left-grid-col a, span.a-size-small.a-color-base",
            "seller_url": "h3.olpSellerName a, a[aria-label*='seller'], #aod-offer-soldBy a",
            "seller_id": "[data-seller-id], [data-merchant-id]",
            "seller_rating": "span.olpSellerRating, i.a-icon-star-small, span[data-rating]",
            "seller_review_count": "span.a-size-small[aria-label*='rating'], span.a-size-small:has-text('ratings')",
            "seller_location": "span.olpShipFrom, div.ships-from span",
            "seller_description": "[data-seller-description]",
            "seller_join_date": "[data-join-date]",
            "categories": "a.a-link-normal.a-color-tertiary, span.a-color-tertiary",
            "product_count": "[data-product-count]",
            "next_page_button": "li.a-last a, a:has-text('Next')",
            "load_more_button": "button:has-text('Show more')",
        },
    },

    # ── eBay (seller listings / search results) ──────────────────────
    "ebay": {
        "description": "eBay — Search results with seller information",
        "base_url": "https://www.ebay.com/sch/i.html?_nkw=electronics",
        "pagination_type": "url_param",
        "page_param": "_pgn",
        "selectors": {
            "seller_card": "li.s-item, div.s-item__wrapper, div.srp-results li",
            "seller_name": "span.s-item__seller-info-text, a.s-item__seller-info, span.mbg-nw",
            "seller_url": "a.s-item__link, a.s-item__seller-info",
            "seller_id": "[data-seller-id]",
            "seller_rating": "span.s-item__etrs-text, span.seller-rating",
            "seller_review_count": "span.s-item__reviews-count, span.s-item__reviews",
            "seller_location": "span.s-item__location, span.s-item__itemLocation",
            "seller_description": "span.s-item__subtitle",
            "seller_join_date": "[data-join-date]",
            "categories": "a.s-item__category-col, span.s-item__dynamic",
            "product_count": "[data-product-count]",
            "next_page_button": "a.pagination__next, a[aria-label='Go to next search page']",
            "load_more_button": "button:has-text('Show more')",
        },
    },

    # ── Reddit (demo/testing — posts as "sellers") ───────────────────
    "reddit": {
        "description": "Reddit — Subreddit posts (demo mode, posts act as sellers)",
        "base_url": "https://www.reddit.com/r/Entrepreneur/",
        "pagination_type": "infinite_scroll",
        "page_param": "page",
        "use_dom_extraction": True,  # Reddit uses Shadow DOM, needs JS extraction
        "selectors": {
            "seller_card": "shreddit-post, div[data-testid='post-container'], article",
            "seller_name": "a[slot='title'], a[data-testid='post-title'], h3 a",
            "seller_url": "a[slot='title'], a[data-testid='post-title'], h3 a",
            "seller_id": "[data-testid='post-id']",
            "seller_rating": "[data-testid='rating'], .rating",
            "seller_review_count": "[data-testid='review-count'], .review-count",
            "seller_location": "[data-testid='location'], .seller-location",
            "seller_description": "[data-testid='description'], .seller-bio",
            "seller_join_date": "[data-testid='join-date'], .join-date",
            "categories": "span.flair, flair-pill",
            "product_count": "[data-testid='product-count'], .product-count",
            "next_page_button": "button[aria-label='Next'], a.next, .pagination-next",
            "load_more_button": "button:has-text('Load More'), button:has-text('Show more')",
        },
    },

    # ── Books to Scrape (demo/testing — guaranteed to work) ────────────
    "books": {
        "description": "Books to Scrape — Free sandbox site, perfect for testing (books.toscrape.com)",
        "base_url": "https://books.toscrape.com/",
        "pagination_type": "next_button",
        "page_param": "page",
        "selectors": {
            "seller_card": "article.product_pod",
            "seller_name": "h3 a",
            "seller_url": "h3 a",
            "seller_id": "[data-id]",
            "seller_rating": ".star-rating",
            "seller_review_count": "[data-reviews]",
            "seller_location": "[data-location]",
            "seller_description": "[data-description]",
            "seller_join_date": "[data-join-date]",
            "categories": ".side_categories ul li ul li a",
            "product_count": ".price_color",
            "next_page_button": "li.next a",
            "load_more_button": "button:has-text('Load more')",
        },
    },

    # ── Custom (user provides their own URL and uses default selectors) ─
    "custom": {
        "description": "Custom — Provide your own URL via --url flag",
        "base_url": "",
        "pagination_type": "url_param",
        "page_param": "page",
        "selectors": {
            "seller_card": "[data-seller], .seller-card, .product-card, article, .listing-card, li.result",
            "seller_name": "h2 a, h3 a, h4 a, .title a, [data-name], .seller-name",
            "seller_url": "h2 a, h3 a, h4 a, .title a, a.listing-link",
            "seller_id": "[data-seller-id], [data-id]",
            "seller_rating": ".rating, .stars, [data-rating], span[class*='star']",
            "seller_review_count": ".review-count, .reviews, [data-reviews]",
            "seller_location": ".location, .seller-location, [data-location]",
            "seller_description": ".description, .bio, .seller-bio, [data-description]",
            "seller_join_date": ".join-date, [data-join-date]",
            "categories": ".category, .tag, .badge, [data-category]",
            "product_count": ".product-count, .listing-count, [data-count]",
            "next_page_button": "a.next, a[rel='next'], button:has-text('Next'), .pagination-next a",
            "load_more_button": "button:has-text('Load more'), button:has-text('Show more')",
        },
    },
}


def apply_preset(preset_name: str) -> dict:
    """
    Look up a preset by name and return its config dict.

    Raises ValueError if the preset is not found.
    """
    key = preset_name.lower().strip()
    if key not in PRESETS:
        available = ", ".join(sorted(PRESETS.keys()))
        raise ValueError(
            f"Unknown preset '{preset_name}'. Available presets: {available}"
        )
    return PRESETS[key]


def list_presets() -> list[tuple[str, str]]:
    """Return a list of (name, description) for all available presets."""
    return [(name, p["description"]) for name, p in sorted(PRESETS.items())]
