"""
Web Scraper
Handles Poshmark listing extraction using Playwright
"""

import re
import json
import time
import random
import logging
from typing import List, Dict, Optional
from urllib.parse import urlencode, quote_plus
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeout


logger = logging.getLogger(__name__)

# Rotate through real Chrome UAs so each run looks different
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# JS injected before every page load to mask automation signals
_STEALTH_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
    window.chrome = {runtime: {}};
    const origQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (params) =>
        params.name === 'notifications'
            ? Promise.resolve({state: Notification.permission})
            : origQuery(params);
"""


class PoshmarkScraper:
    """Scrapes Poshmark listings using Playwright"""

    def __init__(self, config: Dict):
        """
        Initialize scraper with configuration

        Args:
            config: Scraper configuration dictionary
        """
        self.config = config
        self.headless = config.get('headless', True)
        self.timeout = config.get('timeout', 30000)
        self.delay_min = config.get('delay_min', 2)
        self.delay_max = config.get('delay_max', 5)
        self.max_listings = config.get('max_listings_per_search', 48)

        self.playwright = None
        self.browser = None

    def start_browser(self):
        """Launch Playwright browser"""
        logger.info("Starting browser...")
        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )

        logger.info("Browser started successfully")

    def stop_browser(self):
        """Close browser and Playwright"""
        if self.browser:
            self.browser.close()
            logger.info("Browser closed")

        if self.playwright:
            self.playwright.stop()

    def build_search_url(self, keyword: str, filters: Optional[Dict] = None) -> str:
        """
        Build Poshmark search URL with filters

        Args:
            keyword: Search keyword
            filters: Optional filters (size, price_min, price_max, etc.)

        Returns:
            Complete search URL
        """
        base_url = "https://poshmark.com/search"

        # Start with base URL and query
        url_parts = [base_url + '?query=' + quote_plus(keyword)]

        filters = filters or {}

        # Size filters - Poshmark uses size[] parameter (can have multiple)
        if filters.get('size'):
            for size in filters['size']:
                url_parts.append(f"size[]={quote_plus(str(size))}")

        # Price filters
        if filters.get('price_min') is not None:
            url_parts.append(f"price_from={filters['price_min']}")

        if filters.get('price_max') is not None:
            url_parts.append(f"price_to={filters['price_max']}")

        # Brand filters (can have multiple)
        if filters.get('brand'):
            if isinstance(filters['brand'], list):
                for brand in filters['brand']:
                    url_parts.append(f"brand[]={quote_plus(str(brand))}")
            else:
                url_parts.append(f"brand[]={quote_plus(str(filters['brand']))}")

        # Category filters
        if filters.get('category'):
            url_parts.append(f"category={quote_plus(str(filters['category']))}")

        # Condition filters (can have multiple)
        if filters.get('condition'):
            if isinstance(filters['condition'], list):
                for condition in filters['condition']:
                    url_parts.append(f"condition[]={quote_plus(str(condition))}")
            else:
                url_parts.append(f"condition[]={quote_plus(str(filters['condition']))}")

        # Always sort newest-first so the DB dedup stays accurate
        sort_map = {
            'just_in': 'added_desc',
            'price_low_to_high': 'price_asc',
            'price_high_to_low': 'price_desc'
        }
        sort_key = filters.get('sort', 'just_in')
        sort_value = sort_map.get(sort_key, sort_key)
        url_parts.append(f"sort_by={sort_value}")

        url = '&'.join(url_parts)
        logger.debug(f"Built search URL: {url}")

        return url

    def random_delay(self):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(self.delay_min, self.delay_max)
        logger.debug(f"Waiting {delay:.2f} seconds...")
        time.sleep(delay)

    def extract_listing_from_element(self, element) -> Optional[Dict]:
        """
        Extract listing data from a DOM element

        Args:
            element: Playwright element locator

        Returns:
            Dictionary with listing data or None
        """
        try:
            listing = {}

            # Extract listing URL.
            # The element may be a card container (has <a> children) or the
            # <a> tag itself (when the fallback selector matched links directly).
            href = None
            link_element = element.locator('a[href*="/listing/"]').first
            if link_element.count() > 0:
                href = link_element.get_attribute('href')
            else:
                # Element itself is the <a> tag
                href = element.get_attribute('href')

            if href:
                match = re.search(r'/listing/([^?#/]+)', href)
                if match:
                    listing['listing_id'] = match.group(1)
                    listing['url'] = f"https://poshmark.com/listing/{listing['listing_id']}"

            if 'listing_id' not in listing:
                return None

            # Extract image URL
            # Poshmark lazy-loads images, so the real URL may be in
            # data-src or srcset rather than src
            img_element = element.locator('img').first
            if img_element.count() > 0:
                img_src = (
                    img_element.get_attribute('src')
                    or img_element.get_attribute('data-src')
                )
                # Fall back to srcset (take the first URL if present)
                if not img_src or img_src.startswith('data:'):
                    srcset = img_element.get_attribute('srcset')
                    if srcset:
                        img_src = srcset.split(',')[0].strip().split(' ')[0]
                if img_src and not img_src.startswith('data:'):
                    listing['image_url'] = img_src

            # Extract title — try DOM selectors first, then fallbacks
            title_selectors = [
                '[data-testid="listing-title"]',
                '.tile__title',
                'div[class*="title"]',
                'p[class*="title"]',
                'span[class*="title"]',
                'h2', 'h3',
            ]

            for selector in title_selectors:
                title_element = element.locator(selector).first
                if title_element.count() > 0:
                    title = title_element.inner_text().strip()
                    if title:
                        listing['title'] = title
                        break

            # Fallback 1: image alt text often contains the listing title
            if not listing.get('title') and img_element and img_element.count() > 0:
                alt = img_element.get_attribute('alt') or ''
                if alt.strip():
                    listing['title'] = alt.strip()

            # Fallback 2: derive a readable title from the URL slug
            # e.g. "Zara-Silk-Top-abc123" → "Zara Silk Top"
            if not listing.get('title'):
                slug = listing['listing_id']
                # Strip the trailing hash (last hyphen-separated token is the ID)
                parts = slug.rsplit('-', 1)
                readable = parts[0].replace('-', ' ') if len(parts) > 1 else slug.replace('-', ' ')
                listing['title'] = readable

            # Extract price
            price_selectors = [
                '[data-testid="listing-price"]',
                '.tile__price',
                'div[class*="price"]',
                'span[class*="price"]',
                '.price'
            ]

            price_found = False
            for selector in price_selectors:
                price_element = element.locator(selector).first
                if price_element.count() > 0:
                    price_text = price_element.inner_text().strip()
                    price_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', price_text)
                    if price_match:
                        price_str = price_match.group(1).replace(',', '')
                        try:
                            listing['price'] = float(price_str)
                            price_found = True
                            break  # only stop when we actually got a price
                        except ValueError:
                            pass

            # Fallback: scan all text in the element for a price
            if not price_found:
                try:
                    full_text = element.inner_text()
                    # Try with dollar sign first, then bare number as last resort
                    price_match = (
                        re.search(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', full_text)
                        or re.search(r'(?<!\d)(\d{1,4}\.\d{2})(?!\d)', full_text)
                    )
                    if price_match:
                        price_str = price_match.group(1).replace(',', '')
                        listing['price'] = float(price_str)
                except Exception:
                    pass

            # Extract size (if visible in tile)
            size_selectors = [
                '[data-testid="listing-size"]',
                '.tile__size',
                'div[class*="size"]'
            ]

            size_found = False
            for selector in size_selectors:
                size_element = element.locator(selector).first
                if size_element.count() > 0:
                    size_text = size_element.inner_text().strip()
                    if size_text:
                        listing['size'] = size_text
                        size_found = True
                        break

            # Fallback: Parse size from text
            if not size_found:
                try:
                    full_text = element.inner_text()
                    # Look for "Size: 10" or "Size 10" pattern
                    size_match = re.search(r'Size:?\s*([^\n]+)', full_text, re.IGNORECASE)
                    if size_match:
                        listing['size'] = size_match.group(1).strip()
                except Exception:
                    pass

            # Extract brand (if visible)
            brand_selectors = [
                '[data-testid="listing-brand"]',
                '.tile__brand',
                'div[class*="brand"]'
            ]

            for selector in brand_selectors:
                brand_element = element.locator(selector).first
                if brand_element.count() > 0:
                    brand_text = brand_element.inner_text().strip()
                    if brand_text:
                        listing['brand'] = brand_text
                        break

            # Extract seller username (if visible)
            seller_selectors = [
                '[data-testid="seller-username"]',
                '.tile__seller',
                'div[class*="seller"]'
            ]

            for selector in seller_selectors:
                seller_element = element.locator(selector).first
                if seller_element.count() > 0:
                    seller_text = seller_element.inner_text().strip()
                    if seller_text:
                        listing['seller_username'] = seller_text
                        break

            return listing if listing.get('title') else None

        except Exception as e:
            logger.debug(f"Error extracting listing from element: {e}")
            return None

    def scrape_search(self, search_config: Dict) -> List[Dict]:
        """
        Scrape listings for a single search configuration

        Args:
            search_config: Search configuration with keyword and filters

        Returns:
            List of listing dictionaries
        """
        search_name = search_config['name']
        keyword = search_config['keyword']
        filters = search_config.get('filters', {})

        logger.info(f"Scraping search: {search_name}")

        # Build search URL
        url = self.build_search_url(keyword, filters)

        # Create new page with a random user agent
        user_agent = random.choice(_USER_AGENTS)
        page = self.browser.new_page(user_agent=user_agent)

        try:
            # Inject stealth patches before any page script runs
            page.add_init_script(_STEALTH_SCRIPT)

            # Set realistic viewport
            page.set_viewport_size({"width": 1920, "height": 1080})

            # Set headers that match a real browser
            page.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
            })

            # Navigate to search page — domcontentloaded is more reliable than
            # networkidle on SPAs; we wait for content explicitly after
            logger.info(f"Navigating to: {url}")
            page.goto(url, timeout=self.timeout, wait_until='domcontentloaded')
            # Give JS time to render initial listings
            time.sleep(3)

            # Wait for listings to load
            # Try multiple selectors as Poshmark structure may vary
            listing_selectors = [
                '[data-testid="listing-card"]',
                '.tile',
                '.card',
                'div[class*="listing"]',
                'a[href*="/listing/"]'
            ]

            listing_loaded = False
            for selector in listing_selectors:
                try:
                    page.wait_for_selector(selector, timeout=10000)
                    listing_loaded = True
                    logger.info(f"Listings loaded with selector: {selector}")
                    break
                except PlaywrightTimeout:
                    continue

            if not listing_loaded:
                logger.warning(f"No listings found for search: {search_name}")
                return []

            # Scroll to load more listings (optional)
            # Poshmark uses infinite scroll
            for _ in range(3):
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                time.sleep(1)

            # Extract listings
            listings = []

            # Find all listing containers
            # Try to find the most specific selector first
            container_selectors = [
                '[data-testid="listing-card"]',
                '.card',  # Current Poshmark structure (2026)
                '.tile',
                '.search-content .card',
                'a[href*="/listing/"]'
            ]

            listing_elements = None
            for selector in container_selectors:
                elements = page.locator(selector).all()
                if elements and len(elements) > 0:
                    listing_elements = elements
                    logger.info(f"Found {len(elements)} listing elements with selector: {selector}")
                    break

            if not listing_elements:
                logger.warning(f"No listing elements found for: {search_name}")
                return []

            # Extract data from each listing element
            for idx, element in enumerate(listing_elements):
                if idx >= self.max_listings:
                    logger.info(f"Reached max listings limit ({self.max_listings})")
                    break

                listing = self.extract_listing_from_element(element)

                if listing:
                    listing['search_name'] = search_name
                    listings.append(listing)
                    logger.debug(f"Extracted listing: {listing.get('title', 'N/A')}")

            logger.info(f"Extracted {len(listings)} listings for search: {search_name}")

            # Filter out listings that exceed price_max (Poshmark doesn't always enforce it)
            price_max = filters.get('price_max')
            if price_max is not None:
                before_count = len(listings)
                listings = [l for l in listings if l.get('price') is None or l['price'] <= price_max]
                filtered_count = before_count - len(listings)
                if filtered_count > 0:
                    logger.info(f"Filtered out {filtered_count} listings over ${price_max}")

            # Random delay before next search
            self.random_delay()

            return listings

        except PlaywrightTimeout as e:
            logger.error(f"Timeout loading page for search '{search_name}': {e}")
            return []

        except Exception as e:
            logger.error(f"Error scraping search '{search_name}': {e}")
            return []

        finally:
            page.close()

    def scrape_all_searches(self, searches: List[Dict]) -> List[Dict]:
        """
        Scrape listings for all search configurations

        Args:
            searches: List of search configurations

        Returns:
            List of all listings from all searches
        """
        if not self.browser:
            self.start_browser()

        all_listings = []

        for search_config in searches:
            listings = self.scrape_search(search_config)
            all_listings.extend(listings)

        logger.info(f"Total listings scraped: {len(all_listings)}")

        return all_listings

    def __enter__(self):
        """Context manager entry"""
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_browser()
