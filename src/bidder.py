#!/usr/bin/env python3
"""
Upwork Bidder
- Generate proposals using Claude
- Submit bids via Playwright
- Track submissions
"""

import json
import sqlite3
import time
import random
import logging
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
from anthropic import Anthropic

CONFIG_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "config" / "upwork_config.json"
DB_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "db" / "jobs.sqlite"
LOG_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "logs" / "bidder.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

client = Anthropic()

PROPOSAL_PROMPT = """Write a proposal. Sound like a real founder.

Job: {title}
Details: {description}
Budget: {budget}
Duration: {duration}

Expertise: Rust/TypeScript backend, React/Leptos frontend, APIs, ML/LLM, databases, cloud
Rate: ${rate}/hour

Write 300-400 words. Rules:
1. Start with "Hey" or similar. Sound casual.
2. Show you read their job. Reference something specific.
3. Say what you'd do in 1-2 sentences. Be direct.
4. Mention relevant tech you've used.
5. Timeline: "We can start immediately" or similar.
6. Close: "Let's chat" or "Ready to get started"

NO corporate language. NO "leverage", "synergize", "solutions".
Sound like someone who builds things. Confident but not arrogant.
Real person. Real work. Real pitch."""

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def random_delay(min_s=5, max_s=10):
    """Longer delay between bid submissions (anti-bot)"""
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)

def get_ready_to_bid():
    """Get evaluated jobs ready for bidding"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT job_id, title, description, budget_min, budget_max, duration
        FROM jobs
        WHERE job_id IN (
            SELECT job_id FROM bids 
            WHERE status = 'evaluated' AND confidence >= 0.75
        )
        AND job_id NOT IN (
            SELECT job_id FROM bids WHERE status = 'submitted'
        )
        LIMIT 5
    ''')
    rows = c.fetchall()
    conn.close()
    return rows

def generate_proposal(job_data, rate):
    """Generate proposal with Claude"""
    prompt = PROPOSAL_PROMPT.format(
        title=job_data[1],
        description=job_data[2],
        budget=f"${job_data[3]}-{job_data[4]}",
        duration=job_data[5],
        rate=rate
    )
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return None

def submit_bid(page, job_id, proposal, rate):
    """Submit bid via Playwright"""
    try:
        logger.info(f"Submitting bid for job {job_id}...")
        
        # Click "Send Proposal" button (selector may vary)
        for selector in [
            'button:has-text("Send Proposal")',
            'button[type="submit"]',
            '[data-test="send-proposal-button"]'
        ]:
            try:
                page.click(selector)
                random_delay(1, 2)
                break
            except:
                pass
        
        # Fill proposal text
        for selector in ['textarea', '[data-test="proposal-textarea"]', 'textarea[name="proposal"]']:
            try:
                page.fill(selector, proposal)
                random_delay(1, 2)
                break
            except:
                pass
        
        # Set rate if visible
        for selector in ['input[name="rate"]', '[data-test="rate-input"]']:
            try:
                page.fill(selector, str(rate))
                random_delay(0.5, 1)
                break
            except:
                pass
        
        # Click final submit
        for selector in ['button:has-text("Submit")', 'button[type="submit"]']:
            try:
                page.click(selector)
                random_delay(2, 3)
                break
            except:
                pass
        
        logger.info(f"✅ Bid submitted for job {job_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error submitting bid: {e}")
        return False

def mark_submitted(job_id, proposal, rate):
    """Mark bid as submitted in DB"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE bids 
        SET status = 'submitted', proposal_text = ?, suggested_rate = ?, submitted_at = ?
        WHERE job_id = ?
    ''', (proposal, rate, datetime.utcnow().isoformat(), job_id))
    conn.commit()
    conn.close()

def main():
    logger.info("[UPWORK BIDDER] Starting...")
    
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return
    
    max_bids = config.get("filters", {}).get("max_bids_per_day", 5)
    jobs_to_bid = get_ready_to_bid()
    
    if not jobs_to_bid:
        logger.info("No jobs ready for bidding")
        return
    
    logger.info(f"Found {len(jobs_to_bid)} jobs ready to bid on (max {max_bids} today)")
    
    submitted_count = 0
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Login
            logger.info("Logging into Upwork...")
            page.goto("https://www.upwork.com/ab/account-security/login")
            page.wait_for_load_state("networkidle", timeout=10000)
            random_delay(2, 4)
            
            for job in jobs_to_bid[:max_bids]:
                job_id = job[0]
                title = job[1]
                description = job[2]
                budget_min = job[3]
                budget_max = job[4]
                
                logger.info(f"Processing job: {title[:50]}...")
                
                # Generate proposal
                estimated_rate = min(config["filters"]["max_rate"], 
                                   max(config["filters"]["min_rate"], (budget_min + budget_max) // 2 // 40))
                proposal = generate_proposal(job, estimated_rate)
                
                if not proposal:
                    logger.warning(f"Failed to generate proposal for {job_id}")
                    continue
                
                # Navigate to job page
                # Note: In production, would navigate to specific job URL
                page.goto(f"https://www.upwork.com/jobs/~{job_id}")
                page.wait_for_load_state("networkidle", timeout=10000)
                random_delay(2, 3)
                
                # Submit bid
                success = submit_bid(page, job_id, proposal, estimated_rate)
                
                if success:
                    mark_submitted(job_id, proposal, estimated_rate)
                    submitted_count += 1
                    
                    # Anti-bot: longer delay between submissions
                    if submitted_count < max_bids:
                        random_delay(5, 10)
        
        finally:
            browser.close()
    
    logger.info(f"✅ BIDDER COMPLETE: {submitted_count}/{len(jobs_to_bid)} bids submitted")

if __name__ == "__main__":
    main()
