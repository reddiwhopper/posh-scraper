# Quick Setup Guide

Follow these steps to get your Poshmark scraper running:

## 1. Install Dependencies

Open a terminal in the project directory and run:

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

## 2. Configure Gmail

1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to https://myaccount.google.com/apppasswords
4. Create an app password for "Mail"
5. Copy the 16-character password

## 3. Create .env File

Create a file named `.env` (copy from `.env.example`):

```
GMAIL_APP_PASSWORD=your-16-character-password-here
```

Replace `your-16-character-password-here` with your actual Gmail app password.

## 4. Create config.yaml

Copy the example configuration:

```bash
cp config\config.example.yaml config\config.yaml
```

Edit `config\config.yaml` and update:

- **sender_email**: Your Gmail address
- **recipient_emails**: Email addresses to receive notifications
- **searches**: Your Poshmark search queries and filters

Example search:

```yaml
searches:
  - name: "Nike Shoes Size 10"
    keyword: "Nike shoes"
    filters:
      size: ["10"]
      price_min: 20
      price_max: 150
```

## 5. Test Run

Run the scraper manually to test:

```bash
python main.py
```

Check for:
- ✅ Browser opens (or runs headless)
- ✅ Listings are scraped
- ✅ Email is sent
- ✅ No errors in output

## 6. Setup Task Scheduler (Optional)

To run automatically every day:

1. Open **Task Scheduler** (search in Windows)
2. Click **Create Basic Task**
3. Name: "Poshmark Scraper"
4. Trigger: Daily at your preferred time (e.g., 8:00 AM)
5. Action: **Start a program**
6. Program: Browse to `run_scraper.bat` in your project folder
7. Finish and test

## Troubleshooting

### "Module not found" errors
- Make sure virtual environment is activated: `venv\Scripts\activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### "Configuration file not found"
- Create `config\config.yaml` from `config\config.example.yaml`

### Email not sending
- Verify Gmail app password in `.env`
- Check that 2-Step Verification is enabled
- Look for SMTP errors in logs at `data\logs\scraper.log`

### No listings found
- Check if Poshmark search URL is valid
- Try removing filters temporarily
- Set `headless: false` in config to see browser

## Next Steps

1. Monitor `data\logs\scraper.log` for execution details
2. Check `data\listings.db` for saved listings
3. Adjust searches in `config\config.yaml` as needed
4. Schedule the task to run daily

## Need Help?

Check the full README.md for detailed documentation.
