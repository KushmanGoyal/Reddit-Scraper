"""
scraper.py — Main entry point for the Marketplace Seller Data Extraction Tool.

Orchestrates:
  1. Browser launch via Playwright
  2. Page navigation & pagination
  3. HTML capture → parser.py  (or direct DOM extraction for shadow-DOM sites)
  4. Data aggregation → exporter.py

Usage:
    python scraper.py --preset etsy              # scrape Etsy with default search
    python scraper.py --preset amazon --pages 3  # scrape Amazon, 3 pages max
    python scraper.py --preset custom --url URL  # scrape any URL with generic selectors
    python scraper.py --url <URL>                # override the target URL (uses config.py)
    python scraper.py --pages 5                  # limit pages to scrape
    python scraper.py --output out.csv           # custom output path
    python scraper.py --visible                  # run browser in visible (non-headless) mode
    python scraper.py --list-presets             # show available marketplace presets
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from typing import Any

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

import config
from parser import parse_page
from exporter import export_to_csv, preview_data
from presets import apply_preset, list_presets


# ─── Logging setup ────────────────────────────────────────────────────

logger = logging.getLogger("scraper")
logger.setLevel(config.LOG_LEVEL)

# File handler — detailed log for debugging
_file_handler = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
)
logger.addHandler(_file_handler)

# Console handler — warnings and above go to stderr alongside Rich output
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.WARNING)
_console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(_console_handler)


console = Console()

# ─── Constants ────────────────────────────────────────────────────────

MAX_RETRIES = 3          # Max retries for navigation / network failures
RETRY_BACKOFF = 5        # Seconds to wait between retries


# ─── Human-like delay helpers ─────────────────────────────────────────

def _human_delay(low: float = 1.0, high: float = 3.5) -> None:
    """Sleep for a randomized duration to mimic human browsing speed."""
    delay = random.uniform(low, high)
    logger.debug("Human delay: %.1fs", delay)
    time.sleep(delay)


def _simulate_human_behavior(page: Page) -> None:
    """Perform random mouse movements and scrolls to look human."""
    if not _is_page_alive(page):
        return
    try:
        # Random mouse move
        x = random.randint(200, 1200)
        y = random.randint(200, 600)
        page.mouse.move(x, y)
        _human_delay(0.3, 0.8)

        # Small random scroll
        scroll_y = random.randint(100, 400)
        page.mouse.wheel(0, scroll_y)
        _human_delay(0.5, 1.5)
    except Exception:
        pass  # Non-critical — don't crash if this fails


# ─── Browser helpers ──────────────────────────────────────────────────

def _launch_browser(playwright, headless: bool) -> tuple[Browser, BrowserContext, Page]:
    """Launch Chromium with comprehensive stealth settings and return (browser, context, page)."""
    logger.info("Launching Chromium (headless=%s)", headless)
    browser = playwright.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--window-size=1920,1080",
        ],
    )
    # Randomize viewport slightly to avoid fingerprinting
    vp_width = 1920 + random.randint(-20, 20)
    vp_height = 1080 + random.randint(-10, 10)
    context = browser.new_context(
        user_agent=config.USER_AGENT,
        viewport={"width": vp_width, "height": vp_height},
        locale="en-US",
        timezone_id="America/New_York",
        permissions=["geolocation"],
        color_scheme="light",
    )
    # Comprehensive stealth: mask all common automation indicators
    context.add_init_script("""
        // ── Core automation flags ─────────────────────────
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        delete navigator.__proto__.webdriver;

        // ── Languages & plugins ───────────────────────────
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                { name: 'Native Client', filename: 'internal-nacl-plugin' },
            ]
        });
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => [
                { type: 'application/pdf', suffixes: 'pdf' },
                { type: 'application/x-nacl', suffixes: '' },
            ]
        });

        // ── Chrome runtime ────────────────────────────────
        window.chrome = {
            runtime: { onMessage: { addListener: () => {}, removeListener: () => {} } },
            loadTimes: () => ({}),
            csi: () => ({}),
            app: { isInstalled: false, InstallState: { DISABLED: 'disabled' } },
        };

        // ── Hardware / device hints ────────────────────────
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
        Object.defineProperty(navigator, 'deviceMemory',        { get: () => 8 });
        Object.defineProperty(navigator, 'maxTouchPoints',      { get: () => 0 });
        Object.defineProperty(navigator, 'connection', {
            get: () => ({ effectiveType: '4g', rtt: 50, downlink: 10, saveData: false })
        });

        // ── Permissions API ────────────────────────────────
        const origQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : origQuery(parameters);

        // ── WebGL vendor / renderer ───────────────────────
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(param) {
            if (param === 37445) return 'Intel Inc.';
            if (param === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter.call(this, param);
        };

        // ── Prevent iframe-based detection ─────────────────
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
            get: function() {
                return window;
            }
        });
    """)
    page = context.new_page()
    return browser, context, page


def _is_page_alive(page: Page) -> bool:
    """Check whether the Playwright page is still usable."""
    try:
        page.evaluate("1 + 1")
        return True
    except Exception:
        return False


def _dismiss_dialogs(page: Page) -> None:
    """
    Try to dismiss common cookie / consent / age-gate dialogs that block content.
    Different marketplaces use different button labels.
    """
    dismiss_selectors = [
        "button:has-text('Accept')",
        "button:has-text('Accept All')",
        "button:has-text('Accept all')",
        "button:has-text('Accept Cookies')",
        "button:has-text('I Accept')",
        "button:has-text('Agree')",
        "button:has-text('OK')",
        "button:has-text('Got it')",
        "button:has-text('Continue')",
        "button:has-text('Close')",
        "button[id*='accept']",
        "button[id*='consent']",
        "a:has-text('Accept')",
        "#sp-cc-accept",            # Amazon cookie consent
        "#onetrust-accept-btn-handler",  # OneTrust (used by many sites)
        "button.accept-cookies",
    ]
    for sel in dismiss_selectors:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                logger.info("Dismissed dialog with selector: %s", sel)
                time.sleep(1)
                return
        except Exception:
            continue


def _check_for_bot_wall(page: Page, headless: bool) -> None:
    """
    Detect bot-detection / CAPTCHA pages and pause for manual solving.
    In --visible mode, waits up to 60s for the user to solve the challenge.
    In headless mode, logs a warning and continues.
    """
    if not _is_page_alive(page):
        return

    bot_indicators = [
        "unusual activity",
        "are you a robot",
        "captcha",
        "verify you are human",
        "access denied",
        "blocked",
        "security check",
        "please verify",
    ]
    try:
        page_text = page.evaluate("document.body.innerText").lower()
    except Exception:
        return

    detected = any(indicator in page_text for indicator in bot_indicators)
    if not detected:
        return

    logger.warning("Bot-detection wall detected on page")

    if headless:
        console.print(
            "\n[bold red]⚠ Bot detection triggered![/bold red] "
            "Run with [cyan]--visible[/cyan] to solve CAPTCHAs manually.\n"
        )
        return

    # Visible mode: give user time to solve the CAPTCHA manually
    console.print(
        "\n[bold yellow]🛡  Bot detection / CAPTCHA detected![/bold yellow]"
    )
    console.print(
        "[yellow]   Solve the challenge in the browser window."
        " The scraper will wait up to 60 seconds then continue.[/yellow]\n"
    )

    for i in range(60):
        time.sleep(1)
        try:
            current_text = page.evaluate("document.body.innerText").lower()
            still_blocked = any(ind in current_text for ind in bot_indicators)
            if not still_blocked:
                console.print("  [green]✓ Challenge solved! Continuing…[/green]")
                logger.info("Bot wall cleared after %ds", i + 1)
                _human_delay(1.0, 2.0)
                return
        except Exception:
            return

    console.print("  [red]Timed out waiting for CAPTCHA solve. Continuing anyway…[/red]")
    logger.warning("Bot wall not cleared within 60s timeout")


def _navigate_with_retry(page: Page, url: str, context: BrowserContext | None = None, headless: bool = True) -> Page:
    """
    Navigate to *url* with retry logic for transient network failures.
    If the page gets closed by the site, create a fresh page from the context.
    Returns the (possibly new) page object.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if not _is_page_alive(page) and context is not None:
                logger.warning("Page was closed — creating a fresh page (attempt %d)", attempt)
                console.print("  [yellow]Page was closed by site — opening fresh page…[/yellow]")
                page = context.new_page()

            logger.info("Navigating to %s (attempt %d/%d)", url, attempt, MAX_RETRIES)
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            _human_delay(1.5, 3.0)  # Human-like settle time
            _dismiss_dialogs(page)
            _check_for_bot_wall(page, headless)
            _simulate_human_behavior(page)
            return page
        except Exception as exc:
            logger.warning("Navigation attempt %d failed: %s", attempt, exc)
            if attempt == MAX_RETRIES:
                logger.error("All %d navigation attempts failed for %s", MAX_RETRIES, url)
                raise
            console.print(
                f"  [yellow]Navigation error (attempt {attempt}/{MAX_RETRIES}). "
                f"Retrying in {RETRY_BACKOFF}s…[/yellow]"
            )
            time.sleep(RETRY_BACKOFF)
            # Recreate page for next attempt if it died
            if not _is_page_alive(page) and context is not None:
                try:
                    page = context.new_page()
                except Exception:
                    pass
    return page  # Shouldn't reach here, but keeps type checker happy


def _wait_for_content(page: Page) -> None:
    """Wait for seller cards to appear on the page."""
    if not _is_page_alive(page):
        logger.warning("Page is not alive — skipping wait_for_content")
        return

    selectors = config.SELECTORS["seller_card"]
    for sel in selectors.split(","):
        sel = sel.strip()
        try:
            page.wait_for_selector(sel, timeout=config.ELEMENT_TIMEOUT)
            logger.debug("Content found with selector: %s", sel)
            return
        except Exception:
            continue
    # If no selector matched, just wait a fixed duration.
    logger.info("No specific selector matched — waiting %ds for page to settle", config.PAGE_LOAD_WAIT)
    time.sleep(config.PAGE_LOAD_WAIT)


# ─── Direct DOM extraction (for Shadow-DOM / web-component sites) ────

def _extract_via_dom(page: Page) -> list[dict[str, Any]]:
    """
    Use Playwright's evaluate() to directly extract data from the live DOM.
    This works for sites that use Shadow DOM / web components (like Reddit's
    <shreddit-post> elements) where innerHTML is not accessible to
    BeautifulSoup after page.content().
    """
    if not _is_page_alive(page):
        logger.warning("Page is not alive — cannot extract via DOM")
        return []

    try:
        results = page.evaluate("""
        () => {
            const results = [];
            // Try multiple strategies to find post/seller elements

            // Strategy 1: shreddit-post elements (modern Reddit)
            const shredditPosts = document.querySelectorAll('shreddit-post');
            for (const post of shredditPosts) {
                const title = post.getAttribute('post-title') || '';
                const permalink = post.getAttribute('permalink') || '';
                const author = post.getAttribute('author') || '';
                const score = post.getAttribute('score') || '';
                const commentCount = post.getAttribute('comment-count') || '';
                const subreddit = post.getAttribute('subreddit-prefixed-name') || '';
                const createdTimestamp = post.getAttribute('created-timestamp') || '';

                // Try to get flair
                let flair = '';
                const flairEl = post.querySelector('flair-pill');
                if (flairEl) {
                    flair = flairEl.textContent.trim();
                }
                // Also try shadow root for flair
                if (!flair) {
                    try {
                        const sr = post.shadowRoot;
                        if (sr) {
                            const f = sr.querySelector('flair-pill, .flair');
                            if (f) flair = f.textContent.trim();
                        }
                    } catch(e) {}
                }

                if (title) {
                    results.push({
                        seller_name: title,
                        seller_url: permalink ? (permalink.startsWith('http') ? permalink : 'https://www.reddit.com' + permalink) : '',
                        seller_id: author,
                        seller_rating: score,
                        seller_review_count: commentCount,
                        seller_location: subreddit,
                        seller_description: '',
                        seller_join_date: createdTimestamp,
                        categories: flair,
                        product_count: '',
                    });
                }
            }

            // Strategy 2: data-testid post containers (older Reddit / fallback)
            if (results.length === 0) {
                const posts = document.querySelectorAll('div[data-testid="post-container"]');
                for (const post of posts) {
                    const titleEl = post.querySelector('a[data-testid="post-title"], h3');
                    const title = titleEl ? titleEl.textContent.trim() : '';
                    const href = titleEl ? (titleEl.getAttribute('href') || '') : '';

                    if (title) {
                        results.push({
                            seller_name: title,
                            seller_url: href.startsWith('http') ? href : 'https://www.reddit.com' + href,
                            seller_id: '',
                            seller_rating: '',
                            seller_review_count: '',
                            seller_location: '',
                            seller_description: '',
                            seller_join_date: '',
                            categories: '',
                            product_count: '',
                        });
                    }
                }
            }

            // Strategy 3: generic marketplace fallback — any anchor with certain data attributes
            if (results.length === 0) {
                const cards = document.querySelectorAll('[data-seller], .seller-card, .product-card, article');
                for (const card of cards) {
                    const nameEl = card.querySelector('h2, h3, h4, .title, [data-name]');
                    const linkEl = card.querySelector('a[href]');
                    const name = nameEl ? nameEl.textContent.trim() : '';
                    const url = linkEl ? linkEl.getAttribute('href') : '';
                    if (name) {
                        results.push({
                            seller_name: name,
                            seller_url: url || '',
                            seller_id: '',
                            seller_rating: '',
                            seller_review_count: '',
                            seller_location: '',
                            seller_description: '',
                            seller_join_date: '',
                            categories: '',
                            product_count: '',
                        });
                    }
                }
            }

            return results;
        }
        """)
        logger.debug("DOM extraction returned %d items", len(results))
        return results
    except Exception as exc:
        logger.warning("DOM extraction failed: %s", exc)
        return []


def _extract_page_data(page: Page) -> list[dict[str, Any]]:
    """
    Extract seller data from the current page.
    Tries DOM extraction first, then falls back to HTML parsing.
    """
    if not _is_page_alive(page):
        logger.warning("Page is not alive — returning empty data")
        return []

    sellers = _extract_via_dom(page)
    if not sellers:
        try:
            sellers = parse_page(page.content())
        except Exception as exc:
            logger.warning("HTML parsing failed: %s", exc)
            sellers = []
    return sellers


# ─── Pagination strategies ───────────────────────────────────────────

def _paginate_infinite_scroll(page: Page, max_pages: int) -> list[list[dict[str, Any]]]:
    """
    Handle infinite-scroll pagination by scrolling to the bottom
    and collecting data after each scroll.
    """
    all_page_data: list[list[dict[str, Any]]] = []

    for i in range(max_pages):
        console.print(f"  [dim]Scroll {i + 1}/{max_pages}…[/dim]")

        if not _is_page_alive(page):
            logger.warning("Page closed during infinite scroll at scroll %d", i + 1)
            console.print("  [red]Page was closed by site — stopping scroll.[/red]")
            break

        _wait_for_content(page)
        sellers = _extract_page_data(page)

        if not sellers:
            logger.info("Scroll %d: empty page detected — stopping pagination", i + 1)
            console.print(f"  [yellow]Scroll {i + 1}: no data found (empty page).[/yellow]")

        all_page_data.append(sellers)

        try:
            prev_height = page.evaluate("document.body.scrollHeight")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            _human_delay(config.REQUEST_DELAY - 1, config.REQUEST_DELAY + 2)
            new_height = page.evaluate("document.body.scrollHeight")
        except Exception as exc:
            logger.warning("Scroll interaction failed: %s", exc)
            console.print("  [red]Lost connection to page during scroll.[/red]")
            break

        if new_height == prev_height:
            console.print("  [green]Reached end of scroll.[/green]")
            logger.info("End of infinite scroll reached at scroll %d", i + 1)
            break

    return all_page_data


def _paginate_load_more(page: Page, max_pages: int) -> list[list[dict[str, Any]]]:
    """Click a 'Load More' button and collect data after each click."""
    all_page_data: list[list[dict[str, Any]]] = []

    for i in range(max_pages):
        console.print(f"  [dim]Load more {i + 1}/{max_pages}…[/dim]")

        if not _is_page_alive(page):
            logger.warning("Page closed during load-more at step %d", i + 1)
            console.print("  [red]Page was closed by site — stopping.[/red]")
            break

        _wait_for_content(page)
        sellers = _extract_page_data(page)

        if not sellers:
            logger.info("Load-more %d: empty page detected", i + 1)
            console.print(f"  [yellow]Load-more {i + 1}: no data found (empty page).[/yellow]")

        all_page_data.append(sellers)

        btn_selector = config.SELECTORS["load_more_button"]
        clicked = False
        for sel in btn_selector.split(","):
            sel = sel.strip()
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    _human_delay(config.REQUEST_DELAY - 1, config.REQUEST_DELAY + 2)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            console.print("  [green]No more 'Load More' button found.[/green]")
            logger.info("Load-more button disappeared at page %d", i + 1)
            break

    return all_page_data


def _paginate_next_button(page: Page, max_pages: int, context: BrowserContext | None = None) -> list[list[dict[str, Any]]]:
    """Click a 'Next page' button and collect data from each page."""
    all_page_data: list[list[dict[str, Any]]] = []

    for i in range(max_pages):
        console.print(f"  [dim]Page {i + 1}/{max_pages}…[/dim]")

        if not _is_page_alive(page):
            logger.warning("Page closed during next-button pagination at page %d", i + 1)
            console.print("  [red]Page was closed by site — stopping.[/red]")
            break

        _wait_for_content(page)
        sellers = _extract_page_data(page)

        if not sellers:
            logger.info("Next-button page %d: empty page detected", i + 1)
            console.print(f"  [yellow]Page {i + 1}: no data found (empty page).[/yellow]")

        all_page_data.append(sellers)

        btn_selector = config.SELECTORS["next_page_button"]
        clicked = False
        for sel in btn_selector.split(","):
            sel = sel.strip()
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    page.wait_for_load_state("networkidle")
                    _human_delay(config.REQUEST_DELAY - 1, config.REQUEST_DELAY + 2)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            console.print("  [green]No more pages.[/green]")
            logger.info("Next-page button disappeared at page %d", i + 1)
            break

    return all_page_data


def _paginate_url_param(page: Page, base_url: str, max_pages: int, context: BrowserContext | None = None, headless: bool = True) -> list[list[dict[str, Any]]]:
    """Iterate through pages by incrementing a URL query parameter."""
    all_page_data: list[list[dict[str, Any]]] = []
    separator = "&" if "?" in base_url else "?"

    for i in range(1, max_pages + 1):
        url = f"{base_url}{separator}{config.PAGE_PARAM}={i}"
        console.print(f"  [dim]Page {i}/{max_pages} → {url}[/dim]")
        page = _navigate_with_retry(page, url, context, headless)
        _wait_for_content(page)

        sellers = _extract_page_data(page)

        if not sellers:
            logger.info("URL-param page %d: empty page detected — stopping", i)
            console.print(f"  [yellow]Page {i}: no data found (empty page). Stopping.[/yellow]")
            break

        all_page_data.append(sellers)
        _human_delay(config.REQUEST_DELAY - 1, config.REQUEST_DELAY + 2)

    return all_page_data


# ─── Preset application ──────────────────────────────────────────────

def _apply_preset_to_config(preset_name: str) -> None:
    """Override config.py values with a marketplace preset."""
    preset = apply_preset(preset_name)
    console.print(f"[bold magenta]Using preset:[/bold magenta] {preset['description']}")
    logger.info("Applying preset: %s", preset_name)

    if preset.get("base_url"):
        config.BASE_URL = preset["base_url"]
    if preset.get("pagination_type"):
        config.PAGINATION_TYPE = preset["pagination_type"]
    if preset.get("page_param"):
        config.PAGE_PARAM = preset["page_param"]
    if preset.get("selectors"):
        config.SELECTORS = preset["selectors"]


# ─── Orchestrator ─────────────────────────────────────────────────────

def scrape(
    url: str | None = None,
    max_pages: int | None = None,
    output_path: str | None = None,
    headless: bool | None = None,
    preset: str | None = None,
) -> list[dict[str, Any]]:
    """
    Run the full scraping pipeline and return the aggregated seller list.
    """
    # Apply preset FIRST (before reading defaults) so overrides take effect
    if preset:
        _apply_preset_to_config(preset)

    url = url or config.BASE_URL
    max_pages = max_pages if max_pages is not None else config.MAX_PAGES
    headless = headless if headless is not None else config.HEADLESS
    output_path = output_path or config.OUTPUT_CSV

    if not url:
        console.print("[bold red]Error:[/bold red] No URL specified. Use --url or --preset.")
        sys.exit(1)

    console.rule("[bold cyan]Marketplace Seller Data Extraction Tool[/bold cyan]")
    console.print(f"[bold]Target URL :[/bold] {url}")
    console.print(f"[bold]Max pages  :[/bold] {max_pages}")
    console.print(f"[bold]Pagination :[/bold] {config.PAGINATION_TYPE}")
    console.print(f"[bold]Headless   :[/bold] {headless}")
    console.print(f"[bold]Output     :[/bold] {output_path}")
    console.print()

    logger.info(
        "Scrape started | url=%s | max_pages=%d | pagination=%s | headless=%s | output=%s",
        url, max_pages, config.PAGINATION_TYPE, headless, output_path,
    )

    all_sellers: list[dict[str, Any]] = []

    with sync_playwright() as pw:
        browser, context, page = _launch_browser(pw, headless)

        try:
            # ── Navigate to target ────────────────────────────────
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Navigating to marketplace…", total=None)
                page = _navigate_with_retry(page, url, context, headless)
                _wait_for_content(page)
                progress.update(task, description="[green]Page loaded.[/green]")

            # ── Pagination ────────────────────────────────────────
            console.print("\n[bold]Starting pagination…[/bold]")
            pagination_type = config.PAGINATION_TYPE

            if pagination_type == "infinite_scroll":
                page_data_list = _paginate_infinite_scroll(page, max_pages)
            elif pagination_type == "load_more":
                page_data_list = _paginate_load_more(page, max_pages)
            elif pagination_type == "next_button":
                page_data_list = _paginate_next_button(page, max_pages, context)
            elif pagination_type == "url_param":
                page_data_list = _paginate_url_param(page, url, max_pages, context, headless)
            else:
                # Fallback: just scrape the single page.
                logger.warning("Unknown pagination type '%s' — scraping single page", pagination_type)
                sellers = _extract_page_data(page)
                page_data_list = [sellers]

            # ── Deduplicate across all pages ──────────────────────
            console.print(f"\n[bold]Processing {len(page_data_list)} page(s)…[/bold]")
            seen_keys: set[tuple[str, str]] = set()

            for idx, page_sellers in enumerate(page_data_list, 1):
                new_count = 0
                for s in page_sellers:
                    key = (s["seller_name"], s["seller_url"])
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_sellers.append(s)
                        new_count += 1
                console.print(
                    f"  Page {idx}: {len(page_sellers)} found, "
                    f"{new_count} new (total: {len(all_sellers)})"
                )
                logger.info(
                    "Page %d: %d found, %d new, %d total",
                    idx, len(page_sellers), new_count, len(all_sellers),
                )

        except Exception as exc:
            console.print(f"\n[bold red]Error during scraping:[/bold red] {exc}")
            logger.exception("Fatal error during scraping")
        finally:
            context.close()
            browser.close()
            logger.info("Browser closed")

    # ── Export ─────────────────────────────────────────────────────
    if all_sellers:
        csv_path = export_to_csv(all_sellers, output_path)
        console.print(f"\n[bold green]✓ Exported {len(all_sellers)} sellers → {csv_path}[/bold green]")
        logger.info("Exported %d sellers to %s", len(all_sellers), csv_path)

        # Show a preview table
        console.print()
        preview_df = preview_data(all_sellers, max_rows=8)
        table = Table(title="Preview (first 8 rows)", show_lines=True)
        for col in preview_df.columns:
            table.add_column(col, style="cyan", no_wrap=(col == "seller_url"))
        for _, row in preview_df.iterrows():
            table.add_row(*[str(v)[:80] for v in row])
        console.print(table)
    else:
        console.print("\n[bold yellow]⚠ No sellers extracted. Check your selectors in config.py.[/bold yellow]")
        logger.warning("No sellers extracted — check selectors or target URL")

    return all_sellers


# ─── CLI ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Marketplace Seller Data Extraction Tool (MVP)",
        epilog="Example: python scraper.py --preset etsy --pages 5 --visible",
    )
    parser.add_argument("--url", type=str, default=None, help="Target marketplace URL")
    parser.add_argument("--pages", type=int, default=None, help="Max pages to scrape")
    parser.add_argument("--output", type=str, default=None, help="Output CSV path")
    parser.add_argument(
        "--visible", action="store_true", default=False,
        help="Run browser in visible (non-headless) mode",
    )
    parser.add_argument(
        "--preset", type=str, default=None,
        help="Marketplace preset (etsy, amazon, ebay, reddit, custom). Use --list-presets to see all.",
    )
    parser.add_argument(
        "--list-presets", action="store_true", default=False,
        help="Show available marketplace presets and exit",
    )
    args = parser.parse_args()

    # Handle --list-presets
    if args.list_presets:
        console.print("\n[bold]Available marketplace presets:[/bold]\n")
        table = Table(show_lines=True)
        table.add_column("Preset Name", style="cyan bold")
        table.add_column("Description", style="white")
        for name, desc in list_presets():
            table.add_row(name, desc)
        console.print(table)
        console.print("\nUsage: [dim]python scraper.py --preset <name>[/dim]\n")
        sys.exit(0)

    sellers = scrape(
        url=args.url,
        max_pages=args.pages,
        output_path=args.output,
        headless=not args.visible,
        preset=args.preset,
    )

    console.print(f"\n[bold]Done. {len(sellers)} seller(s) extracted.[/bold]")
    sys.exit(0 if sellers else 1)


if __name__ == "__main__":
    main()
