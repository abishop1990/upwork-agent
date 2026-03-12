#!/usr/bin/env python3
"""
Upwork Job Scraper
- Login to Upwork
- Scroll job feed
- Extract job details
- Store to SQLite
"""

import json
import sqlite3
import time
import random
import logging
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

CONFIG_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "config" / "upwork_config.json"
DB_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "db" / "jobs.sqlite"
LOG_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "logs" / "scraper.log"

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

def random_delay(min_s=2, max_s=5):
    """Random human-like delay"""
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)

def login(page, email, password):
    """Log into Upwork"""
    logger.info("Logging into Upwork...")
    page.goto("https://www.upwork.com/ab/account-security/login")
    random_delay(2, 3)
    
    # Fill email
    page.fill('input[type="email"]', email)
    random_delay(1, 2)
    page.press('input[type="email"]', "Enter")
    random_delay(3, 5)
    
    # Fill password if needed
    try:
        page.fill('input[type="password"]', password)
        random_delay(1, 2)
        page.press('input[type="password"]', "Enter")
    except:
        pass  # May already be logged in
    
    page.wait_for_load_state("networkidle", timeout=10000)
    random_delay(3, 5)
    logger.info("✅ Logged in")

def extract_job_details(page, job_card):
    """Extract details from a job card"""
    try:
        # Try multiple selectors for title
        title = None
        for selector in ['h2 a', 'a[title]', '[data-test="job-title"]']:
            try:
                elem = job_card.query_selector(selector)
                if elem:
                    title = elem.text_content().strip()
                    if title:
                        break
            except:
                pass
        
        if not title:
            return None
        
        return {
            "title": title,
            "description": job_card.text_content()[:500],
            "scraped_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.debug(f"Error extracting job: {e}")
        return None

def scrape_jobs(page, config):
    """Scrape jobs from Upwork feed"""
    logger.info("Starting job scrape...")
    
    page.goto(config["upwork"]["search_url"])
    page.wait_for_load_state("networkidle", timeout=10000)
    random_delay(2, 4)
    
    jobs = []
    scroll_depth = config["scraper"]["scroll_depth"]
    
    for scroll_num in range(scroll_depth):
        logger.info(f"Scroll {scroll_num + 1}/{scroll_depth}...")
        
        # Scroll down
        page.evaluate("window.scrollBy(0, 500)")
        random_delay(2, 4)
        
        # Extract job cards (try multiple selectors)
        job_cards = None
        for selector in ['article[data-test="job-item"]', '[data-test="job-card"]', 'article']:
            try:
                cards = page.query_selector_all(selector)
                if cards and len(cards) > 0:
                    job_cards = cards
                    break
            except:
                pass
        
        if not job_cards:
            logger.info(f"  No jobs found with current selectors, retrying...")
            continue
        
        # Extract from each card
        for card in job_cards:
            job = extract_job_details(page, card)
            if job:
                jobs.append(job)
        
        logger.info(f"  Found {len(jobs)} jobs so far")
    
    return jobs

def store_jobs(jobs):
    """Store jobs to SQLite"""
    if not jobs:
        logger.info("No jobs to store")
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    for i, job in enumerate(jobs):
        if not job or not job.get("title"):
            continue
        
        try:
            job_id = f"upwork_{i}_{int(time.time())}"
            c.execute('''
                INSERT OR IGNORE INTO jobs 
                (job_id, title, description, scraped_at)
                VALUES (?, ?, ?, ?)
            ''', (
                job_id,
                job.get("title"),
                job.get("description"),
                job.get("scraped_at")
            ))
        except Exception as e:
            logger.warning(f"Error storing job: {e}")
    
    conn.commit()
    conn.close()
    logger.info(f"✅ Stored {len(jobs)} jobs to DB")

def main():
    try:
        config = load_config()
        
        logger.info("[UPWORK SCRAPER] Starting...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Login
                login(page, config["upwork"]["email"], config["upwork"]["password"])
                
                # Scrape
                jobs = scrape_jobs(page, config)
                
                # Store
                store_jobs(jobs)
                
                logger.info(f"✅ SCRAPER COMPLETE: {len(jobs)} jobs found")
                
            finally:
                browser.close()
    
    except Exception as e:
        logger.error(f"❌ SCRAPER FAILED: {e}")
        raise

if __name__ == "__main__":
    main()
