# Upwork Autonomous Agent

A fully autonomous system for finding, evaluating, and bidding on Upwork jobs using Claude AI.

**Status:** 50% MVP Complete (Code: 60%, Bidder/Tracker: TBD, QA: Pending)  
**Timeline to Revenue:** April 1-7, 2026  
**Revenue Target:** $5-12K/month by April 15, 2026

---

## Overview

This system operates as a 4-stage pipeline:

1. **Scraper** — Find relevant jobs on Upwork
2. **Evaluator** — Use Claude to score job fit (0-1.0 confidence)
3. **Bidder** — Auto-generate proposals & submit bids
4. **Tracker** — Monitor responses & detect wins

All components run autonomously via cron jobs, 24/7.

---

## Project Status

### ✅ Completed

- [x] Database schema (SQLite: jobs, bids, responses tables)
- [x] Configuration system (credentials, filters, settings)
- [x] Scraper implementation (Playwright, anti-bot protection)
- [x] Evaluator implementation (Claude API integration)

### ⏳ In Progress

- [ ] Bidder implementation (proposal generation, form submission)
- [ ] Tracker implementation (response polling, win detection)
- [ ] Cron scheduling
- [ ] QA & integration testing

### Timeline

| Date | Milestone | Status |
|------|-----------|--------|
| Mar 11 | Setup + DB | ✅ Complete |
| Mar 12-13 | Scraper + Evaluator tests | 🔨 Testing |
| Mar 12-13 | Bidder + Tracker code | ⏳ In progress |
| Mar 14-15 | Full QA + Cron deployment | ⏳ Pending |
| Mar 15 | **MVP Shipped** | 🎯 Target |
| Mar 15-18 | Start bidding (5/day) | 📋 Queued |
| Apr 1-7 | First payments | 💰 Target |

---

## Installation

### Requirements

- Python 3.9+
- SQLite3
- Playwright (for browser automation)
- Anthropic API key

### Setup

```bash
# Clone repo
git clone https://github.com/alanbishop/upwork-agent.git
cd upwork-agent

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Set environment variables
export ANTHROPIC_API_KEY="sk-..."

# Initialize database
python src/db_init.py

# Edit config (add real Upwork credentials)
nano config/upwork_config.json
```

---

## Usage

### Manual Execution

```bash
# Scrape jobs
python src/scraper.py

# Evaluate jobs
python src/evaluator.py

# Submit bids
python src/bidder.py

# Check responses
python src/tracker.py
```

### Automated via Cron

```bash
# Edit crontab
crontab -e

# Add:
0 */2 * * * cd ~/.openclaw/workspace/upwork-agent && python src/scraper.py
0 * * * * cd ~/.openclaw/workspace/upwork-agent && python src/evaluator.py
30 9,15 * * * cd ~/.openclaw/workspace/upwork-agent && python src/bidder.py
0 */6 * * * cd ~/.openclaw/workspace/upwork-agent && python src/tracker.py
```

---

## Architecture

### Database Schema

**jobs** table
```
job_id (PK), title, description, client_name, client_rating,
client_reviews, budget_min, budget_max, duration, skills_required,
deadline, scraped_at, url
```

**bids** table
```
bid_id (PK), job_id (FK), proposal_text, suggested_rate,
confidence, submitted_at, status, response
```

**responses** table
```
response_id (PK), bid_id (FK), client_message, message_type,
received_at, action
```

### Pipeline Flow

```
Upwork Job Feed
    ↓
Scraper (every 2h)
    ↓
SQLite jobs table
    ↓
Evaluator (every 1h)
    ↓ (filters: confidence ≥ 0.75)
SQLite bids table (marked "evaluated")
    ↓
Bidder (2x/day: 9:30 AM, 3:30 PM)
    ↓
Submit proposals via Upwork form
    ↓
SQLite bids table (marked "submitted")
    ↓
Tracker (every 6h)
    ↓
Check for client responses
    ↓
SQLite responses table
    ↓
Discord notification on wins
```

---

## Configuration

### config/upwork_config.json

```json
{
  "upwork": {
    "email": "alan@codingforcats.com",
    "password": "YOUR_PASSWORD_HERE",
    "search_url": "https://www.upwork.com/nx/search/jobs"
  },
  "scraper": {
    "frequency_hours": 2,
    "scroll_depth": 3,
    "random_delay_min": 2,
    "random_delay_max": 5
  },
  "filters": {
    "categories": ["API Development", "Backend Development", "Machine Learning"],
    "min_rate": 50,
    "max_rate": 500,
    "min_client_rating": 4.0,
    "max_bids_per_day": 5
  },
  "bidding": {
    "confidence_threshold": 0.75,
    "min_estimated_hours": 10,
    "max_estimated_hours": 80
  },
  "discord": {
    "webhook_url": "https://discord.com/api/webhooks/..."
  }
}
```

---

## Key Features

### Anti-Bot Protection
- Real Playwright browser (not API abuse)
- Random 2-5 second delays between actions
- Human-like scroll patterns
- Rate limiting (5 bids/day max)
- Monitoring for Upwork blocks

### Smart Job Evaluation
- Claude Sonnet for fast, accurate scoring
- Skill match analysis (Rust/TS, React, APIs, ML/LLM, databases, cloud)
- Client quality filtering (rating ≥ 4.0)
- Rate competitiveness check ($50-500/hr)
- Strategic fit assessment

### Error Handling & Logging
- Comprehensive logging to file + stdout
- Try/catch around all network calls
- Graceful degradation (retry failed jobs)
- Duplicate prevention (INSERT OR IGNORE)

---

## Revenue Model

### Expected Timeline

- **Week 1-2 (Mar 15-22):** 15-20 bids submitted, waiting for responses
- **Week 3 (Mar 25-31):** First 2-3 client responses, closing negotiations
- **Week 4+ (Apr 1+):** First wins, payments clearing
- **Month 2 (Apr):** 4-5 wins/week, $5-12K revenue

### Win Rate Assumptions

- **Bid submitted:** 20/week (5/day × 4 days)
- **Client response rate:** 15-20%
- **Win rate:** 30-50% (after closing)
- **Monthly revenue:** (20 bids × 0.175 response × 0.4 win × $1,000-3,000 avg project) = $1.4K-10.5K

---

## Troubleshooting

### Scraper Not Finding Jobs
- Check Upwork login credentials
- Verify Chrome is installed (`playwright install chromium`)
- Check job selectors (Upwork HTML changes frequently)
- Review logs: `tail -f logs/scraper.log`

### Evaluator Not Scoring Jobs
- Verify `ANTHROPIC_API_KEY` is set
- Check Claude API quota/balance
- Verify database has jobs with `sqlite3 db/jobs.sqlite "SELECT COUNT(*) FROM jobs"`
- Review logs: `tail -f logs/evaluator.log`

### Bidder Failing to Submit
- Verify Upwork session is still valid (scraper test first)
- Check proposal form selectors (may have changed)
- Review logs: `tail -f logs/bidder.log`

### Tracker Not Detecting Responses
- Verify bids were actually submitted (check Upwork dashboard)
- Check message selectors (HTML may have changed)
- Review logs: `tail -f logs/tracker.log`

---

## Files

```
upwork-agent/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── .gitignore
├── config/
│   └── upwork_config.json             # Config (credentials, filters)
├── db/
│   └── jobs.sqlite                    # SQLite database
├── src/
│   ├── db_init.py                     # Initialize database schema
│   ├── scraper.py                     # Scrape Upwork jobs
│   ├── evaluator.py                   # Evaluate with Claude
│   ├── bidder.py                      # Generate & submit proposals (TBD)
│   └── tracker.py                     # Monitor responses (TBD)
└── logs/
    ├── scraper.log                    # Scraper execution log
    ├── evaluator.log                  # Evaluator execution log
    ├── bidder.log                     # Bidder execution log
    └── tracker.log                    # Tracker execution log
```

---

## Security Notes

- **Credentials:** Store password in environment variable or encrypted config (not in repo)
- **API Keys:** Use `ANTHROPIC_API_KEY` environment variable
- **Database:** Never commit `jobs.sqlite` to git
- **Logs:** Sanitize sensitive data before sharing logs

---

## License

Proprietary - Coding for Cats LLC

---

## Contact

Questions? Reach out to Alan Bishop (CEO, Coding for Cats LLC)

---

**Last Updated:** March 11, 2026  
**Status:** 50% MVP Complete, Code-Ready, Pending QA & Deployment
