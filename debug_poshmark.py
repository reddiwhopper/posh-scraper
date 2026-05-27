"""
Debug script to inspect Poshmark's HTML structure
This will help us figure out the correct CSS selectors
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config_manager import ConfigManager


def debug_poshmark():
    """Open Poshmark and inspect the HTML structure"""

    print("=" * 60)
    print("Poshmark HTML Structure Debugger")
    print("=" * 60)

    # Load config
    config_manager = ConfigManager()
    searches = config_manager.get_searches()

    if not searches:
        print("ERROR: No searches configured!")
        return

    # Use first search
    search = searches[0]
    print(f"\nUsing search: {search['name']}")
    print(f"Keyword: {search['keyword']}")

    # Build URL
    from scraper import PoshmarkScraper
    scraper_config = config_manager.get_scraper_config()
    scraper = PoshmarkScraper(scraper_config)

    url = scraper.build_search_url(search['keyword'], search.get('filters', {}))
    print(f"\nURL: {url}\n")

    print("Starting browser (you'll see Chrome open)...")
    print("=" * 60)

    with sync_playwright() as p:
        # Launch browser (NOT headless so you can see)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})

        print(f"Navigating to: {url}")
        page.goto(url, wait_until='networkidle')

        print("\nWaiting for page to load...")
        time.sleep(5)

        # Try to find listing elements
        print("\n" + "=" * 60)
        print("STEP 1: Finding listing containers...")
        print("=" * 60)

        container_selectors = [
            '[data-testid="listing-card"]',
            '.tile',
            '.card',
            'a[href*="/listing/"]'
        ]

        listing_elements = None
        used_selector = None

        for selector in container_selectors:
            elements = page.locator(selector).all()
            if elements and len(elements) > 0:
                listing_elements = elements
                used_selector = selector
                print(f"✓ Found {len(elements)} elements with selector: {selector}")
                break
            else:
                print(f"✗ No elements with selector: {selector}")

        if not listing_elements:
            print("\nERROR: No listing elements found!")
            print("The page might not have loaded correctly.")
            input("\nPress Enter to close browser...")
            return

        # Inspect first listing
        print("\n" + "=" * 60)
        print("STEP 2: Inspecting FIRST listing element...")
        print("=" * 60)

        first_element = listing_elements[0]

        # Get outer HTML
        outer_html = first_element.evaluate("el => el.outerHTML")
        print("\nFull HTML of first listing:")
        print("-" * 60)
        print(outer_html[:2000])  # First 2000 chars
        if len(outer_html) > 2000:
            print(f"\n... (truncated, total length: {len(outer_html)} chars)")
        print("-" * 60)

        # Try to find specific elements
        print("\n" + "=" * 60)
        print("STEP 3: Looking for specific data in first listing...")
        print("=" * 60)

        # Try to find link
        print("\n[Link/URL]")
        link_selectors = [
            'a[href*="/listing/"]',
            'a',
            '[href*="/listing/"]'
        ]

        for selector in link_selectors:
            try:
                link = first_element.locator(selector).first
                if link.count() > 0:
                    href = link.get_attribute('href')
                    print(f"  ✓ Found with '{selector}': {href}")
                    break
            except:
                print(f"  ✗ Not found with '{selector}'")

        # Try to find image
        print("\n[Image]")
        img_selectors = [
            'img',
            'img[src]',
            '[data-testid="listing-image"]'
        ]

        for selector in img_selectors:
            try:
                img = first_element.locator(selector).first
                if img.count() > 0:
                    src = img.get_attribute('src')
                    alt = img.get_attribute('alt')
                    print(f"  ✓ Found with '{selector}'")
                    print(f"    src: {src[:100]}...")
                    print(f"    alt: {alt}")
                    break
            except:
                print(f"  ✗ Not found with '{selector}'")

        # Try to find title/text
        print("\n[Title/Text]")
        title_selectors = [
            '[data-testid="listing-title"]',
            '.tile__title',
            'div[class*="title"]',
            '.title',
            'h2',
            'h3'
        ]

        for selector in title_selectors:
            try:
                title = first_element.locator(selector).first
                if title.count() > 0:
                    text = title.inner_text()
                    print(f"  ✓ Found with '{selector}': {text}")
                    break
            except:
                print(f"  ✗ Not found with '{selector}'")

        # Try to find price
        print("\n[Price]")
        price_selectors = [
            '[data-testid="listing-price"]',
            '.tile__price',
            'div[class*="price"]',
            '.price',
            'span[class*="price"]'
        ]

        for selector in price_selectors:
            try:
                price = first_element.locator(selector).first
                if price.count() > 0:
                    text = price.inner_text()
                    print(f"  ✓ Found with '{selector}': {text}")
                    break
            except:
                print(f"  ✗ Not found with '{selector}'")

        # Get ALL text content
        print("\n[All Text Content]")
        all_text = first_element.inner_text()
        print(f"All text in element:\n{all_text}")

        print("\n" + "=" * 60)
        print("DEBUGGING COMPLETE")
        print("=" * 60)
        print("\nThe browser will stay open so you can inspect the page.")
        print("Right-click on a listing and select 'Inspect' to see the HTML.")
        print("\nLook for:")
        print("  - The link to the listing (should contain '/listing/')")
        print("  - The title of the item")
        print("  - The price")
        print("  - The image")
        print("\nPress Enter when you're done to close the browser...")

        input()

        browser.close()


if __name__ == "__main__":
    debug_poshmark()
