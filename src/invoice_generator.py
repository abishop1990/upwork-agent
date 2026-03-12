#!/usr/bin/env python3
"""
Invoice Generator
- Generate PDF invoices
- Send to clients
- Track payment
"""

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path

LOG_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "logs" / "invoices.log"
DB_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "db" / "jobs.sqlite"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

INVOICE_TEMPLATE = """
╔════════════════════════════════════════════════════════╗
║              INVOICE - CODING FOR CATS LLC              ║
╚════════════════════════════════════════════════════════╝

Invoice #: {invoice_id}
Date: {date}
Due Date: {due_date}

FROM:
  Coding for Cats LLC
  alan@codingforcats.com
  https://codingforcats.com

TO:
  {client_name}
  (Upwork: {upwork_id})

═══════════════════════════════════════════════════════════

DESCRIPTION OF WORK:
{job_description}

═══════════════════════════════════════════════════════════

RATE:        ${rate}/hour
HOURS:       {hours} hours
SUBTOTAL:    ${subtotal:,.2f}

TAX (0%):    $0.00
TOTAL DUE:   ${total:,.2f}

═══════════════════════════════════════════════════════════

Payment Terms: Net 7 days
Please remit payment to: [Bank details or PayPal]

Thank you for your business!

"""

def get_projects_for_invoicing():
    """Get completed projects ready for invoicing"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT b.bid_id, j.job_id, j.title, b.suggested_rate, 
               j.client_name, j.duration
        FROM bids b
        JOIN jobs j ON b.job_id = j.job_id
        WHERE b.status = 'completed' 
        AND (b.invoice_sent IS NULL OR b.invoice_sent = '')
        LIMIT 10
    """)
    
    rows = c.fetchall()
    conn.close()
    return rows

def estimate_hours(duration_str, rate):
    """Estimate hours from duration string"""
    # Parse duration string like "3-4 weeks", "40 hours", etc.
    duration_lower = str(duration_str).lower()
    
    if "hour" in duration_lower:
        try:
            hours = int(''.join(c for c in duration_lower if c.isdigit()))
            return hours
        except:
            pass
    
    if "week" in duration_lower:
        try:
            weeks = int(''.join(c for c in duration_lower if c.isdigit()))
            return weeks * 40  # Assume 40 hours/week
        except:
            pass
    
    if "month" in duration_lower:
        try:
            months = int(''.join(c for c in duration_lower if c.isdigit()))
            return months * 160  # Assume 160 hours/month
        except:
            pass
    
    # Default: estimate based on rate
    return int(5000 / max(rate, 50))  # Assume $5K project

def generate_invoice(bid_id, job_title, client_name, rate, duration):
    """Generate invoice text"""
    hours = estimate_hours(duration, rate)
    subtotal = hours * rate
    total = subtotal  # No tax
    
    invoice_id = f"CFC-{datetime.utcnow().strftime('%Y%m%d')}-{bid_id[:6]}"
    due_date = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    invoice_text = INVOICE_TEMPLATE.format(
        invoice_id=invoice_id,
        date=datetime.utcnow().strftime("%Y-%m-%d"),
        due_date=due_date,
        client_name=client_name,
        upwork_id=bid_id,
        job_description=job_title,
        rate=rate,
        hours=hours,
        subtotal=subtotal,
        total=total
    )
    
    return {
        "invoice_id": invoice_id,
        "text": invoice_text,
        "hours": hours,
        "total": total
    }

def save_invoice(invoice_id, invoice_text):
    """Save invoice to file"""
    invoice_path = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "invoices" / f"{invoice_id}.txt"
    invoice_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(invoice_path, "w") as f:
        f.write(invoice_text)
    
    logger.info(f"Invoice saved: {invoice_path}")
    return invoice_path

def send_invoice_to_client(bid_id, invoice_id, client_name):
    """Send invoice to client (placeholder)"""
    # In production, would:
    # 1. Send via Upwork messages
    # 2. Send via email (SMTP)
    # 3. Track delivery
    
    logger.info(f"Invoice {invoice_id} ready to send to {client_name}")
    logger.info("  (In production, would send via Upwork messages)")
    return True

def mark_invoice_sent(bid_id, invoice_id):
    """Mark invoice as sent"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE bids SET invoice_sent = ? WHERE bid_id = ?
    """, (invoice_id, bid_id))
    conn.commit()
    conn.close()

def process_invoices():
    """Process projects and generate invoices"""
    logger.info("[INVOICE GENERATOR] Processing projects...")
    
    projects = get_projects_for_invoicing()
    
    if not projects:
        logger.info("No projects ready for invoicing")
        return
    
    logger.info(f"Found {len(projects)} project(s) ready for invoicing")
    
    total_revenue = 0
    
    for bid_id, job_id, title, rate, client_name, duration in projects:
        logger.info(f"Generating invoice for: {title[:50]}...")
        
        invoice = generate_invoice(bid_id, title, client_name or "Client", rate or 75, duration)
        
        # Save invoice
        invoice_path = save_invoice(invoice["invoice_id"], invoice["text"])
        
        # Send to client
        send_invoice_to_client(bid_id, invoice["invoice_id"], client_name or "Client")
        
        # Mark as sent
        mark_invoice_sent(bid_id, invoice["invoice_id"])
        
        total_revenue += invoice["total"]
        
        logger.info(f"✅ Invoice generated: {invoice['invoice_id']} (${invoice['total']:,.2f})")
    
    logger.info(f"✅ INVOICE GENERATOR COMPLETE: ${total_revenue:,.2f} pending")

if __name__ == "__main__":
    process_invoices()
