import feedparser
import json
import os
import time
import logging
from datetime import datetime, timedelta
import dateparser
from bs4 import BeautifulSoup

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RSSFetcher:
    def __init__(self):
        self.processed_file = "processed_news.json"
        self.feeds = [
            # Dainik Jagran
            "https://rss.jagran.com/rss/news/national.xml",
            "https://rss.jagran.com/rss/news/world.xml",
            "https://rss.jagran.com/rss/entertainment.xml",
            
            # Amar Ujala
            "https://www.amarujala.com/rss/india-news.xml",
            "https://www.amarujala.com/rss/world.xml",
            
            # Navbharat Times
            "https://navbharattimes.indiatimes.com/india/rssfeedsection/15636828.cms",
            "https://navbharattimes.indiatimes.com/world/rssfeedsection/2279801.cms",
            
            # Zee News
            "https://zeenews.india.com/hindi/india.xml",
            "https://zeenews.india.com/hindi/world.xml",
            "https://zeenews.india.com/hindi/entertainment.xml",

            # News18 India
            "https://hindi.news18.com/common-feeds/v1/hin/rss/nation.xml",
            "https://hindi.news18.com/common-feeds/v1/hin/rss/world.xml",

            # TV9 Bharatvarsh
            "https://www.tv9hindi.com/feed",
            
            # BBC Hindi
            "https://feeds.bbci.co.uk/hindi/rss.xml"
        ]
        self._load_processed()

    def _load_processed(self):
        if os.path.exists(self.processed_file):
            try:
                with open(self.processed_file, 'r', encoding='utf-8') as f:
                    self.processed = json.load(f)
            except:
                self.processed = []
        else:
            self.processed = []

    def _save_processed(self):
        # Keep only last 1000 items to avoid file growing indefinitely
        if len(self.processed) > 1000:
            self.processed = self.processed[-1000:]
        
        with open(self.processed_file, 'w', encoding='utf-8') as f:
            json.dump(self.processed, f, ensure_ascii=False, indent=2)

    def is_processed(self, link):
        return link in self.processed

    def mark_processed(self, link):
        if link not in self.processed:
            self.processed.append(link)
            self._save_processed()

    def fetch_all_news(self):
        """
        Fetches news from all registered feeds, de-duplicates, and returns a list of raw news items.
        Returns: List of dicts {title, link, summary, published, source, image}
        """
        all_news = []
        logging.info(f"📡 Fetching from {len(self.feeds)} RSS feeds...")

        for feed_url in self.feeds:
            try:
                # Parse Feed
                d = feedparser.parse(feed_url)
                
                if not d.entries:
                    continue

                source_name = d.feed.get('title', 'Unknown Source')
                
                for entry in d.entries[:10]: # Check top 10 per feed
                    link = entry.get('link', '')
                    if not link or self.is_processed(link):
                        continue

                    title = entry.get('title', '')
                    summary = entry.get('summary', '') or entry.get('description', '')
                    
                    # Clean up summary (remove HTML)
                    soup = BeautifulSoup(summary, "html.parser")
                    summary_clean = soup.get_text()[:500] # Limit length

                    # Try to find an image
                    image_url = None
                    
                    # Method 1: Media Content / Enclosures (Standard RSS)
                    if 'media_content' in entry:
                        media = entry.media_content
                        if media and isinstance(media, list):
                            image_url = media[0].get('url')
                    
                    if not image_url and 'media_thumbnail' in entry:
                         media = entry.media_thumbnail
                         if media and isinstance(media, list):
                            image_url = media[0].get('url')

                    # Method 2: Extract from summary HTML (Common in some feeds)
                    if not image_url:
                        img_tag = soup.find('img')
                        if img_tag:
                            image_url = img_tag.get('src')
                    
                    # Filter out tiny tracking pixels or low qual images if possible? 
                    # For now, just take what we get.
                    
                    # Published Date Check (ensure it's somewhat recent, e.g. last 24h)
                    pub_str = entry.get('published', '')
                    is_fresh = True
                    if pub_str:
                        pub_date = dateparser.parse(pub_str)
                        if pub_date:
                            # If older than 24 hours, skip
                            if datetime.now(pub_date.tzinfo) - pub_date > timedelta(hours=24):
                                is_fresh = False
                    
                    if is_fresh and title:
                        all_news.append({
                            "title": title,
                            "summary": summary_clean,
                            "link": link,
                            "source": source_name,
                            "image": image_url,
                            "published": pub_str
                        })
            
            except Exception as e:
                logging.error(f"❌ Error fetching {feed_url}: {e}")

        logging.info(f"✅ Found {len(all_news)} fresh news items.")
        return all_news

if __name__ == "__main__":
    fetcher = RSSFetcher()
    news = fetcher.fetch_all_news()
    for i, n in enumerate(news[:5]):
        print(f"[{i+1}] {n['title']} ({n['source']})")
        print(f"    Img: {n['image']}")
