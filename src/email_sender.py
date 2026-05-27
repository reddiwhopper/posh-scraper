"""
Email Sender
Composes and sends HTML email notifications with listing images
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from jinja2 import Environment, FileSystemLoader


logger = logging.getLogger(__name__)


class EmailSender:
    """Handles email composition and sending"""

    def __init__(self, email_config: Dict, gmail_password: str):
        """
        Initialize email sender

        Args:
            email_config: Email configuration dictionary
            gmail_password: Gmail app password
        """
        self.smtp_server = email_config['smtp_server']
        self.smtp_port = email_config['smtp_port']
        self.sender_email = email_config['sender_email']
        self.recipient_emails = email_config['recipient_emails']
        self.gmail_password = gmail_password

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent.parent / 'templates'
        self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))

    def group_listings_by_search(self, listings: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group listings by search name

        Args:
            listings: List of listing dictionaries

        Returns:
            Dictionary mapping search names to lists of listings
        """
        grouped = {}

        for listing in listings:
            search_name = listing.get('search_name', 'Unknown')

            if search_name not in grouped:
                grouped[search_name] = []

            grouped[search_name].append(listing)

        return grouped

    def compose_email(self, listings: List[Dict]) -> MIMEMultipart:
        """
        Compose HTML email with listings

        Args:
            listings: List of listing dictionaries

        Returns:
            MIMEMultipart email message
        """
        # Create message
        message = MIMEMultipart('related')
        message['Subject'] = f'New Poshmark Listings - {datetime.now().strftime("%B %d, %Y")}'
        message['From'] = self.sender_email
        message['To'] = ', '.join(self.recipient_emails)

        # Group listings by search
        listings_by_search = self.group_listings_by_search(listings)

        # Prepare template data
        template_data = {
            'timestamp': datetime.now().strftime("%B %d, %Y at %I:%M %p"),
            'total_listings': len(listings),
            'total_searches': len(listings_by_search),
            'listings_by_search': listings_by_search
        }

        # Render HTML template
        template = self.jinja_env.get_template('email_template.html')
        html_content = template.render(**template_data)

        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        message.attach(html_part)

        return message

    def send_email(self, message: MIMEMultipart) -> bool:
        """
        Send email via Gmail SMTP

        Args:
            message: MIMEMultipart email message

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            logger.info(f"Connecting to SMTP server: {self.smtp_server}:{self.smtp_port}")

            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.set_debuglevel(0)
                server.starttls()

                # Login
                logger.info(f"Logging in as: {self.sender_email}")
                server.login(self.sender_email, self.gmail_password)

                # Send email
                logger.info(f"Sending email to: {', '.join(self.recipient_emails)}")
                server.send_message(message)

            logger.info("Email sent successfully")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            logger.error("Please verify your Gmail app password is correct.")
            logger.error("Generate a new one at: https://myaccount.google.com/apppasswords")
            return False

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def send_listings_email(self, listings: List[Dict]) -> bool:
        """
        Compose and send email with new listings

        Args:
            listings: List of listing dictionaries

        Returns:
            True if sent successfully, False otherwise
        """
        if not listings:
            logger.info("No listings to send")
            return False

        logger.info(f"Composing email with {len(listings)} listings")

        # Compose email
        message = self.compose_email(listings)

        # Send email
        return self.send_email(message)

    def send_test_email(self) -> bool:
        """
        Send a test email to verify configuration

        Returns:
            True if sent successfully, False otherwise
        """
        logger.info("Sending test email")

        # Create simple test message
        message = MIMEMultipart()
        message['Subject'] = 'Poshmark Scraper - Test Email'
        message['From'] = self.sender_email
        message['To'] = ', '.join(self.recipient_emails)

        html_content = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                .container { max-width: 600px; margin: 0 auto; background: #f5f5f5; padding: 30px; border-radius: 8px; }
                h1 { color: #667eea; }
                .success { background: #d4edda; padding: 15px; border-radius: 5px; color: #155724; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Test Email Successful!</h1>
                <div class="success">
                    <strong>Your Poshmark Web Scraper is configured correctly.</strong>
                    <p>You will receive notifications at this email address when new listings are found.</p>
                </div>
                <p><small>Sent at: {}</small></p>
            </div>
        </body>
        </html>
        """.format(datetime.now().strftime("%B %d, %Y at %I:%M %p"))

        html_part = MIMEText(html_content, 'html')
        message.attach(html_part)

        return self.send_email(message)
