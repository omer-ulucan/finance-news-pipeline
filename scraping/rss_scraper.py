"""
RSS Feed Scraper Module optimized for financial news within the last hour
"""

import asyncio
import aiohttp
import json
import feedparser
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import logging
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Time window for recent news - 1 hour for financial prediction
TIME_WINDOW = timedelta(hours=1)
now = datetime.now(timezone.utc)

# Global list to store news
news_list = []

# List of user agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
]

async def fetch_feed(session, source_name, feed_url, attempt=1):
    """
    Fetch and parse an RSS feed from the given URL with retry logic
    
    Args:
        session: aiohttp ClientSession
        source_name: Name of the news source
        feed_url: URL of the RSS feed
        attempt: Current attempt number
        
    Returns:
        Tuple of (source_name, feed_data)
    """
    # Fix common URL issues
    if feed_url.startswith("http://") and not feed_url.startswith("http://feeds."):
        feed_url = feed_url.replace("http://", "https://", 1)
    
    # Select a random user agent
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/"  # Sometimes helps with access
    }
    
    try:
        # Fetch the feed with timeout and headers
        async with session.get(feed_url, headers=headers, timeout=8) as response:
            if response.status != 200:
                if attempt < 2:  # Retry once
                    logging.warning(f"Retrying {feed_url} after {response.status} error (attempt {attempt})")
                    await asyncio.sleep(1)  # Wait a bit before retry
                    return await fetch_feed(session, source_name, feed_url, attempt + 1)
                else:
                    logging.error(f"Error fetching {feed_url}: HTTP status {response.status}")
                    return source_name, None
            
            content = await response.text()
            
            # Parse the feed with feedparser
            feed_data = feedparser.parse(content)
            
            # Check if the feed is valid
            if feed_data.get('bozo_exception'):
                logging.warning(f"Warning parsing {feed_url}: {feed_data.get('bozo_exception')}")
            
            if not feed_data.get('entries'):
                logging.warning(f"No entries found in {feed_url}")
            
            return source_name, feed_data
    
    except asyncio.TimeoutError:
        if attempt < 2:  # Retry once on timeout
            logging.warning(f"Retrying {feed_url} after timeout (attempt {attempt})")
            await asyncio.sleep(1)  # Wait a bit before retry
            return await fetch_feed(session, source_name, feed_url, attempt + 1)
        else:
            logging.error(f"Timeout fetching {feed_url}")
            return source_name, None
    except Exception as e:
        logging.error(f"Error fetching {feed_url}: {e}")
        return source_name, None

def filter_recent_news(source_name, feed_data):
    """
    Filter news items that are within the recent time window (1 hour)
    
    Args:
        source_name: Name of the news source
        feed_data: Parsed feed data from feedparser
        
    Returns:
        List of recent news items
    """
    if not feed_data or "entries" not in feed_data:
        return []
    
    recent_news = []
    for entry in feed_data.entries:
        try:
            # Get the published date
            date_struct = entry.get("published_parsed") or entry.get("updated_parsed")
            
            if date_struct:
                # Convert struct_time to datetime
                published_date = datetime(*date_struct[:6], tzinfo=timezone.utc)
                
                # Check if within time window
                if now - published_date <= TIME_WINDOW:
                    # Create news item
                    news_item = {
                        "source": source_name,
                        "title": entry.get("title", "No Title"),
                        "link": entry.get("link", ""),
                        "published": published_date.isoformat(),
                        "summary": entry.get("summary", "") or entry.get("description", "No Summary"),
                        "location": None
                    }
                    
                    # Clean up summary by removing HTML tags (simple method)
                    summary = news_item["summary"]
                    summary = summary.replace("<p>", "").replace("</p>", " ")
                    summary = summary.replace("<br>", " ").replace("<br/>", " ")
                    news_item["summary"] = summary
                    
                    recent_news.append(news_item)
            else:
                # For financial news, we're strict about dates
                # If no date, use current time but log a warning
                logging.warning(f"No date for entry from {source_name}, using current time")
                
                news_item = {
                    "source": source_name,
                    "title": entry.get("title", "No Title"),
                    "link": entry.get("link", ""),
                    "published": now.isoformat(),  # Use current time
                    "summary": entry.get("summary", "") or entry.get("description", "No Summary"),
                    "location": None
                }
                
                # Clean up summary
                summary = news_item["summary"]
                summary = summary.replace("<p>", "").replace("</p>", " ")
                summary = summary.replace("<br>", " ").replace("<br/>", " ")
                news_item["summary"] = summary
                
                recent_news.append(news_item)
                
        except Exception as e:
            logging.error(f"Error parsing entry from {source_name}: {e}")
    
    return recent_news

async def process_rss_feeds():
    """
    Process all RSS feeds defined in the configuration file
    
    Returns:
        List of news items collected
    """
    global news_list
    news_list = []  # Reset news list
    
    try:
        # Load RSS sources configuration
        with open("news/rss.json", "r", encoding="utf-8") as file:
            rss_sources = json.load(file)
        
        # Create ClientSession with connection limit
        conn = aiohttp.TCPConnector(limit=10)  # Limit concurrent connections
        timeout = aiohttp.ClientTimeout(total=30)  # Overall timeout
        
        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
            # Create tasks for all feeds
            tasks = []
            for source in rss_sources:
                for _, feed_url in source["rss_feeds"].items():
                    tasks.append(fetch_feed(session, source["source"], feed_url))
            
            # Execute all tasks concurrently
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions
            valid_responses = []
            for resp in responses:
                if isinstance(resp, Exception):
                    logging.error(f"Task error: {resp}")
                else:
                    valid_responses.append(resp)
            
            # Process feeds in parallel using ThreadPoolExecutor
            with ThreadPoolExecutor() as executor:
                filtered_news = list(executor.map(
                    lambda x: filter_recent_news(x[0], x[1]), 
                    valid_responses
                ))
            
            # Flatten news lists
            for group in filtered_news:
                news_list.extend(group)
            
            logging.info(f"{len(news_list)} news collected within the last hour!")
    
    except Exception as e:
        logging.error(f"Error in process_rss_feeds: {e}")
    
    # Important: Return the news_list explicitly, not just rely on global variable
    return news_list

if __name__ == "__main__":
    # When run directly, execute the feed processing
    collected_news = asyncio.run(process_rss_feeds())
    
    # Print some statistics
    print(f"Collected {len(collected_news)} news items from the last hour")
    
    # Print the first 3 news items as a sample
    for i, news in enumerate(collected_news[:3]):
        print(f"\n--- News {i+1} ---")
        print(f"Source: {news['source']}")
        print(f"Title: {news['title']}")
        print(f"Link: {news['link']}")
        print(f"Published: {news['published']}")
        print(f"Summary: {news['summary'][:100]}...")