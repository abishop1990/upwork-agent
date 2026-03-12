#!/usr/bin/env python3
"""
Response Automation
- Auto-reply to common questions
- Rate negotiations
- Timeline questions
"""

import json
import sqlite3
import logging
from pathlib import Path
from anthropic import Anthropic

LOG_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "logs" / "responses.log"
DB_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "db" / "jobs.sqlite"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

client = Anthropic()

AUTO_REPLY_PROMPT = """You are a professional business development manager for Coding for Cats LLC.

Client Message: {message}
Job Context: {job_title}
Our Rate: ${rate}/hour

Classify the message as one of:
- rate_question: Client asking about our rate
- timeline_question: Client asking about timeline/deadline
- tech_question: Client asking about technology/approach
- experience_question: Client asking about relevant experience
- interview_request: Client wants to discuss further
- general_inquiry: General question

Then write a professional, brief reply (2-3 sentences max):
- Be friendly but professional
- Address their specific concern
- Move toward closing

Format:
TYPE: [type]
REPLY: [your reply text]
"""

def classify_and_reply(message, job_title, rate):
    """Classify message and generate auto-reply"""
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[{"role": "user", "content": AUTO_REPLY_PROMPT.format(
                message=message,
                job_title=job_title,
                rate=rate
            )}]
        )
        
        reply_text = response.content[0].text
        lines = reply_text.split("\n")
        
        msg_type = "unknown"
        reply = reply_text
        
        for line in lines:
            if line.startswith("TYPE:"):
                msg_type = line.replace("TYPE:", "").strip()
            elif line.startswith("REPLY:"):
                reply = line.replace("REPLY:", "").strip()
        
        return {
            "type": msg_type,
            "reply": reply,
            "should_auto_send": msg_type in ["rate_question", "timeline_question", "interview_request"]
        }
    except Exception as e:
        logger.error(f"Error generating reply: {e}")
        return {
            "type": "error",
            "reply": None,
            "should_auto_send": False
        }

def get_pending_responses():
    """Get client messages needing replies"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT r.response_id, r.bid_id, r.client_message, j.title, b.suggested_rate
        FROM responses r
        JOIN bids b ON r.bid_id = b.bid_id
        JOIN jobs j ON b.job_id = j.job_id
        WHERE r.action IS NULL OR r.action = ''
        LIMIT 5
    """)
    
    rows = c.fetchall()
    conn.close()
    return rows

def mark_response_handled(response_id, action):
    """Mark response as handled"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE responses SET action = ? WHERE response_id = ?
    """, (action, response_id))
    conn.commit()
    conn.close()

def process_responses():
    """Process pending client messages"""
    logger.info("[RESPONSE AUTOMATION] Processing client messages...")
    
    pending = get_pending_responses()
    
    if not pending:
        logger.info("No pending responses")
        return
    
    logger.info(f"Found {len(pending)} pending response(s)")
    
    for response_id, bid_id, message, job_title, rate in pending:
        logger.info(f"Processing message from {job_title[:40]}...")
        
        result = classify_and_reply(message, job_title, rate or 75)
        
        if result["type"] != "error":
            logger.info(f"  Type: {result['type']}")
            logger.info(f"  Reply: {result['reply'][:60]}...")
            logger.info(f"  Auto-send: {result['should_auto_send']}")
            
            # In production, would submit reply via Upwork API/Playwright
            # For now, just log and mark as processed
            action = "auto_reply_generated"
            if result["should_auto_send"]:
                action = "auto_reply_ready_to_send"
            
            mark_response_handled(response_id, action)

if __name__ == "__main__":
    process_responses()
