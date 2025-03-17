import asyncio
import aiohttp
import json
import feedparser
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

TIME_WINDOW = timedelta(hours=1)
now = datetime.now(timezone.utc)

with open("../news/rss.json", "r", encoding="utf-8") as file:
    rss_sources = json.load(file)

news_list = []

async def fetch_feed(session, source_name, feed_url):
    if "cbc.ca" in feed_url and feed_url.startswith("http://"):
        feed_url = feed_url.replace("http://", "https://", 1)
        
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/115.0.0.0 Safari/537.36"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    try:
        async with session.get(feed_url, headers=headers, timeout=10) as response:
            if response.status != 200:
                print(f" Error fetching {feed_url}: HTTP status {response.status}")
                return source_name, None
            content = await response.text()
            return source_name, feedparser.parse(content)
    except Exception as e:
        print(f" Error fetching {feed_url}: {e}")
        return source_name, None

def filter_recent_news(source_name, feed_data):
    if not feed_data or "entries" not in feed_data:
        return []
    
    recent_news = []
    for entry in feed_data.entries:
        date_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if date_struct:
            try:
                published_date = datetime(*date_struct[:6], tzinfo=timezone.utc)
                if now - published_date <= TIME_WINDOW:
                    recent_news.append({
                        "source": source_name,
                        "title": entry.get("title", "No Title"),
                        "link": entry.get("link", ""),
                        "published": published_date.isoformat(),
                        "summary": entry.get("summary", "No Summary"),
                        "location": None
                    })
            except Exception as e:
                print(f"Error parsing date for {source_name}: {e}")
    return recent_news

async def process_rss_feeds():
    global news_list
    async with aiohttp.ClientSession() as session:
        tasks = []
        for source in rss_sources:
            for _, feed_url in source["rss_feeds"].items():
                tasks.append(fetch_feed(session, source["source"], feed_url))
                
        responses = await asyncio.gather(*tasks)
        
        with ThreadPoolExecutor() as executor:
            filtered_news = list(executor.map(lambda x: filter_recent_news(x[0], x[1]), responses))
            
        news_list = [news for group in filtered_news for news in group]

if __name__ == "__main__":
    asyncio.run(process_rss_feeds())
    print(f" {len(news_list)} news collected!")