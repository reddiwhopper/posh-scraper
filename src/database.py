"""
Database Manager
Handles SQLite operations for tracking listings
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class DatabaseManager:
    """Manages SQLite database operations for listing tracking"""

    def __init__(self, db_path="data/listings.db"):
        """
        Initialize database manager

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection = None
        self.init_db()

    def init_db(self):
        """Create database and tables if they don't exist"""
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

        cursor = self.connection.cursor()

        # Create listings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                listing_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                price REAL,
                size TEXT,
                brand TEXT,
                seller_username TEXT,
                url TEXT NOT NULL,
                image_url TEXT,
                local_image_path TEXT,
                search_name TEXT NOT NULL,
                first_seen TIMESTAMP NOT NULL,
                notified BOOLEAN DEFAULT 0,
                notified_at TIMESTAMP
            )
        """)

        # Create index on notified column for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notified
            ON listings(notified)
        """)

        # Create index on search_name for filtering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_name
            ON listings(search_name)
        """)

        self.connection.commit()

    def is_listing_new(self, listing_id: str) -> bool:
        """
        Check if a listing is new (not seen before)

        Args:
            listing_id: Unique listing identifier

        Returns:
            True if listing is new, False if already exists
        """
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT listing_id FROM listings WHERE listing_id = ?",
            (listing_id,)
        )

        result = cursor.fetchone()
        return result is None

    def save_listing(self, listing_data: Dict) -> bool:
        """
        Save a new listing to the database

        Args:
            listing_data: Dictionary containing listing information

        Returns:
            True if saved successfully, False if already exists
        """
        # Check if listing already exists
        if not self.is_listing_new(listing_data['listing_id']):
            return False

        cursor = self.connection.cursor()

        # Add timestamp
        listing_data['first_seen'] = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO listings (
                listing_id, title, price, size, brand, seller_username,
                url, image_url, local_image_path, search_name, first_seen,
                notified, notified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)
        """, (
            listing_data['listing_id'],
            listing_data.get('title', ''),
            listing_data.get('price'),
            listing_data.get('size', ''),
            listing_data.get('brand', ''),
            listing_data.get('seller_username', ''),
            listing_data['url'],
            listing_data.get('image_url', ''),
            listing_data.get('local_image_path', ''),
            listing_data['search_name'],
            listing_data['first_seen']
        ))

        self.connection.commit()
        return True

    def get_unnotified_listings(self) -> List[Dict]:
        """
        Get all listings that haven't been notified via email

        Returns:
            List of listing dictionaries
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM listings
            WHERE notified = 0
            ORDER BY first_seen DESC
        """)

        rows = cursor.fetchall()

        # Convert rows to dictionaries
        listings = []
        for row in rows:
            listing = dict(row)
            listings.append(listing)

        return listings

    def mark_as_notified(self, listing_id: str):
        """
        Mark a listing as notified

        Args:
            listing_id: Unique listing identifier
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE listings
            SET notified = 1, notified_at = ?
            WHERE listing_id = ?
        """, (datetime.now().isoformat(), listing_id))

        self.connection.commit()

    def mark_multiple_as_notified(self, listing_ids: List[str]):
        """
        Mark multiple listings as notified

        Args:
            listing_ids: List of listing identifiers
        """
        if not listing_ids:
            return

        cursor = self.connection.cursor()
        timestamp = datetime.now().isoformat()

        # Use executemany for better performance
        cursor.executemany("""
            UPDATE listings
            SET notified = 1, notified_at = ?
            WHERE listing_id = ?
        """, [(timestamp, listing_id) for listing_id in listing_ids])

        self.connection.commit()

    def get_listing(self, listing_id: str) -> Optional[Dict]:
        """
        Get a specific listing by ID

        Args:
            listing_id: Unique listing identifier

        Returns:
            Listing dictionary or None if not found
        """
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM listings WHERE listing_id = ?",
            (listing_id,)
        )

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_all_listings(self, search_name: Optional[str] = None) -> List[Dict]:
        """
        Get all listings, optionally filtered by search name

        Args:
            search_name: Optional search name to filter by

        Returns:
            List of listing dictionaries
        """
        cursor = self.connection.cursor()

        if search_name:
            cursor.execute("""
                SELECT * FROM listings
                WHERE search_name = ?
                ORDER BY first_seen DESC
            """, (search_name,))
        else:
            cursor.execute("""
                SELECT * FROM listings
                ORDER BY first_seen DESC
            """)

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_statistics(self) -> Dict:
        """
        Get database statistics

        Returns:
            Dictionary with statistics
        """
        cursor = self.connection.cursor()

        stats = {}

        # Total listings
        cursor.execute("SELECT COUNT(*) as count FROM listings")
        stats['total_listings'] = cursor.fetchone()['count']

        # Notified listings
        cursor.execute("SELECT COUNT(*) as count FROM listings WHERE notified = 1")
        stats['notified_listings'] = cursor.fetchone()['count']

        # Unnotified listings
        cursor.execute("SELECT COUNT(*) as count FROM listings WHERE notified = 0")
        stats['unnotified_listings'] = cursor.fetchone()['count']

        # Listings by search
        cursor.execute("""
            SELECT search_name, COUNT(*) as count
            FROM listings
            GROUP BY search_name
            ORDER BY count DESC
        """)
        stats['by_search'] = [dict(row) for row in cursor.fetchall()]

        return stats

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
