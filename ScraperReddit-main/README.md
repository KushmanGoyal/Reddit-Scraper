# Marketplace Seller Data Extraction Tool — MVP

A Python-based CLI tool that extracts structured seller data from online marketplaces using browser automation. It handles dynamic content, pagination, and exports clean CSV output.

---

## Features

- **Marketplace presets** — Built-in configs for Etsy, Amazon, eBay, Reddit, and any custom URL
- **Browser automation** — Uses Playwright to render JavaScript-heavy pages
- **Multiple pagination strategies** — Infinite scroll, "Load More" buttons, Next page buttons, and URL parameters
- **Configurable selectors** — Easily adapt to any marketplace by editing `config.py` or creating a preset
- **Clean CSV export** — UTF-8 encoded, deduplicated, structured output via Pandas
- **Graceful error handling** — Network retries, page recovery, consent dialog dismissal, and empty page detection
- **Rich CLI output** — Progress spinners, preview tables, and colour-coded status messages
- **Structured logging** — All operations logged to `output/scraper.log` for debugging

---

## Project Structure

```
ScraperReddit/
├── config.py                # Core configuration — timing, output, logging
├── presets.py               # Marketplace presets (Etsy, Amazon, eBay, etc.)
├── scraper.py               # Main entry point — browser orchestration & pagination
├── parser.py                # HTML parsing — BeautifulSoup-based data extraction
├── exporter.py              # Data export — CSV generation with Pandas
├── requirements.txt         # Python dependencies
├── output/                  # Generated output files
│   ├── sellers.csv          # Extracted data (generated on run)
│   ├── sellers_sample.csv   # Sample output demonstrating CSV format
│   └── scraper.log          # Execution log
├── PRD.md                   # Product Requirements Document
└── README.md                # This file
```

---

## Installation

### Prerequisites

- **Python 3.9+** installed
- **pip** package manager

### Steps

```bash
# 1. Clone or download this repository
cd ScraperReddit

# 2. (Recommended) Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers (one-time setup)
python -m playwright install chromium
```

---

## Quick Start

### Use a built-in preset (easiest)

```bash
# Scrape Etsy sellers
python scraper.py --preset etsy --visible

# Scrape eBay listings for "electronics"
python scraper.py --preset ebay --pages 3 --visible

# Scrape Amazon seller offers
python scraper.py --preset amazon --pages 5

# See all available presets
python scraper.py --list-presets
```

### Use any custom URL

```bash
# Custom marketplace — tool uses generic selectors as a starting point
python scraper.py --preset custom --url "https://example.com/sellers" --visible

# Or override the URL on any preset
python scraper.py --preset etsy --url "https://www.etsy.com/search?q=jewelry" --pages 5
```

### Run with defaults (from config.py)

```bash
python scraper.py
```

---

## Available Presets

| Preset | Marketplace | Pagination | Description |
|---|---|---|---|
| `etsy` | Etsy | URL parameter | Search results showing shops & sellers |
| `amazon` | Amazon | URL parameter | Third-party seller offers on products |
| `ebay` | eBay | URL parameter | Search results with seller info |
| `reddit` | Reddit | Infinite scroll | Subreddit posts (demo mode) |
| `custom` | Any | URL parameter | Generic selectors — provide your own `--url` |

To add a new marketplace, edit `presets.py` and add a new entry to the `PRESETS` dictionary.

---

## CLI Options

```bash
python scraper.py [OPTIONS]
```

| Flag | Description |
|---|---|
| `--preset NAME` | Marketplace preset (`etsy`, `amazon`, `ebay`, `reddit`, `custom`) |
| `--url URL` | Override the target marketplace URL |
| `--pages N` | Maximum number of pages to scrape (default: 10) |
| `--output PATH` | Custom output CSV path (default: `output/sellers.csv`) |
| `--visible` | Show the browser window (non-headless, useful for debugging) |
| `--list-presets` | Show available presets and exit |
| `--help` | Show help and exit |

---

## Configuration

All core settings live in **`config.py`**:

| Parameter | Description | Default |
|---|---|---|
| `MAX_PAGES` | Safety limit on pages to traverse | `10` |
| `PAGE_LOAD_WAIT` | Seconds to wait for content | `5` |
| `REQUEST_DELAY` | Seconds between page navigations | `3` |
| `ELEMENT_TIMEOUT` | Timeout (ms) for dynamic elements | `20000` |
| `HEADLESS` | Run browser in background | `True` |
| `OUTPUT_CSV` | Output CSV file path | `output/sellers.csv` |
| `LOG_FILE` | Log file path | `output/scraper.log` |

Marketplace-specific settings (URL, selectors, pagination type) are in **`presets.py`**.

---

## Output Format

The tool generates a CSV file with the following columns:

| Column | Required? | Description |
|---|---|---|
| `seller_name` | ✅ Yes | Seller display name |
| `seller_url` | ✅ Yes | Link to seller profile |
| `seller_id` | Optional | Unique seller identifier |
| `seller_rating` | Optional | Average rating |
| `seller_review_count` | Optional | Number of reviews |
| `seller_location` | Optional | Seller location |
| `seller_description` | Optional | Bio / about text |
| `seller_join_date` | Optional | Date of marketplace registration |
| `categories` | Optional | Semicolon-separated list of categories |
| `product_count` | Optional | Total products listed |

Missing values are represented as empty strings.

---

## Example Output

A sample CSV is included at `output/sellers_sample.csv`. Here's a preview:

```csv
seller_name,seller_url,seller_id,seller_rating,seller_review_count,seller_location,seller_description,seller_join_date,categories,product_count
"How I grew my SaaS to $10k MRR","https://www.reddit.com/r/Entrepreneur/comments/abc123/...","u/founder_jane","42","15","r/Entrepreneur","","2025-11-02T14:30:00Z","SaaS; Growth",""
"Best tools for e-commerce in 2025","https://www.reddit.com/r/Entrepreneur/comments/def456/...","u/ecom_guru","128","47","r/Entrepreneur","","2025-10-28T09:15:00Z","E-Commerce",""
```

---

## Logging

All operations are logged to `output/scraper.log` with timestamps and severity levels. The log includes:

- Navigation attempts and retries
- Selector matches and content detection
- Per-page extraction summaries (items found, duplicates, skipped)
- Export details (row count, file path)
- Errors with full stack traces

Warnings and errors are also printed to the terminal alongside the Rich console output.

---

## How It Works (For Custom Marketplaces)

1. **Edit `presets.py`** — Add a new entry to the `PRESETS` dict with:
   - `base_url`: The listing/search page URL
   - `selectors`: CSS selectors for each data field (inspect the site's HTML to find these)
   - `pagination_type`: How the site paginates (`url_param`, `infinite_scroll`, `load_more`, `next_button`)

2. **Test with `--visible`** — Run with `--visible` to watch the browser and verify selectors work

3. **Check logs** — If no data is extracted, check `output/scraper.log` for detailed debugging info

---

## Troubleshooting

| Issue | Solution |
|---|---|
| No sellers extracted | Check that CSS selectors match the target page (use `--visible` to see) |
| Timeout errors | Increase `ELEMENT_TIMEOUT` or `PAGE_LOAD_WAIT` in `config.py` |
| Browser crashes | Try running with `--visible` flag to debug visually |
| Page closed by site | Tool auto-retries with a fresh page; some sites block automation |
| Cookie/consent dialogs | Tool auto-dismisses common dialogs; add selectors in `_dismiss_dialogs()` if needed |
| Encoding issues | Output uses UTF-8-sig; open CSV in Excel via "Data → From Text" if needed |
| Network errors | Tool retries up to 3 times automatically; check `output/scraper.log` for details |

---

## Legal

This tool only extracts **publicly accessible data**. It does not bypass authentication, login systems, or any access controls.

---

## License

MIT
#   S c r a p e r R e d d i t  
 