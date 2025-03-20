"""
RSS News Tracking System - Main Program
This program collects news from RSS sources, filters them, and adds location information.
"""

import asyncio
import json
import time
import logging
import os
from datetime import datetime

# Create required directories first
os.makedirs("logs", exist_ok=True)
os.makedirs("results", exist_ok=True)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/news_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)

# Modules
from scraping.rss_scraper import process_rss_feeds
from modules.news_filter import remove_duplicates_lsh
from modules.location_extractor import add_locations

async def main():
    """
    Main program function. Collects, filters, and adds location to news in sequence.
    """
    total_start_time = time.time()
    
    # ----- STEP 1: RSS NEWS COLLECTION -----
    logging.info("Collecting news from RSS sources...")
    rss_start_time = time.time()
    
    try:
        # Collect news from RSS feeds
        collected_news = await process_rss_feeds()
        collected_count = len(collected_news)
        rss_time = time.time() - rss_start_time
        logging.info(f"Collected {collected_count} news items ({rss_time:.2f} seconds)")
    except Exception as e:
        logging.error(f"RSS collection error: {str(e)}")
        return
    
    if not collected_news:
        logging.warning("No news collected! Terminating process.")
        return
    
    # ----- STEP 2: NEWS FILTERING -----
    logging.info("Filtering news and removing duplicates...")
    filter_start_time = time.time()
    
    try:
        filtered_news = remove_duplicates_lsh(collected_news)
        filter_time = time.time() - filter_start_time
        logging.info(f"{len(filtered_news)} unique news items remaining from {len(collected_news)} ({filter_time:.2f} seconds)")
    except Exception as e:
        logging.error(f"Filtering error: {str(e)}")
        return
    
    # ----- STEP 3: ADDING LOCATIONS -----
    logging.info("Adding location information to news items...")
    location_start_time = time.time()
    
    try:
        # Use the simple synchronous location extractor
        news_with_locations = add_locations(filtered_news)
        
        location_time = time.time() - location_start_time
        
        # Calculate number of news with locations
        location_count = sum(1 for news in news_with_locations if news.get("location"))
        location_percentage = location_count / len(news_with_locations) * 100 if news_with_locations else 0
        
        logging.info(f"Location info: Added to {location_count}/{len(news_with_locations)} news items "
                     f"({location_percentage:.1f}%, {location_time:.2f} seconds)")
    except Exception as e:
        logging.error(f"Location addition error: {str(e)}")
        return
    
    # ----- STEP 4: SAVE RESULTS -----
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"results/processed_news_{timestamp}.json"
    
    try:
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(news_with_locations, f, ensure_ascii=False, indent=2)
        logging.info(f"Processed news saved to: {result_file}")
    except Exception as e:
        logging.error(f"Error saving results: {str(e)}")
    
    # ----- PERFORMANCE REPORT -----
    total_time = time.time() - total_start_time
    logging.info(f"\nPERFORMANCE REPORT:")
    logging.info(f"  - RSS Collection:    {rss_time:.2f}s ({rss_time/total_time*100:.1f}%)")
    logging.info(f"  - Filtering:         {filter_time:.2f}s ({filter_time/total_time*100:.1f}%)")
    logging.info(f"  - Location Addition: {location_time:.2f}s ({location_time/total_time*100:.1f}%)")
    logging.info(f"  - Total Time:        {total_time:.2f}s")
    logging.info(f"  - Processing Steps:  {len(collected_news)} → {len(filtered_news)} → {len(news_with_locations)}")
    
    # ----- SHOW SAMPLE NEWS -----
    if news_with_locations:
        logging.info("\nSAMPLE PROCESSED NEWS:")
        for i, news in enumerate(news_with_locations[:5]):  # Show first 5 news
            logging.info(f"  {i+1}. {news['source']}: {news['title'][:50]}...")
            logging.info(f"     Link: {news['link']}")
            logging.info(f"     Location: {news.get('location', 'None')}")
            logging.info(f"     Published: {news.get('published', 'Unknown')}")
            logging.info("")

if __name__ == "__main__":
    try:
        logging.info("=== RSS NEWS TRACKING SYSTEM STARTING ===")
        asyncio.run(main())
        logging.info("=== PROCESS COMPLETED ===")
    except KeyboardInterrupt:
        logging.info("Stopped by user.")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")