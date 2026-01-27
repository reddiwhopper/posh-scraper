"""
Test URL building
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config_manager import ConfigManager
from scraper import PoshmarkScraper

# Load config
config = ConfigManager()
searches = config.get_searches()
scraper_config = config.get_scraper_config()

# Create scraper
scraper = PoshmarkScraper(scraper_config)

print("\n" + "="*80)
print("Testing URL Generation")
print("="*80 + "\n")

for search in searches:
    name = search['name']
    keyword = search['keyword']
    filters = search.get('filters', {})

    url = scraper.build_search_url(keyword, filters)

    print(f"Search: {name}")
    print(f"URL: {url}")
    print(f"\nFilters applied:")
    print(f"  Size: {filters.get('size', 'None')}")
    print(f"  Price min: {filters.get('price_min', 'None')}")
    print(f"  Price max: {filters.get('price_max', 'None')}")
    print(f"  Sort: {filters.get('sort', 'None')}")
    print("\n" + "="*80 + "\n")
