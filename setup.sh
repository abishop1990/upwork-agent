#!/bin/bash
set -e

echo "📦 Setting up Upwork Autonomous Agent..."

# Create directories
echo "📁 Creating directories..."
mkdir -p config db logs

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium

# Initialize database
echo "🗄️  Initializing database..."
python src/db_init.py

# Create config template if not exists
if [ ! -f "config/upwork_config.json" ]; then
    echo "📝 Creating config template..."
    cp config/upwork_config.json.example config/upwork_config.json 2>/dev/null || \
    cat > config/upwork_config.json << 'EOF'
{
  "upwork": {
    "email": "your-email@example.com",
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
    "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"
  }
}
EOF
    echo "⚠️  Please edit config/upwork_config.json with your credentials"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config/upwork_config.json with your Upwork credentials"
echo "2. Set ANTHROPIC_API_KEY environment variable"
echo "3. Run: python src/scraper.py (test)"
echo "4. Run: python src/evaluator.py (test)"
echo "5. Run: python src/bidder.py (test)"
echo "6. Run: python src/tracker.py (test)"
echo "7. Deploy cron jobs (see README.md for schedule)"
echo ""
