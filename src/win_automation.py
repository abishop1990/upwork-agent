#!/usr/bin/env python3
"""
Win Automation
- When project converts to "won", create GitHub issue
- Assign to team
- Send Discord notification
"""

import json
import sqlite3
import subprocess
import logging
from datetime import datetime
from pathlib import Path

LOG_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "logs" / "wins.log"
DB_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "db" / "jobs.sqlite"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def get_new_wins():
    """Get projects that just converted to 'won'"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT b.bid_id, b.job_id, j.title, j.description, b.suggested_rate, j.duration
        FROM bids b
        JOIN jobs j ON b.job_id = j.job_id
        WHERE b.status = 'won' AND b.github_issue IS NULL
        LIMIT 10
    """)
    
    rows = c.fetchall()
    conn.close()
    return rows

def create_github_issue(job_title, job_description, rate, duration):
    """Create GitHub issue for won project"""
    
    body = f"""## Upwork Project Won

**Client Project:** {job_title}
**Rate:** ${rate}/hour
**Duration:** {duration}

### Description
{job_description[:500]}

### Tasks
- [ ] Kickoff call with client
- [ ] Set up project repository
- [ ] Establish communication cadence
- [ ] Create detailed timeline
- [ ] Begin development

### Timeline
- Start: {datetime.utcnow().strftime('%Y-%m-%d')}
- Estimated Duration: {duration}

### Notes
Project sourced via Upwork autonomous bidding system.
"""
    
    try:
        # Use gh CLI to create issue
        cmd = [
            "gh", "issue", "create",
            "--title", f"[UPWORK WIN] {job_title[:60]}",
            "--body", body,
            "--label", "upwork,won",
            "--repo", "abishop1990/upwork-agent"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            issue_url = result.stdout.strip()
            logger.info(f"✅ GitHub issue created: {issue_url}")
            return issue_url
        else:
            logger.error(f"Failed to create issue: {result.stderr}")
            return None
    
    except Exception as e:
        logger.error(f"Error creating GitHub issue: {e}")
        return None

def mark_win_processed(bid_id, github_issue):
    """Mark win as processed"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE bids SET github_issue = ? WHERE bid_id = ?
    """, (github_issue, bid_id))
    conn.commit()
    conn.close()

def send_discord_win_notification(job_title, rate, duration, github_url):
    """Send Discord notification about win"""
    # Note: Requires DISCORD_WEBHOOK_URL env var
    import os
    import requests
    
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.debug("No Discord webhook configured")
        return
    
    payload = {
        "embeds": [{
            "title": f"🎉 UPWORK WIN! {job_title[:60]}",
            "description": f"Rate: ${rate}/hour\nDuration: {duration}",
            "color": 65280,  # Green
            "fields": [
                {
                    "name": "GitHub Issue",
                    "value": f"[View]('{github_url}')",
                    "inline": True
                },
                {
                    "name": "Status",
                    "value": "Ready for kickoff",
                    "inline": True
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    
    try:
        requests.post(webhook_url, json=payload, timeout=5)
        logger.info("✅ Discord notification sent")
    except Exception as e:
        logger.warning(f"Failed to send Discord notification: {e}")

def process_wins():
    """Process newly won projects"""
    logger.info("[WIN AUTOMATION] Processing won projects...")
    
    wins = get_new_wins()
    
    if not wins:
        logger.info("No new wins")
        return
    
    logger.info(f"Found {len(wins)} new win(s)")
    
    for bid_id, job_id, title, description, rate, duration in wins:
        logger.info(f"Creating automation for: {title[:50]}...")
        
        # Create GitHub issue
        github_url = create_github_issue(title, description or "", rate or 75, duration or "TBD")
        
        if github_url:
            # Mark as processed
            mark_win_processed(bid_id, github_url)
            
            # Send Discord notification
            send_discord_win_notification(title, rate or 75, duration or "TBD", github_url)
            
            logger.info(f"✅ Win automation complete")
        else:
            logger.error(f"Failed to create GitHub issue for {title}")

if __name__ == "__main__":
    process_wins()
