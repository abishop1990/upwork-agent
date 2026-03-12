import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "db" / "jobs.sqlite"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        title TEXT,
        description TEXT,
        client_name TEXT,
        client_rating REAL,
        client_reviews INT,
        budget_min INT,
        budget_max INT,
        duration TEXT,
        skills_required TEXT,
        deadline TEXT,
        scraped_at TEXT,
        url TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS bids (
        bid_id TEXT PRIMARY KEY,
        job_id TEXT,
        proposal_text TEXT,
        suggested_rate INT,
        confidence REAL,
        submitted_at TEXT,
        status TEXT,
        response TEXT,
        FOREIGN KEY (job_id) REFERENCES jobs(job_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS responses (
        response_id TEXT PRIMARY KEY,
        bid_id TEXT,
        client_message TEXT,
        message_type TEXT,
        received_at TEXT,
        action TEXT,
        FOREIGN KEY (bid_id) REFERENCES bids(bid_id)
    )''')
    
    conn.commit()
    conn.close()
    print("[UPWORK DAY 1] Database initialized ✅")

if __name__ == "__main__":
    init_db()
