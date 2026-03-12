#!/usr/bin/env python3
"""
Enhanced Proposal Generation
- Customized to job category
- Include past work samples
- Tech stack matching
"""

import json
import sqlite3
import logging
from pathlib import Path
from anthropic import Anthropic

LOG_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "logs" / "proposals.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

client = Anthropic()

# Our portfolio
PORTFOLIO = {
    "api_development": {
        "title": "API Optimization & Microservices",
        "examples": [
            "OpenRouter LLM integration (real-time streaming, cost optimization)",
            "Multi-tenant API architecture (database sharding, rate limiting)",
            "RESTful + GraphQL endpoints (authentication, pagination)"
        ],
        "tech": "Rust (Axum), TypeScript, Node.js, PostgreSQL"
    },
    "backend_development": {
        "title": "Backend Systems & Services",
        "examples": [
            "UseAllMyPoints: Affiliate tracking + travel rewards engine ($40K opportunity)",
            "Adria MTG: Magic: The Gathering analysis engine (5K+ daily users)",
            "Real-time data pipelines (ETL, caching, queuing)"
        ],
        "tech": "Rust, TypeScript, Node.js, SQLite, PostgreSQL, Redis"
    },
    "frontend_development": {
        "title": "Modern Frontend Architecture",
        "examples": [
            "Adria MTG: Interactive coaching UI (React + Leptos, 60%+ satisfaction)",
            "Responsive design (mobile-first, accessibility WCAG 2.1)",
            "Real-time updates (WebSockets, polling)"
        ],
        "tech": "React, Leptos (Rust WASM), TypeScript, Tailwind CSS"
    },
    "machine_learning": {
        "title": "LLM Integration & AI Systems",
        "examples": [
            "Claude API integration (structured JSON parsing, confidence scoring)",
            "Deterministic coaching framework (5-gate decision logic, win rate correlation)",
            "Multi-turn conversations with memory (context windows, summarization)"
        ],
        "tech": "Anthropic Claude, OpenRouter, Python, LangChain"
    },
    "data_engineering": {
        "title": "Data Systems & Analytics",
        "examples": [
            "SQLite optimization (schema design, indexing, migrations)",
            "Real-time analytics (event tracking, dashboards)",
            "Data pipelines (extraction, transformation, loading)"
        ],
        "tech": "SQLite, PostgreSQL, Python, SQL"
    },
    "devops_deployment": {
        "title": "Cloud Deployment & Infrastructure",
        "examples": [
            "Railway.app deployment (CI/CD, environment variables)",
            "Vercel frontend hosting (automatic deployments, edge functions)",
            "Docker containerization (multi-stage builds, optimization)"
        ],
        "tech": "Docker, Railway, Vercel, GitHub Actions, Cloud platforms"
    }
}

CUSTOM_PROPOSAL_PROMPT = """Write a proposal that sounds like a real founder, not a consultant.

Job: {title}
Details: {description}
Budget: {budget}
Timeline: {duration}

Our work:
{portfolio}

Why we fit:
{analysis}

Write 300-400 words. Sound like a real person:
- Start casual: "Hey, I've built similar systems"
- Be specific: Name actual tech, past work, concrete examples
- Show you read their job: Mention something from their description
- Explain your approach: "Here's how we'd tackle this..."
- Be confident but not arrogant: "This is straightforward for us"
- Clear next step: "Let's jump on a quick call"

NO corporate speak. NO "I'd be happy to". NO "leverage" or "synergistic".
Sound like someone who's built real products. Direct. Confident. Real."""

def detect_category(job_data):
    """Detect job category from title + description"""
    title_lower = job_data.get("title", "").lower()
    desc_lower = job_data.get("description", "").lower()
    combined = title_lower + " " + desc_lower
    
    categories = {
        "api_development": ["api", "rest", "graphql", "endpoint", "integration", "webhook"],
        "backend_development": ["backend", "server", "database", "microservice", "service", "python", "node", "rust"],
        "frontend_development": ["frontend", "react", "vue", "ui", "ux", "interface", "web app"],
        "machine_learning": ["machine learning", "ml", "ai", "llm", "claude", "gpt", "neural"],
        "data_engineering": ["data", "analytics", "pipeline", "etl", "warehouse", "bigquery"],
        "devops_deployment": ["devops", "deployment", "docker", "kubernetes", "ci/cd", "cloud", "aws"]
    }
    
    scores = {}
    for category, keywords in categories.items():
        score = sum(1 for keyword in keywords if keyword in combined)
        scores[category] = score
    
    best = max(scores.items(), key=lambda x: x[1])
    return best[0] if best[1] > 0 else "backend_development"

def analyze_fit(job_data, category):
    """Use Claude to analyze fit"""
    portfolio_text = PORTFOLIO.get(category, PORTFOLIO["backend_development"])
    
    analysis_prompt = f"""
    Job Title: {job_data.get('title')}
    Job Description: {job_data.get('description', '')[:500]}
    
    Our Expertise in this Category:
    - {portfolio_text['title']}
    - Examples: {', '.join(portfolio_text['examples'][:2])}
    - Tech: {portfolio_text['tech']}
    
    Write 2-3 sentences explaining why we're a great fit for this specific job.
    Be concrete and reference relevant skills/experience."""
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[{"role": "user", "content": analysis_prompt}]
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Claude error in analysis: {e}")
        return "We have direct experience with similar projects and strong expertise in this area."

def generate_custom_proposal(job_data, rate):
    """Generate customized proposal"""
    logger.info(f"Generating custom proposal for: {job_data.get('title', '')[:50]}")
    
    # Detect category
    category = detect_category(job_data)
    logger.info(f"  Category: {category}")
    
    # Get portfolio
    portfolio = PORTFOLIO.get(category, PORTFOLIO["backend_development"])
    portfolio_text = f"""
    {portfolio['title']}
    
    Examples:
    {chr(10).join(f"• {ex}" for ex in portfolio['examples'])}
    
    Technology: {portfolio['tech']}
    """
    
    # Analyze fit
    analysis = analyze_fit(job_data, category)
    
    # Generate proposal
    prompt = CUSTOM_PROPOSAL_PROMPT.format(
        title=job_data.get("title", ""),
        description=job_data.get("description", "")[:500],
        client_name=job_data.get("client_name", "Client"),
        budget=f"${job_data.get('budget_min', 0)}-{job_data.get('budget_max', 0)}",
        duration=job_data.get("duration", "Not specified"),
        portfolio=portfolio_text,
        analysis=analysis
    )
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        proposal = response.content[0].text
        logger.info(f"  ✅ Proposal generated ({len(proposal)} chars)")
        return proposal
    except Exception as e:
        logger.error(f"Error generating proposal: {e}")
        return None

if __name__ == "__main__":
    # Test
    test_job = {
        "title": "Rust Backend API Development",
        "description": "Build a high-performance REST API for our SaaS platform",
        "client_name": "TechCorp Inc",
        "budget_min": 5000,
        "budget_max": 10000,
        "duration": "6-8 weeks"
    }
    
    proposal = generate_custom_proposal(test_job, 100)
    print("\n" + "="*60)
    print(proposal)
