"""
Image Manager
Handles image downloading, compression, and cleanup
"""

import os
import json
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional
from PIL import Image
from io import BytesIO


logger = logging.getLogger(__name__)


class ImageManager:
    """Manages listing image downloads and storage"""

    def __init__(self, config: Dict, base_path="data/images"):
        """
        Initialize image manager

        Args:
            config: Image configuration dictionary
            base_path: Base directory for image storage
        """
        self.config = config
        self.base_path = Path(base_path)
        self.max_width = config.get('max_width', 500)
        self.max_height = config.get('max_height', 500)
        self.cleanup_days = config.get('cleanup_days', 30)

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def download_image(self, listing_id: str, image_url: str, listing_data: Dict) -> Optional[str]:
        """
        Download and compress listing image

        Args:
            listing_id: Unique listing identifier
            image_url: URL of the image to download
            listing_data: Complete listing data for metadata

        Returns:
            Local file path to saved image or None if failed
        """
        if not image_url:
            logger.warning(f"No image URL provided for listing {listing_id}")
            return None

        try:
            # Create listing directory
            listing_dir = self.base_path / listing_id
            listing_dir.mkdir(parents=True, exist_ok=True)

            # Download image
            logger.debug(f"Downloading image for listing {listing_id}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(image_url, headers=headers, timeout=30)
            response.raise_for_status()

            # Open image with Pillow
            img = Image.open(BytesIO(response.content))

            # Convert RGBA to RGB if necessary
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Make image square by cropping to center
            # This ensures consistent display in emails
            width, height = img.size
            square_size = min(width, height)

            # Calculate crop box for center square
            left = (width - square_size) // 2
            top = (height - square_size) // 2
            right = left + square_size
            bottom = top + square_size

            # Crop to square
            img = img.crop((left, top, right, bottom))

            # Resize to target size
            target_size = min(self.max_width, self.max_height)
            img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)

            # Save compressed image
            image_filename = "image.jpg"
            image_path = listing_dir / image_filename
            img.save(image_path, 'JPEG', quality=85, optimize=True)

            logger.info(f"Saved image for listing {listing_id}: {image_path}")

            # Save metadata
            self.save_metadata(listing_dir, listing_data)

            return str(image_path)

        except requests.RequestException as e:
            logger.error(f"Error downloading image for listing {listing_id}: {e}")
            return None

        except Exception as e:
            logger.error(f"Error processing image for listing {listing_id}: {e}")
            return None

    def save_metadata(self, listing_dir: Path, listing_data: Dict):
        """
        Save listing metadata as JSON

        Args:
            listing_dir: Directory to save metadata in
            listing_data: Listing data dictionary
        """
        metadata_path = listing_dir / "metadata.json"

        try:
            # Add timestamp
            metadata = listing_data.copy()
            metadata['downloaded_at'] = datetime.now().isoformat()

            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved metadata to {metadata_path}")

        except Exception as e:
            logger.error(f"Error saving metadata to {metadata_path}: {e}")

    def cleanup_old_images(self):
        """
        Delete images older than configured cleanup_days

        Returns:
            Number of directories deleted
        """
        if self.cleanup_days <= 0:
            return 0

        logger.info(f"Cleaning up images older than {self.cleanup_days} days")

        deleted_count = 0
        cutoff_date = datetime.now() - timedelta(days=self.cleanup_days)

        try:
            # Iterate through listing directories
            for listing_dir in self.base_path.iterdir():
                if not listing_dir.is_dir():
                    continue

                # Check metadata file for date
                metadata_path = listing_dir / "metadata.json"

                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)

                        # Check downloaded_at timestamp
                        if 'downloaded_at' in metadata:
                            downloaded_at = datetime.fromisoformat(metadata['downloaded_at'])

                            if downloaded_at < cutoff_date:
                                # Delete entire directory
                                self._delete_directory(listing_dir)
                                deleted_count += 1
                                logger.debug(f"Deleted old listing directory: {listing_dir.name}")

                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Error reading metadata for {listing_dir.name}: {e}")

                else:
                    # No metadata, check directory modification time
                    dir_mtime = datetime.fromtimestamp(listing_dir.stat().st_mtime)

                    if dir_mtime < cutoff_date:
                        self._delete_directory(listing_dir)
                        deleted_count += 1
                        logger.debug(f"Deleted old listing directory (no metadata): {listing_dir.name}")

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old listing directories")

            return deleted_count

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return deleted_count

    def _delete_directory(self, directory: Path):
        """
        Recursively delete a directory and its contents

        Args:
            directory: Path to directory to delete
        """
        try:
            for item in directory.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    self._delete_directory(item)

            directory.rmdir()

        except Exception as e:
            logger.error(f"Error deleting directory {directory}: {e}")

    def get_image_path(self, listing_id: str) -> Optional[Path]:
        """
        Get path to image for a listing

        Args:
            listing_id: Unique listing identifier

        Returns:
            Path to image file or None if not found
        """
        image_path = self.base_path / listing_id / "image.jpg"

        if image_path.exists():
            return image_path

        return None

    def get_metadata(self, listing_id: str) -> Optional[Dict]:
        """
        Get metadata for a listing

        Args:
            listing_id: Unique listing identifier

        Returns:
            Metadata dictionary or None if not found
        """
        metadata_path = self.base_path / listing_id / "metadata.json"

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"Error reading metadata for {listing_id}: {e}")
            return None

    def get_statistics(self) -> Dict:
        """
        Get image storage statistics

        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_listings': 0,
            'total_size_mb': 0,
            'listings_with_images': 0
        }

        try:
            for listing_dir in self.base_path.iterdir():
                if not listing_dir.is_dir():
                    continue

                stats['total_listings'] += 1

                image_path = listing_dir / "image.jpg"
                if image_path.exists():
                    stats['listings_with_images'] += 1
                    stats['total_size_mb'] += image_path.stat().st_size / (1024 * 1024)

            stats['total_size_mb'] = round(stats['total_size_mb'], 2)

        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")

        return stats
