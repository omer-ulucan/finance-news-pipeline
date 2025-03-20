"""
Simple location extractor that works directly with spaCy without async complexity
"""
import time
import logging
from typing import List, Dict, Any, Optional
import spacy
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load spaCy for NER
try:
    nlp = spacy.load("en_core_web_sm", disable=["tok2vec", "tagger", "parser", "attribute_ruler", "lemmatizer"])
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning("spaCy not available - install with: pip install spacy && python -m spacy download en_core_web_sm")

def extract_location_from_text(text: str) -> Optional[str]:
    """
    Extract location from text using spaCy NER
    """
    if not SPACY_AVAILABLE or not text:
        return None
    
    # Process only the first 500 chars for speed
    if len(text) > 500:
        text = text[:500]
    
    # Process the text with spaCy
    doc = nlp(text)
    
    # Find the first GPE (country, city) or LOC (location) entity
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"]:
            return ent.text
    
    # Backup method: Try to find location patterns
    # Common location patterns in financial news
    location_patterns = [
        r'in ([A-Z][a-z]+)',  # "in London", "in Tokyo"
        r'from ([A-Z][a-z]+)',  # "from Washington"
        r'at ([A-Z][a-z]+)',  # "at Frankfurt"
    ]
    
    for pattern in location_patterns:
        matches = re.findall(pattern, text)
        if matches:
            return matches[0]
    
    return None

def add_locations(news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add locations to all news items - simple synchronous version
    """
    start_time = time.time()
    
    if not news_list:
        return []
    
    if not SPACY_AVAILABLE:
        logging.error("spaCy is required for location extraction")
        return news_list
    
    # Process each news item
    for news in news_list:
        # Skip if already has location
        if news.get("location"):
            continue
        
        # Extract location from title and summary
        combined_text = f"{news.get('title', '')}. {news.get('summary', '')}"
        location = extract_location_from_text(combined_text)
        news["location"] = location
    
    # Count news with locations
    location_count = sum(1 for item in news_list if item.get("location"))
    
    elapsed_time = time.time() - start_time
    logging.info(f"Added locations to {location_count}/{len(news_list)} news items in {elapsed_time:.2f} seconds")
    
    return news_list

# For testing directly
if __name__ == "__main__":
    # Sample news items for testing
    test_news = [
        {
            "source": "CNN",
            "title": "Stock markets plunge amid recession fears",
            "link": "https://www.bbc.com/news/world",
            "summary": "Global markets experienced significant drops as investors worry about economic downturn in Europe."
        },
        {
            "source": "BBC",
            "title": "COVID cases rise in Europe",
            "link": "https://www.bbc.com/news/uk",
            "summary": "Several European countries are seeing increased COVID-19 infections."
        }
    ]
    
    # Process the news
    processed_news = add_locations(test_news)
    
    # Print results
    for news in processed_news:
        print(f"Title: {news['title']}")
        print(f"Location: {news.get('location', 'Not found')}")
        print()