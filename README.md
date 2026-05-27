# Poshmark Web Scraper

A Python-based web scraper that monitors Poshmark searches with filters, tracks new listings, and sends email notifications with images.

## Features

- **Automated Scraping**: Uses Playwright to scrape Poshmark listings with JavaScript rendering support
- **Smart Tracking**: SQLite database tracks seen listings to avoid duplicates
- **Email Notifications**: Beautiful HTML emails with listing images and details
- **Image Management**: Downloads and compresses images, with automatic cleanup
- **Flexible Filtering**: Support for size, price, brand, and other filters
- **Multiple Searches**: Configure unlimited search queries with different filters
- **Scheduled Execution**: Run daily via Windows Task Scheduler
- **Comprehensive Logging**: Detailed logs for troubleshooting

## Project Structure

```
posh/
├── config/
│   ├── config.yaml              # Your search configurations
│   └── config.example.yaml      # Template for configuration
├── data/
│   ├── listings.db              # SQLite database
│   ├── images/                  # Downloaded listing images
│   └── logs/scraper.log         # Execution logs
├── src/
│   ├── config_manager.py        # Configuration loading and validation
│   ├── database.py              # Database operations
│   ├── scraper.py               # Playwright scraping logic
│   ├── image_manager.py         # Image downloading and management
│   └── email_sender.py          # Email composition and sending
├── templates/
│   └── email_template.html      # HTML email template
├── main.py                      # Main orchestrator script
├── requirements.txt             # Python dependencies
├── .env                         # Gmail credentials (create this)
└── README.md                    # This file
```

## Prerequisites

- Python 3.8 or higher
- Gmail account with 2FA enabled
- Windows (for Task Scheduler) or modify for Linux/Mac cron

## Installation

### 1. Clone or Download

Download this project to your desired location.

### 2. Create Virtual Environment

```bash
cd posh
python -m venv venv
```

### 3. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Install Playwright Browser

```bash
playwright install chromium
```

This downloads the Chromium browser needed for scraping.

## Configuration

### 1. Gmail App Password

To send emails, you need a Gmail App Password:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification if not already enabled
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Select "Mail" and "Windows Computer" (or "Other")
5. Generate password (16 characters)
6. Copy the generated password

### 2. Create .env File

Copy the example file and add your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your Gmail app password:

```
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

### 3. Create Configuration File

Copy the example configuration:

```bash
cp config/config.example.yaml config/config.yaml
```

Edit `config/config.yaml` with your settings:

```yaml
# Email settings
email:
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  sender_email: "your-email@gmail.com"
  recipient_emails:
    - "your-email@gmail.com"

# Search configurations
searches:
  - name: "Nike Sneakers Size 10"
    keyword: "Nike sneakers"
    filters:
      size: ["10"]
      price_min: 20
      price_max: 100

  - name: "Vintage Levi's Jeans"
    keyword: "vintage Levi's jeans"
    filters:
      size: ["32"]
      price_min: 30
      price_max: 150

# Scraper settings (optional - these are defaults)
scraper:
  headless: true
  timeout: 30000
  delay_min: 2
  delay_max: 5
  max_listings_per_search: 48

# Image settings (optional)
image:
  max_width: 500
  max_height: 500
  cleanup_days: 30
```

## Usage

### Manual Execution

Run the scraper manually to test:

```bash
python main.py
```

You should see output like:

```
============================================================
Poshmark Web Scraper Started
============================================================
Loading configuration...
Configuration loaded successfully
Configured searches: 2
Initializing database...
Database initialized
...
Found 12 new listings
Email sent successfully
============================================================
```

### Check the Results

1. **Database**: Check `data/listings.db` for saved listings
2. **Images**: Check `data/images/` for downloaded images
3. **Logs**: Check `data/logs/scraper.log` for execution details
4. **Email**: Check your inbox for the notification email

## Scheduling (Windows Task Scheduler)

### 1. Create Batch File

A `run_scraper.bat` file should already exist in the project root. If not, create it:

```batch
@echo off
cd "C:\Users\mguan\OneDrive - Restaurant Services, Inc\Desktop\Personal\posh"
call venv\Scripts\activate
python main.py
pause
```

**Important**: Update the path to match your actual installation directory.

### 2. Setup Task Scheduler

1. Open **Task Scheduler** (search in Windows Start menu)
2. Click **Create Basic Task**
3. Name: "Poshmark Scraper"
4. Description: "Daily Poshmark listing scraper"
5. Trigger: **Daily**
6. Start time: Choose your preferred time (e.g., 8:00 AM)
7. Action: **Start a program**
8. Program/script: Browse to `run_scraper.bat`
9. Click **Finish**

### 3. Advanced Settings (Optional)

Right-click the task and select **Properties**:

- **General** tab:
  - Check "Run whether user is logged on or not"
  - Check "Run with highest privileges"

- **Conditions** tab:
  - Uncheck "Start the task only if the computer is on AC power"

- **Settings** tab:
  - Check "Run task as soon as possible after a scheduled start is missed"

## Troubleshooting

### No listings found

- **Check URL**: The scraper builds URLs based on your filters. Check logs for the actual URL being visited.
- **Poshmark Changes**: Poshmark may have changed their HTML structure. Check `scraper.py` and update selectors.
- **Filters**: Try removing filters to see if listings appear.

### Email not sending

- **Check credentials**: Verify your Gmail app password is correct in `.env`
- **Check spam**: Email might be in spam folder
- **SMTP errors**: Check logs for detailed error messages
- **2FA**: Ensure 2-Step Verification is enabled on Gmail

### Images not downloading

- **Network**: Check internet connection
- **Permissions**: Ensure `data/images/` directory is writable
- **URL changes**: Image URLs might have changed format

### Browser issues

- **Reinstall**: Run `playwright install chromium` again
- **Headless mode**: Try setting `headless: false` in config to see what's happening
- **Timeout**: Increase `timeout` in config if pages load slowly

### Permission errors

Make sure you have write permissions for:
- `data/` directory (database and logs)
- `data/images/` directory (image downloads)

## Configuration Options

### Search Filters

Supported filters in `config.yaml`:

```yaml
filters:
  size: ["10", "10.5", "11"]        # Shoe/clothing sizes
  price_min: 20                      # Minimum price in dollars
  price_max: 100                     # Maximum price in dollars
  brand: ["Nike", "Adidas"]          # Brand names
  category: "Shoes"                  # Category (needs testing)
  condition: ["NWT", "Like New"]     # Condition (needs testing)
```

**Note**: Some filters may need adjustment based on how Poshmark structures their search URLs.

### Scraper Settings

```yaml
scraper:
  headless: true                    # Run browser in background
  timeout: 30000                    # Page load timeout (milliseconds)
  delay_min: 2                      # Minimum delay between requests (seconds)
  delay_max: 5                      # Maximum delay between requests (seconds)
  max_listings_per_search: 48       # Max listings to scrape per search
```

### Image Settings

```yaml
image:
  max_width: 500                    # Maximum image width (pixels)
  max_height: 500                   # Maximum image height (pixels)
  cleanup_days: 30                  # Delete images older than X days
```

## Database Schema

The SQLite database stores listings with the following schema:

```sql
CREATE TABLE listings (
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
);
```

## Development

### Running Tests

Currently no automated tests. Manual testing recommended:

1. Run with different search configurations
2. Test email sending
3. Verify duplicate detection
4. Check error handling

### Adding Features

Key areas for enhancement:

- **Additional filters**: Add support for more Poshmark filter parameters
- **Better selectors**: Improve scraper selectors for reliability
- **Multiple marketplaces**: Extend to other platforms (eBay, Mercari, etc.)
- **Web interface**: Add a simple web UI for managing searches
- **Notifications**: Add SMS or push notifications

## License

This project is for personal use. Ensure compliance with Poshmark's Terms of Service when using automated scrapers.

## Disclaimer

This tool is for personal use only. Be respectful of Poshmark's servers:
- Don't scrape too frequently
- Use reasonable delays between requests
- Don't overload their servers
- Respect robots.txt and Terms of Service

## Support

For issues or questions:

1. Check logs in `data/logs/scraper.log`
2. Review configuration in `config/config.yaml`
3. Verify Gmail credentials in `.env`
4. Check Poshmark hasn't changed their website structure

## Version History

- **v1.0.0** (2026-01-22): Initial release
  - Playwright-based scraping
  - SQLite tracking
  - Gmail notifications
  - Image management
  - Windows Task Scheduler support
