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

        # Build query parameters
        params = {'query': keyword}

        if filters:
            # Size filters - Poshmark uses size[] parameter
            if 'size' in filters and filters['size']:
                for size in filters['size']:
                    # Size parameter needs special handling in URL
                    params[f'size[]'] = size

            # Price filters
            if 'price_min' in filters:
                params['price_from'] = filters['price_min']

            if 'price_max' in filters:
                params['price_to'] = filters['price_max']

            # Brand filters
            if 'brand' in filters and filters['brand']:
                params['brand[]'] = filters['brand']

            # Category filters
            if 'category' in filters:
                params['category'] = filters['category']

            # Condition filters
            if 'condition' in filters and filters['condition']:
                params['condition[]'] = filters['condition']

            # Sort filter
            # Options: "just_in" (newest), "price_low_to_high", "price_high_to_low"
            if 'sort' in filters:
                sort_map = {
                    'just_in': 'added_desc',
                    'price_low_to_high': 'price_asc',
                    'price_high_to_low': 'price_desc'
                }
                sort_value = sort_map.get(filters['sort'], filters['sort'])
                params['sort_by'] = sort_value

        # Construct URL manually to handle array parameters
        url_parts = [base_url + '?query=' + quote_plus(keyword)]

        for key, value in params.items():
            if key == 'query':
                continue

            if isinstance(value, list):
                for item in value:
                    url_parts.append(f"{key}={quote_plus(str(item))}")
            else:
                url_parts.append(f"{key}={quote_plus(str(value))}")

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

            # Extract listing URL
            link_element = element.locator('a[href*="/listing/"]').first
            if link_element.count() > 0:
                href = link_element.get_attribute('href')
                if href:
                    # Extract listing ID from URL
                    # Format: /listing/Product-Name-123abc or https://poshmark.com/listing/...
                    match = re.search(r'/listing/([^?#/]+)', href)
                    if match:
                        listing['listing_id'] = match.group(1)
                        listing['url'] = f"https://poshmark.com/listing/{listing['listing_id']}"
                    else:
                        return None

            if 'listing_id' not in listing:
                return None

            # Extract image URL
            img_element = element.locator('img').first
            if img_element.count() > 0:
                img_src = img_element.get_attribute('src')
                if img_src:
                    listing['image_url'] = img_src

            # Extract title
            # Try multiple selectors
            title_selectors = [
                '[data-testid="listing-title"]',
                '.tile__title',
                'div[class*="title"]',
                'a[href*="/listing/"]'
            ]

            for selector in title_selectors:
                title_element = element.locator(selector).first
                if title_element.count() > 0:
                    title = title_element.inner_text().strip()
                    if title:
                        listing['title'] = title
                        break

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
                    # Extract numeric value from price string
                    price_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', price_text)
                    if price_match:
                        price_str = price_match.group(1).replace(',', '')
                        try:
                            listing['price'] = float(price_str)
                            price_found = True
                        except ValueError:
                            pass
                    break

            # Fallback: Parse price from full text content if not found
            if not price_found:
                try:
                    full_text = element.inner_text()
                    # Look for price pattern like "$80" or "$12.99"
                    price_match = re.search(r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)', full_text)
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

        # Create new page
        page = self.browser.new_page()

        try:
            # Set realistic viewport and user agent
            page.set_viewport_size({"width": 1920, "height": 1080})

            # Navigate to search page
            logger.info(f"Navigating to: {url}")
            page.goto(url, timeout=self.timeout, wait_until='networkidle')

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
