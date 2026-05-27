"""
Configuration Manager
Loads and validates YAML configuration and environment variables
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv


class ConfigManager:
    """Manages application configuration from YAML and .env files"""

    def __init__(self, config_path="config/config.yaml"):
        """
        Initialize configuration manager

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config = None
        self.gmail_password = None

        # Load environment variables
        load_dotenv()

        # Load and validate configuration
        self.load_config()
        self.validate_config()
        self.load_gmail_credentials()

    def load_config(self):
        """Load YAML configuration file"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                f"Please copy config/config.example.yaml to config/config.yaml and edit it."
            )

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    def validate_config(self):
        """Validate required configuration fields"""
        if not self.config:
            raise ValueError("Configuration is empty")

        # Validate email settings
        if 'email' not in self.config:
            raise ValueError("Missing 'email' section in configuration")

        email_config = self.config['email']
        required_email_fields = ['smtp_server', 'smtp_port', 'sender_email', 'recipient_emails']

        for field in required_email_fields:
            if field not in email_config:
                raise ValueError(f"Missing required email field: {field}")

        if not isinstance(email_config['recipient_emails'], list):
            raise ValueError("'recipient_emails' must be a list")

        if not email_config['recipient_emails']:
            raise ValueError("'recipient_emails' cannot be empty")

        # Validate searches
        if 'searches' not in self.config:
            raise ValueError("Missing 'searches' section in configuration")

        if not isinstance(self.config['searches'], list):
            raise ValueError("'searches' must be a list")

        if not self.config['searches']:
            raise ValueError("'searches' cannot be empty - add at least one search")

        # Validate each search
        for idx, search in enumerate(self.config['searches']):
            if 'name' not in search:
                raise ValueError(f"Search #{idx + 1} missing 'name' field")

            if 'keyword' not in search:
                raise ValueError(f"Search '{search.get('name', idx)}' missing 'keyword' field")

        # Set defaults for optional settings
        if 'scraper' not in self.config:
            self.config['scraper'] = {}

        scraper_defaults = {
            'headless': False,
            'timeout': 30000,
            'delay_min': 2,
            'delay_max': 5,
            'max_listings_per_search': 48
        }

        for key, default_value in scraper_defaults.items():
            if key not in self.config['scraper']:
                self.config['scraper'][key] = default_value

        if 'image' not in self.config:
            self.config['image'] = {}

        image_defaults = {
            'max_width': 500,
            'max_height': 500,
            'cleanup_days': 30
        }

        for key, default_value in image_defaults.items():
            if key not in self.config['image']:
                self.config['image'][key] = default_value

        if 'logging' not in self.config:
            self.config['logging'] = {}

        logging_defaults = {
            'level': 'INFO',
            'log_file': 'data/logs/scraper.log'
        }

        for key, default_value in logging_defaults.items():
            if key not in self.config['logging']:
                self.config['logging'][key] = default_value

    def load_gmail_credentials(self):
        """Load Gmail app password from environment variables"""
        self.gmail_password = os.getenv('GMAIL_APP_PASSWORD')

        if not self.gmail_password:
            raise ValueError(
                "Gmail app password not found.\n"
                "Please set GMAIL_APP_PASSWORD in your .env file.\n"
                "Generate an app password at: https://myaccount.google.com/apppasswords"
            )

        # Remove any hyphens or spaces from password
        self.gmail_password = self.gmail_password.replace('-', '').replace(' ', '')

    def get_email_config(self):
        """Get email configuration"""
        return self.config['email']

    def get_searches(self):
        """Get list of search configurations"""
        return self.config['searches']

    def get_scraper_config(self):
        """Get scraper configuration"""
        return self.config['scraper']

    def get_image_config(self):
        """Get image configuration"""
        return self.config['image']

    def get_logging_config(self):
        """Get logging configuration"""
        return self.config['logging']

    def get_gmail_password(self):
        """Get Gmail app password"""
        return self.gmail_password


def load_config(config_path="config/config.yaml"):
    """
    Convenience function to load configuration

    Args:
        config_path: Path to YAML configuration file

    Returns:
        ConfigManager instance
    """
    return ConfigManager(config_path)
