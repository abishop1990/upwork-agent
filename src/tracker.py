#!/usr/bin/env python3
"""
Upwork Tracker
- Monitor bid responses
- Detect client interest / wins
- Send notifications
"""

import json
import sqlite3
import time
import logging
import requests
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

CONFIG_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "config" / "upwork_config.json"
DB_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "db" / "jobs.sqlite"
LOG_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "logs" / "tracker.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def get_submitted_bids():
    """Get bids that were submitted"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT b.bid_id, b.job_id, j.title
        FROM bids b
        JOIN jobs j ON b.job_id = j.job_id
        WHERE b.status = 'submitted'
        AND b.bid_id NOT IN (
            SELECT bid_id FROM responses WHERE bid_id IS NOT NULL
        )
    ''')
    rows = c.fetchall()
    conn.close()
    return rows

def check_responses(page, bid_id, job_id, title):
    """Check for responses to a specific bid"""
    try:
        logger.info(f"Checking responses for job {job_id}: {title[:50]}...")
        
        # Navigate to messages or bid status page
        page.goto(f"https://www.upwork.com/messages")
        page.wait_for_load_state("networkidle", timeout=10000)
        time.sleep(2)
        
        # Look for client messages (selectors may vary)
        messages = []
        for selector in ['[data-test="message"]', '.message-item', '[role="article"]']:
            try:
                elements = page.query_selector_all(selector)
                if elements:
                    for elem in elements:
                        text = elem.text_content()
                        if text and job_id in text:
                            messages.append(text)
            except:
                pass
        
        if messages:
            logger.info(f"  Found {len(messages)} message(s)")
            return messages
        else:
            logger.info(f"  No new messages")
            return None
    
    except Exception as e:
        logger.error(f"Error checking responses: {e}")
        return None

def parse_response(message_text):
    """Parse response to determine client interest"""
    message_lower = message_text.lower()
    
    if any(word in message_lower for word in ["interested", "would like", "looking for you", "perfect", "great fit"]):
        return "interested"
    elif any(word in message_lower for word in ["interview", "call", "discuss", "meeting"]):
        return "interviewing"
    elif any(word in message_lower for word in ["unfortunately", "thanks but", "already selected", "rejected"]):
        return "rejected"
    elif any(word in message_lower for word in ["rate", "budget", "negotiate", "cost"]):
        return "negotiating"
    else:
        return "unknown"

def store_response(bid_id, job_id, message, message_type):
    """Store response in DB"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO responses (response_id, bid_id, client_message, message_type, received_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        f"{bid_id}_{int(time.time())}",
        bid_id,
        message[:1000],  # Truncate to 1000 chars
        message_type,
        datetime.utcnow().isoformat()
    ))
    
    # Update bid status
    if message_type == "interested":
        c.execute('UPDATE bids SET status = ? WHERE bid_id = ?', ("interested", bid_id))
    elif message_type == "interviewing":
        c.execute('UPDATE bids SET status = ? WHERE bid_id = ?', ("interviewing", bid_id))
    elif message_type == "rejected":
        c.execute('UPDATE bids SET status = ? WHERE bid_id = ?', ("rejected", bid_id))
    
    conn.commit()
    conn.close()

def send_discord_notification(config, title, message_type, job_title):
    """Send Discord notification on interesting response"""
    webhook_url = config.get("discord", {}).get("webhook_url")
    if not webhook_url:
        logger.debug("No Discord webhook configured")
        return
    
    if message_type == "interested":
        emoji = "🎯"
        color = 65280  # Green
    elif message_type == "interviewing":
        emoji = "📞"
        color = 16776960  # Yellow
    elif message_type == "rejected":
        emoji = "❌"
        color = 16711680  # Red
    else:
        emoji = "💬"
        color = 3447003  # Blue
    
    payload = {
        "embeds": [{
            "title": f"{emoji} {message_type.upper()} — {job_title[:60]}",
            "description": f"Bid #{title}\nStatus: {message_type}",
            "color": color,
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        if response.status_code == 204:
            logger.info(f"✅ Discord notification sent")
        else:
            logger.warning(f"Discord notification failed: {response.status_code}")
    except Exception as e:
        logger.warning(f"Error sending Discord notification: {e}")

def main():
    logger.info("[UPWORK TRACKER] Starting...")
    
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return
    
    submitted_bids = get_submitted_bids()
    
    if not submitted_bids:
        logger.info("No submitted bids to track")
        return
    
    logger.info(f"Tracking {len(submitted_bids)} submitted bid(s)")
    
    responses_found = 0
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Login
            logger.info("Logging into Upwork...")
            page.goto("https://www.upwork.com/ab/account-security/login")
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(2)
            
            for bid_id, job_id, title in submitted_bids:
                # Check for responses
                messages = check_responses(page, bid_id, job_id, title)
                
                if messages:
                    for message in messages:
                        # Parse message
                        message_type = parse_response(message)
                        logger.info(f"  → Type: {message_type}")
                        
                        # Store response
                        store_response(bid_id, job_id, message, message_type)
                        responses_found += 1
                        
                        # Send Discord notification
                        if message_type in ["interested", "interviewing"]:
                            send_discord_notification(config, bid_id, message_type, title)
                
                time.sleep(2)  # Small delay between bids
        
        finally:
            browser.close()
    
    logger.info(f"✅ TRACKER COMPLETE: {responses_found} response(s) found and stored")

if __name__ == "__main__":
    main()
