import aiohttp
import asyncio
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from config.logger_setup import setup_logger

logger = setup_logger("social_scraper")

class SocialScraper:
    def __init__(self, batch_size: int = 20):
        """
        Fetches live crypto news via RSS feeds to feed the Scout AI.
        """
        self.batch_size = batch_size
        # Using public RSS feeds for live Crypto news
        self.rss_feeds = [
            "https://cointelegraph.com/rss/tag/bitcoin",
            "https://cointelegraph.com/rss/tag/altcoin"
        ]

    async def fetch_rss(self, session: aiohttp.ClientSession, url: str) -> str:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"Failed to fetch RSS {url}: Status {response.status}")
                    return ""
        except Exception as e:
            logger.error(f"Error fetching RSS {url}: {e}")
            return ""

    def parse_rss_news(self, xml_data: str) -> List[Dict[str, str]]:
        if not xml_data:
            return []
            
        items = []
        try:
            root = ET.fromstring(xml_data)
            for item in root.findall('.//item'):
                title = item.find('title').text if item.find('title') is not None else ""
                # Some RSS feeds put the main content in description or content:encoded
                desc = item.find('description').text if item.find('description') is not None else ""
                if title:
                    # Strip basic HTML tags from description if present
                    import re
                    clean_desc = re.sub('<[^<]+>', '', desc)[:200] # keep it short
                    items.append({"title": title, "summary": clean_desc})
        except Exception as e:
            logger.error(f"Error parsing RSS XML: {e}")
            
        return items

    def create_semantic_batches(self, items: List[Dict[str, str]]) -> List[str]:
        batches = []
        for i in range(0, len(items), self.batch_size):
            batch_slice = items[i:i + self.batch_size]
            batch_json = json.dumps({"news_batch": batch_slice}, ensure_ascii=False)
            batches.append(batch_json)
        return batches

    async def scrape_latest_news(self) -> str:
        """
        Fetches live news from all configured RSS feeds and returns a summarized JSON string.
        """
        all_items = []
        logger.info("Fetching LIVE Crypto News via RSS...")
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_rss(session, url) for url in self.rss_feeds]
            xml_results = await asyncio.gather(*tasks)
            
            for xml_data in xml_results:
                items = self.parse_rss_news(xml_data)
                all_items.extend(items)
                
        # We only need the top 15 most recent news items to avoid blowing up the LLM context
        top_items = all_items[:15]
        if not top_items:
            return "No recent news found."
            
        return json.dumps({"live_news": top_items})

# For local testing
if __name__ == "__main__":
    async def main():
        scraper = SocialScraper()
        news = await scraper.scrape_latest_news()
        print(f"Scraped Live News Data:\n{news[:1000]}...")
            
    asyncio.run(main())
