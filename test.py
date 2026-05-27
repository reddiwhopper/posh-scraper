import asyncio
from playwright.async_api import async_playwright
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# CONFIGURATION
KEYWORDS = "vintage leather jacket"
FILTER_URL = f"https://poshmark.com/search?query={KEYWORDS.replace(' ', '%20')}&sort_by=added_desc"
EMAIL_SENDER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASS")
EMAIL_RECEIVER = "your-email@example.com"

async def scrape_poshmark():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # Setting a real user agent to avoid instant blocks
        await page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36"})
        
        await page.goto(FILTER_URL)
        await page.wait_for_selector('.tile') # Wait for listing tiles to load
        
        listings = []
        items = await page.query_selector_all('.tile')
        
        for item in items[:10]: # Get top 10 new listings
            title_el = await item.query_selector('.tile__title')
            price_el = await item.query_selector('.tile__price')
            link_el = await item.query_selector('a')
            img_el = await item.query_selector('img')
            
            listings.append({
                "title": await title_el.inner_text() if title_el else "N/A",
                "price": await price_el.inner_text() if price_el else "N/A",
                "link": "https://poshmark.com" + await link_el.get_attribute('href'),
                "img": await img_el.get_attribute('src')
            })
            
        await browser.close()
        return listings

def send_email(listings):
    if not listings: return
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Daily Poshmark Finds: {KEYWORDS}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    html = "<h2>New Listings Today</h2>"
    for item in listings:
        html += f"""
        <div style="margin-bottom: 20px;">
            <img src="{item['img']}" width="150"><br>
            <strong>{item['title']}</strong> - {item['price']}<br>
            <a href="{item['link']}">View on Poshmark</a>
        </div>
        """
    
    msg.attach(MIMEText(html, "html"))
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())

if __name__ == "__main__":
    results = asyncio.run(scrape_poshmark())
    send_email(results)
    print(f"Success: Found {len(results)} items.")