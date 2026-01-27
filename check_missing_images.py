"""
Check which listings are missing images
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database import DatabaseManager

def main():
    db = DatabaseManager()

    # Get all listings
    all_listings = db.get_all_listings()

    print(f"\n{'='*60}")
    print(f"Total listings in database: {len(all_listings)}")
    print(f"{'='*60}\n")

    # Check which have images
    with_images = []
    without_images = []
    without_url = []

    for listing in all_listings:
        if listing.get('local_image_path'):
            # Has local image path
            image_path = Path(listing['local_image_path'])
            if image_path.exists():
                with_images.append(listing)
            else:
                without_images.append(listing)
        else:
            # No local image path saved
            if listing.get('image_url'):
                without_images.append(listing)
            else:
                without_url.append(listing)

    print(f"✓ Listings WITH downloaded images: {len(with_images)}")
    print(f"✗ Listings WITHOUT downloaded images: {len(without_images)}")
    print(f"⚠ Listings with NO image URL at all: {len(without_url)}\n")

    if without_images:
        print(f"{'='*60}")
        print("Listings missing images (but have URLs):")
        print(f"{'='*60}\n")
        for listing in without_images[:10]:  # Show first 10
            print(f"Title: {listing['title'][:60]}")
            print(f"  ID: {listing['listing_id']}")
            print(f"  Image URL: {listing.get('image_url', 'NONE')[:80]}")
            print(f"  Local path: {listing.get('local_image_path', 'NOT SET')}")
            print()

        if len(without_images) > 10:
            print(f"... and {len(without_images) - 10} more\n")

    if without_url:
        print(f"{'='*60}")
        print("Listings with NO image URL from Poshmark:")
        print(f"{'='*60}\n")
        for listing in without_url[:5]:  # Show first 5
            print(f"Title: {listing['title'][:60]}")
            print(f"  ID: {listing['listing_id']}")
            print(f"  URL: {listing['url']}")
            print()

    db.close()

if __name__ == "__main__":
    main()
