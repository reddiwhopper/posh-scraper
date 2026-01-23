"""
Poshmark Web Scraper - Main Orchestrator
Coordinates scraping, database operations, and email notifications
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config_manager import ConfigManager
from database import DatabaseManager
from scraper import PoshmarkScraper
from image_manager import ImageManager
from email_sender import EmailSender


def setup_logging(log_config: dict):
    """
    Setup logging configuration

    Args:
        log_config: Logging configuration dictionary
    """
    log_file = Path(log_config.get('log_file', 'data/logs/scraper.log'))
    log_level = log_config.get('level', 'INFO')

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main execution function"""
    start_time = datetime.now()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Poshmark Web Scraper Started")
    logger.info("=" * 60)

    try:
        # Load configuration
        logger.info("Loading configuration...")
        config_manager = ConfigManager()

        # Setup logging with config
        setup_logging(config_manager.get_logging_config())

        email_config = config_manager.get_email_config()
        searches = config_manager.get_searches()
        scraper_config = config_manager.get_scraper_config()
        image_config = config_manager.get_image_config()
        gmail_password = config_manager.get_gmail_password()

        logger.info(f"Configuration loaded successfully")
        logger.info(f"Configured searches: {len(searches)}")

        # Initialize database
        logger.info("Initializing database...")
        db = DatabaseManager()
        logger.info("Database initialized")

        # Initialize image manager
        logger.info("Initializing image manager...")
        image_manager = ImageManager(image_config)
        logger.info("Image manager initialized")

        # Cleanup old images
        logger.info("Cleaning up old images...")
        deleted_count = image_manager.cleanup_old_images()
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old image directories")

        # Initialize scraper and start browser
        logger.info("Initializing scraper...")
        scraper = PoshmarkScraper(scraper_config)
        scraper.start_browser()
        logger.info("Browser started")

        # Scrape all searches
        logger.info("Starting scraping process...")
        all_listings = []
        new_listings = []

        for search_config in searches:
            search_name = search_config['name']
            logger.info(f"Processing search: {search_name}")

            # Scrape listings
            listings = scraper.scrape_search(search_config)
            all_listings.extend(listings)

            logger.info(f"Found {len(listings)} listings for search: {search_name}")

            # Process each listing
            for listing in listings:
                listing_id = listing['listing_id']

                # Check if listing is new
                if db.is_listing_new(listing_id):
                    logger.info(f"New listing found: {listing.get('title', 'N/A')} (ID: {listing_id})")

                    # Download image
                    if listing.get('image_url'):
                        local_image_path = image_manager.download_image(
                            listing_id,
                            listing['image_url'],
                            listing
                        )

                        if local_image_path:
                            listing['local_image_path'] = local_image_path

                    # Save to database
                    db.save_listing(listing)
                    new_listings.append(listing)

                else:
                    logger.debug(f"Listing already exists: {listing_id}")

        # Close browser
        scraper.stop_browser()
        logger.info("Browser closed")

        # Summary
        logger.info("=" * 60)
        logger.info("Scraping Summary:")
        logger.info(f"  Total listings scraped: {len(all_listings)}")
        logger.info(f"  New listings found: {len(new_listings)}")
        logger.info("=" * 60)

        # Send email if there are new listings
        if new_listings:
            logger.info("Preparing to send email notification...")

            # Get unnotified listings from database
            unnotified_listings = db.get_unnotified_listings()
            logger.info(f"Total unnotified listings: {len(unnotified_listings)}")

            # Initialize email sender
            email_sender = EmailSender(email_config, gmail_password)

            # Send email
            if email_sender.send_listings_email(unnotified_listings):
                logger.info("Email sent successfully")

                # Mark listings as notified
                listing_ids = [listing['listing_id'] for listing in unnotified_listings]
                db.mark_multiple_as_notified(listing_ids)
                logger.info(f"Marked {len(listing_ids)} listings as notified")

            else:
                logger.error("Failed to send email")

        else:
            logger.info("No new listings found - no email sent")

        # Database statistics
        db_stats = db.get_statistics()
        logger.info("=" * 60)
        logger.info("Database Statistics:")
        logger.info(f"  Total listings: {db_stats['total_listings']}")
        logger.info(f"  Notified: {db_stats['notified_listings']}")
        logger.info(f"  Unnotified: {db_stats['unnotified_listings']}")

        if db_stats['by_search']:
            logger.info("  Listings by search:")
            for search_stat in db_stats['by_search']:
                logger.info(f"    - {search_stat['search_name']}: {search_stat['count']}")

        logger.info("=" * 60)

        # Image statistics
        img_stats = image_manager.get_statistics()
        logger.info("Image Storage Statistics:")
        logger.info(f"  Total listings with images: {img_stats['listings_with_images']}")
        logger.info(f"  Total storage size: {img_stats['total_size_mb']} MB")
        logger.info("=" * 60)

        # Close database
        db.close()

        # Execution time
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Execution completed in {duration:.2f} seconds")
        logger.info("=" * 60)

        return 0

    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    except ValueError as e:
        logger.error(f"Configuration validation error: {e}")
        return 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
