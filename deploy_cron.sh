#!/bin/bash
# Deploy Upwork Agent cron jobs

PROJECT_PATH="$HOME/.openclaw/workspace/upwork-agent"

echo "📅 Deploying cron jobs for Upwork Autonomous Agent..."
echo "Project path: $PROJECT_PATH"
echo ""

# Create temporary crontab file
CRONTAB_FILE="/tmp/upwork_agent_cron.txt"
cat > "$CRONTAB_FILE" << EOF
# Upwork Autonomous Agent - Cron Schedule
# (Lines starting with # are comments)

# Scraper - Every 2 hours (find new jobs)
0 */2 * * * cd $PROJECT_PATH && /usr/bin/python3 src/scraper.py >> logs/scraper.log 2>&1

# Evaluator - Every hour (score jobs)
0 * * * * cd $PROJECT_PATH && /usr/bin/python3 src/evaluator.py >> logs/evaluator.log 2>&1

# Bidder - 2x per day (9:30 AM, 3:30 PM) - Anti-bot rate limiting
30 9,15 * * * cd $PROJECT_PATH && /usr/bin/python3 src/bidder.py >> logs/bidder.log 2>&1

# Tracker - Every 6 hours (check responses)
0 */6 * * * cd $PROJECT_PATH && /usr/bin/python3 src/tracker.py >> logs/tracker.log 2>&1

EOF

echo "📋 Cron schedule:"
cat "$CRONTAB_FILE" | grep -v "^#"

echo ""
read -p "Install cron jobs? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Merge with existing crontab
    (crontab -l 2>/dev/null; cat "$CRONTAB_FILE") | crontab -
    echo "✅ Cron jobs installed!"
    echo ""
    echo "Current crontab:"
    crontab -l | grep "upwork-agent\|Upwork"
else
    echo "❌ Installation cancelled"
    echo ""
    echo "To install manually, run: crontab -e"
    echo "Then paste the contents of: $CRONTAB_FILE"
fi

rm -f "$CRONTAB_FILE"
