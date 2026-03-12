#!/usr/bin/env python3
"""
Upwork Job Evaluator
- Read jobs from DB
- Call Claude to score
- Store evaluations
"""

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from anthropic import Anthropic
from src.config_loader import get_config, validate_config
from src.prompt_injection_protection import (
    validate_job_data, build_safe_prompt, validate_claude_response
)

DB_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "db" / "jobs.sqlite"
LOG_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "logs" / "evaluator.log"

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

EVALUATION_PROMPT = """You are an AI hiring agent for Coding for Cats LLC.
Evaluate this Upwork job for a bid decision.

Job Title: {title}
Description: {description}

Our capabilities:
- Rust/TypeScript backend development
- React/Leptos frontend
- API design and optimization
- Machine Learning + LLM integration
- Database architecture
- Cloud deployment (Railway, Vercel)

Provide JSON response:
{{
  "should_bid": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "estimated_hours": number
}}

Be honest. If we're not a good fit, say so."""

def get_unevaluated_jobs():
    """Get jobs not yet evaluated"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT * FROM jobs 
        WHERE job_id NOT IN (SELECT job_id FROM bids)
        LIMIT 10
    ''')
    rows = c.fetchall()
    conn.close()
    return rows

def evaluate_job(job_data):
    """Call Claude to evaluate job (with injection protection)"""
    
    # Validate and sanitize job data first
    safe_job = validate_job_data(job_data)
    if safe_job is None:
        logger.warning("Job failed validation (possible injection)")
        return None
    
    # Build safe prompt with boundary
    user_content = EVALUATION_PROMPT.format(**safe_job)
    system_prompt = "You are a job evaluation AI for Coding for Cats LLC. Evaluate the job based on our capabilities."
    safe_prompt = build_safe_prompt(system_prompt, user_content)
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": safe_prompt}]
        )
        
        response_text = response.content[0].text
        
        # Validate response for injection attempts
        response_text = validate_claude_response(response_text)
        if not response_text:
            return None
        
        # Parse JSON from response
        try:
            json_str = response_text[response_text.find('{'):response_text.rfind('}')+1]
            return json.loads(json_str)
        except:
            logger.warning(f"Failed to parse Claude response")
            return None
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return None

def store_evaluation(job_id, evaluation):
    """Store evaluation to DB"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO bids (job_id, confidence, status, submitted_at)
        VALUES (?, ?, ?, ?)
    ''', (
        job_id,
        evaluation.get("confidence", 0),
        "evaluated",
        datetime.utcnow().isoformat()
    ))
    
    conn.commit()
    conn.close()

def main():
    logger.info("[UPWORK EVALUATOR] Starting...")
    
    try:
        config = load_config()
    except:
        config = {"bidding": {"confidence_threshold": 0.75}}
    
    threshold = config.get("bidding", {}).get("confidence_threshold", 0.75)
    
    jobs = get_unevaluated_jobs()
    logger.info(f"Found {len(jobs)} unevaluated jobs")
    
    passed = 0
    for job in jobs:
        if len(job) < 3:
            continue
        
        job_id = job[0]
        title = job[1]
        description = job[2]
        
        logger.info(f"Evaluating: {title[:50]}...")
        
        evaluation = evaluate_job({"title": title, "description": description})
        if not evaluation:
            continue
        
        confidence = evaluation.get("confidence", 0)
        should_bid = evaluation.get("should_bid", False) and confidence >= threshold
        
        logger.info(f"  → Confidence: {confidence:.2f}, Should bid: {should_bid}")
        
        if should_bid:
            store_evaluation(job_id, evaluation)
            passed += 1
    
    logger.info(f"✅ EVALUATOR COMPLETE: {passed} jobs passed quality gate")

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

if __name__ == "__main__":
    main()
