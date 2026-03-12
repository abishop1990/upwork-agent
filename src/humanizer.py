#!/usr/bin/env python3
"""
Humanizer: Remove AI artifacts from text
- Converts stiff corporate language to natural speech
- Removes em-dashes, excessive punctuation
- Shortens sentences
- Adds contractions
- Makes it sound like a real person
Not deception - just good editing
"""

import re
import logging
from pathlib import Path

LOG_PATH = Path.home() / ".openclaw" / "workspace" / "upwork-agent" / "logs" / "humanizer.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class Humanizer:
    """Remove AI artifacts and make text sound natural"""
    
    def __init__(self):
        self.corporate_phrases = {
            r"I'd be delighted to": "I can",
            r"leverage\s+(?:our\s+)?expertise": "use our experience",
            r"synergistic\s+approaches?": "approach",
            r"best-in-class": "solid",
            r"cutting-edge\s+technologies?": "modern tech",
            r"optimized\s+solutions?": "solutions",
            r"enhance\s+(?:your\s+)?capabilities?": "improve",
            r"drive\s+transformational?\s+(?:outcomes|value)": "deliver results",
            r"maximize\s+(?:your\s+)?ROI": "improve your returns",
            r"utilize": "use",
            r"facilitate": "enable",
            r"demonstrate\s+proficiency": "show we can do it",
            r"Our approach is to": "We",
            r"(?:Regarding|With respect to)": "For",
            r"ensure\s+(?:optimal|maximum)": "make sure",
            r"At the end of the day": "Ultimately",
        }
        
        self.em_dash_patterns = {
            r"—": " - ",  # Em-dash to regular dash
            r"–": " - ",  # En-dash to regular dash
        }
        
        self.contractions = {
            r"\byou are\b": "you're",
            r"\bit is\b": "it's",
            r"\bI am\b": "I'm",
            r"\bwe are\b": "we're",
            r"\bthey are\b": "they're",
            r"\bwill not\b": "won't",
            r"\bcannot\b": "can't",
            r"\bwould not\b": "wouldn't",
            r"\bcould not\b": "couldn't",
            r"\bhave not\b": "haven't",
            r"\bhas not\b": "hasn't",
            r"\bis not\b": "isn't",
            r"\bare not\b": "aren't",
        }
    
    def humanize(self, text):
        """Apply all humanization rules"""
        
        if not text:
            return ""
        
        # 1. Replace corporate phrases
        for old, new in self.corporate_phrases.items():
            text = re.sub(old, new, text, flags=re.IGNORECASE)
        
        # 2. Replace em-dashes
        for old, new in self.em_dash_patterns.items():
            text = re.sub(old, new, text)
        
        # 3. Add contractions
        for pattern, contraction in self.contractions.items():
            text = re.sub(pattern, contraction, text, flags=re.IGNORECASE)
        
        # 4. Break up long sentences (> 25 words)
        sentences = text.split(". ")
        humanized_sentences = []
        for sentence in sentences:
            words = sentence.split()
            if len(words) > 25:
                # Split at logical points
                mid = len(words) // 2
                humanized_sentences.append(" ".join(words[:mid]) + ".")
                humanized_sentences.append(" ".join(words[mid:]))
            else:
                humanized_sentences.append(sentence)
        text = " ".join(humanized_sentences)
        
        # 5. Remove excessive exclamation marks (max 1 per paragraph)
        text = re.sub(r"!{2,}", "!", text)
        
        # 6. Remove multiple punctuation
        text = re.sub(r"\.{2,}", ".", text)
        text = re.sub(r",{2,}", ",", text)
        
        # 7. Remove "we are excited to" type fluff
        text = re.sub(r"(?:We are excited|We are thrilled|I'm excited) to (?:announce|share|present)", "", text, flags=re.IGNORECASE)
        
        # 8. Replace passive voice where possible
        passive_patterns = {
            r"is\s+(?:being\s+)?(?:made|created|built|developed)": "was made",
            r"has\s+been\s+(?:made|created|built|developed)": "was built",
        }
        for pattern, replacement in passive_patterns.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # 9. Remove double spaces
        text = re.sub(r"\s{2,}", " ", text)
        
        # 10. Clean up extra punctuation around contractions
        text = re.sub(r"'\s+([a-z])", r"'\1", text)
        
        return text.strip()
    
    def score_ai_artifacts(self, text):
        """Score how "AI-like" the text is (higher = more AI-like)"""
        
        if not text:
            return 0
        
        score = 0
        text_lower = text.lower()
        
        # Count AI-like patterns
        ai_patterns = [
            (r"I'd be delighted", 5),
            (r"leverage", 3),
            (r"synergistic", 5),
            (r"best-in-class", 4),
            (r"cutting-edge", 3),
            (r"optimized", 3),
            (r"maximize.*ROI", 4),
            (r"drive.*transformational", 5),
            (r"facilitate", 2),
            (r"demonstrate.*proficiency", 4),
            (r"at the end of the day", 2),
            (r"ensure.*optimal", 3),
            (r"—|–", 1),  # Em-dashes
            (r"(?<!\.)\. {2,}", 1),  # Double spaces after period
        ]
        
        for pattern, weight in ai_patterns:
            matches = len(re.findall(pattern, text_lower))
            score += matches * weight
        
        # Sentence length (longer = more corporate)
        sentences = text.split(". ")
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        if avg_sentence_length > 25:
            score += 5
        
        return score

# Usage examples
if __name__ == "__main__":
    humanizer = Humanizer()
    
    # Test cases
    test_texts = [
        "I'd be delighted to leverage our best-in-class expertise in cutting-edge technologies to drive transformational outcomes for your organization.",
        "We are excited to announce that we can facilitate optimal solutions to maximize your ROI.",
        "Hey, I've built similar systems. Here's my approach. Let's chat.",
    ]
    
    print("Humanizer Test\n" + "="*60 + "\n")
    
    for original in test_texts:
        humanized = humanizer.humanize(original)
        score_before = humanizer.score_ai_artifacts(original)
        score_after = humanizer.score_ai_artifacts(humanized)
        
        print(f"Original ({score_before} AI points):")
        print(f"  {original}\n")
        print(f"Humanized ({score_after} AI points):")
        print(f"  {humanized}\n")
        print("-" * 60 + "\n")
