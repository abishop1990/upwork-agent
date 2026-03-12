#!/usr/bin/env python3
"""
Secure Configuration Loader
- Loads credentials from environment variables
- Non-sensitive config from JSON file
- Never stores passwords in code/git
"""

import json
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "config"
CONFIG_FILE = CONFIG_DIR / "upwork_config.json"

def load_env_file():
    """Load .env file if exists"""
    env_file = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
        logger.debug("Loaded .env file")

def get_config():
    """Get full configuration (secure)"""
    
    # Load .env if present
    load_env_file()
    
    # Load config.json (non-sensitive only)
    config = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    
    # Override with environment variables (takes precedence)
    upwork_config = {
        "email": os.getenv("UPWORK_EMAIL") or config.get("upwork", {}).get("email"),
        "password": os.getenv("UPWORK_PASSWORD") or config.get("upwork", {}).get("password"),
        "search_url": config.get("upwork", {}).get("search_url", "https://www.upwork.com/nx/search/jobs")
    }
    
    discord_config = {
        "webhook_url": os.getenv("DISCORD_WEBHOOK_URL") or config.get("discord", {}).get("webhook_url")
    }
    
    filters = config.get("filters", {
        "categories": ["API Development", "Backend Development", "Machine Learning"],
        "min_rate": 50,
        "max_rate": 500,
        "min_client_rating": 4.0,
        "max_bids_per_day": 5
    })
    
    bidding = config.get("bidding", {
        "confidence_threshold": 0.75,
        "min_estimated_hours": 10,
        "max_estimated_hours": 80
    })
    
    return {
        "upwork": upwork_config,
        "discord": discord_config,
        "filters": filters,
        "bidding": bidding
    }

def validate_config(config):
    """Validate that all required credentials are present"""
    
    required = [
        ("UPWORK_EMAIL", config["upwork"]["email"]),
        ("UPWORK_PASSWORD", config["upwork"]["password"]),
        ("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY")),
        ("DISCORD_WEBHOOK_URL", config["discord"]["webhook_url"])
    ]
    
    missing = [name for name, value in required if not value]
    
    if missing:
        raise ValueError(f"Missing required credentials: {', '.join(missing)}")
    
    logger.info("✅ All credentials loaded securely")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    config = get_config()
    validate_config(config)
    print(f"✅ Config loaded. Upwork email: {config['upwork']['email'][:20]}...")
