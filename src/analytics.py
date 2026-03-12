#!/usr/bin/env python3
"""
Analytics Dashboard
- Track bids, responses, wins
- Calculate conversion rates
- Revenue pipeline
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging

DB_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "db" / "jobs.sqlite"
LOG_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "logs" / "analytics.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def get_metrics():
    """Get all key metrics"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    metrics = {}
    
    # Total jobs scraped
    c.execute("SELECT COUNT(*) FROM jobs")
    metrics["total_jobs"] = c.fetchone()[0]
    
    # Total bids submitted
    c.execute("SELECT COUNT(*) FROM bids WHERE status = 'submitted'")
    metrics["total_bids_submitted"] = c.fetchone()[0]
    
    # Responses received
    c.execute("SELECT COUNT(DISTINCT bid_id) FROM responses")
    metrics["responses_received"] = c.fetchone()[0]
    
    # Wins (interested + interviewing)
    c.execute("""
        SELECT COUNT(*) FROM bids 
        WHERE status IN ('interested', 'interviewing', 'won')
    """)
    metrics["wins"] = c.fetchone()[0]
    
    # Response rate
    if metrics["total_bids_submitted"] > 0:
        metrics["response_rate"] = round(
            (metrics["responses_received"] / metrics["total_bids_submitted"]) * 100, 1
        )
    else:
        metrics["response_rate"] = 0
    
    # Win rate (of those with responses)
    if metrics["responses_received"] > 0:
        metrics["win_rate"] = round(
            (metrics["wins"] / metrics["responses_received"]) * 100, 1
        )
    else:
        metrics["win_rate"] = 0
    
    # Revenue pipeline (estimated)
    c.execute("""
        SELECT SUM(suggested_rate * 40) FROM bids 
        WHERE status IN ('submitted', 'interested', 'interviewing')
    """)
    pipeline = c.fetchone()[0] or 0
    metrics["revenue_pipeline"] = int(pipeline)
    
    # Bids last 7 days
    c.execute("""
        SELECT COUNT(*) FROM bids 
        WHERE submitted_at > datetime('now', '-7 days')
    """)
    metrics["bids_last_7_days"] = c.fetchone()[0]
    
    # Bids last 24 hours
    c.execute("""
        SELECT COUNT(*) FROM bids 
        WHERE submitted_at > datetime('now', '-1 day')
    """)
    metrics["bids_last_24h"] = c.fetchone()[0]
    
    conn.close()
    return metrics

def get_category_breakdown():
    """Get metrics by category"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # This is simplified - in real scenario, would store category in jobs table
    c.execute("""
        SELECT COUNT(*) FROM jobs
        GROUP BY substr(title, 1, 3)
        LIMIT 5
    """)
    
    conn.close()
    return "See logs for category breakdown"

def print_dashboard():
    """Print formatted dashboard"""
    metrics = get_metrics()
    
    print("\n" + "="*60)
    print("📊 UPWORK AGENT ANALYTICS DASHBOARD")
    print("="*60)
    
    print("\n📈 KEY METRICS")
    print(f"  Total Jobs Scraped:      {metrics['total_jobs']:,}")
    print(f"  Bids Submitted:          {metrics['total_bids_submitted']:,}")
    print(f"  Responses Received:      {metrics['responses_received']:,}")
    print(f"  Wins (Interested+):      {metrics['wins']:,}")
    
    print("\n💰 CONVERSION RATES")
    print(f"  Response Rate:           {metrics['response_rate']}%")
    print(f"  Win Rate:                {metrics['win_rate']}%")
    print(f"  Revenue Pipeline:        ${metrics['revenue_pipeline']:,}")
    
    print("\n⏱️  ACTIVITY (Last 7 Days)")
    print(f"  Bids Submitted:          {metrics['bids_last_7_days']:,}")
    print(f"  Bids (Last 24h):         {metrics['bids_last_24h']:,}")
    
    # Projections
    if metrics['response_rate'] > 0 and metrics['bids_last_7_days'] > 0:
        weekly_bids = metrics['bids_last_7_days']
        expected_responses = int(weekly_bids * (metrics['response_rate'] / 100))
        expected_wins = int(expected_responses * (metrics['win_rate'] / 100)) if metrics['win_rate'] > 0 else 0
        avg_project_value = 3000 if metrics['revenue_pipeline'] == 0 else int(metrics['revenue_pipeline'] / max(metrics['wins'], 1))
        
        print("\n🎯 PROJECTIONS (Next 4 Weeks)")
        print(f"  Expected Responses:      ~{expected_responses * 4}")
        print(f"  Expected Wins:           ~{expected_wins * 4}")
        print(f"  Estimated Revenue:       ~${expected_wins * 4 * avg_project_value:,}")
    
    print("\n" + "="*60 + "\n")

def export_metrics_json():
    """Export metrics as JSON"""
    metrics = get_metrics()
    metrics["timestamp"] = datetime.utcnow().isoformat()
    
    output_path = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "metrics.json"
    with open(output_path, "w") as f:
        json.dump(metrics, f, indent=2)
    
    logger.info(f"Metrics exported to {output_path}")
    return metrics

if __name__ == "__main__":
    print_dashboard()
    export_metrics_json()
