"""
Database Management Helper
Simple script to view and manage your listings database
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database import DatabaseManager


def show_menu():
    """Display menu options"""
    print("\n" + "=" * 60)
    print("Poshmark Database Manager")
    print("=" * 60)
    print("\n1. View statistics")
    print("2. Clear ALL listings (start fresh)")
    print("3. Clear listings from a specific search")
    print("4. Mark all as unnotified (resend all in next email)")
    print("5. Exit")
    print("\n" + "=" * 60)


def view_stats(db):
    """Show database statistics"""
    stats = db.get_statistics()

    print("\n" + "=" * 60)
    print("DATABASE STATISTICS")
    print("=" * 60)
    print(f"\nTotal listings: {stats['total_listings']}")
    print(f"Notified: {stats['notified_listings']}")
    print(f"Unnotified: {stats['unnotified_listings']}")

    if stats['by_search']:
        print("\nListings by search:")
        for search_stat in stats['by_search']:
            print(f"  - {search_stat['search_name']}: {search_stat['count']}")

    print("\n" + "=" * 60)


def clear_all_listings(db):
    """Delete all listings"""
    confirm = input("\n⚠️  Are you sure you want to DELETE ALL listings? (yes/no): ")

    if confirm.lower() == 'yes':
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM listings")
        db.connection.commit()

        count = cursor.rowcount
        print(f"\n✓ Deleted {count} listings. Database is now empty.")
    else:
        print("\nCancelled. No listings deleted.")


def clear_search_listings(db):
    """Delete listings from a specific search"""
    stats = db.get_statistics()

    if not stats['by_search']:
        print("\n❌ No listings in database.")
        return

    print("\nSearches in database:")
    for idx, search_stat in enumerate(stats['by_search'], 1):
        print(f"{idx}. {search_stat['search_name']} ({search_stat['count']} listings)")

    try:
        choice = input("\nEnter search number to delete (or 'cancel'): ")

        if choice.lower() == 'cancel':
            print("\nCancelled.")
            return

        idx = int(choice) - 1

        if 0 <= idx < len(stats['by_search']):
            search_name = stats['by_search'][idx]['search_name']
            confirm = input(f"\n⚠️  Delete all listings from '{search_name}'? (yes/no): ")

            if confirm.lower() == 'yes':
                cursor = db.connection.cursor()
                cursor.execute("DELETE FROM listings WHERE search_name = ?", (search_name,))
                db.connection.commit()

                count = cursor.rowcount
                print(f"\n✓ Deleted {count} listings from '{search_name}'")
            else:
                print("\nCancelled.")
        else:
            print("\n❌ Invalid choice.")

    except ValueError:
        print("\n❌ Invalid input.")


def mark_all_unnotified(db):
    """Mark all listings as unnotified so they'll be emailed again"""
    confirm = input("\n⚠️  Mark all listings as unnotified? They'll be in the next email. (yes/no): ")

    if confirm.lower() == 'yes':
        cursor = db.connection.cursor()
        cursor.execute("UPDATE listings SET notified = 0, notified_at = NULL")
        db.connection.commit()

        count = cursor.rowcount
        print(f"\n✓ Marked {count} listings as unnotified. They'll appear in the next email!")
    else:
        print("\nCancelled.")


def main():
    """Main menu loop"""
    db = DatabaseManager()

    while True:
        show_menu()
        choice = input("\nEnter your choice (1-5): ")

        if choice == '1':
            view_stats(db)

        elif choice == '2':
            clear_all_listings(db)

        elif choice == '3':
            clear_search_listings(db)

        elif choice == '4':
            mark_all_unnotified(db)

        elif choice == '5':
            print("\nExiting...")
            db.close()
            break

        else:
            print("\n❌ Invalid choice. Please enter 1-5.")

    print("\nGoodbye!")


if __name__ == "__main__":
    main()
