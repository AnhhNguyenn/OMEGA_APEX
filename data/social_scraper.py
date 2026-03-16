import aiohttp
import asyncio
import json
from bs4 import BeautifulSoup
from typing import List, Dict, Any

class SocialScraper:
    def __init__(self, batch_size: int = 50):
        """
        Initialize the scraper.
        Batch size defines how many raw news items to semantic-batch into one JSON sequence.
        """
        self.batch_size = batch_size

    async def fetch_html(self, session: aiohttp.ClientSession, url: str) -> str:
        """
        Fetch raw HTML content from a URL asynchronously.
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"Failed to fetch {url}: Status {response.status}")
                    return ""
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""

    def parse_mock_news(self, html: str) -> List[Dict[str, str]]:
        """
        A generic mock parser using BeautifulSoup to extract paragraph texts.
        In a real scenario, this would target specific news sites or RSS feeds.
        """
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract headers and paragraphs as mockup news items
        items = []
        for element in soup.find_all(['h2', 'h3', 'p']):
            text = element.get_text(strip=True)
            if len(text) > 30: # Filter out very short UI texts
                items.append({"content": text, "source": "web_scrape"})
                
        return items

    def create_semantic_batches(self, items: List[Dict[str, str]]) -> List[str]:
        """
        Group multiple extracted text items into JSON string batches.
        This optimizes AI token usage by submitting a large array of items to the LLM
        instead of multiple small requests.
        """
        batches = []
        for i in range(0, len(items), self.batch_size):
            batch_slice = items[i:i + self.batch_size]
            batch_json = json.dumps({"batch_id": i // self.batch_size, "items": batch_slice}, ensure_ascii=False)
            batches.append(batch_json)
        return batches

    async def scrape_and_batch(self, urls: List[str]) -> List[str]:
        """
        Main runner: scrape multiple URLs concurrently and create semantic batches.
        """
        all_items = []
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_html(session, url) for url in urls]
            html_results = await asyncio.gather(*tasks)
            
            for html in html_results:
                items = self.parse_mock_news(html)
                all_items.extend(items)
                
        # Group into semantic batches
        batched_jsons = self.create_semantic_batches(all_items)
        return batched_jsons

# For local testing
if __name__ == "__main__":
    async def main():
        scraper = SocialScraper(batch_size=5)
        # Using a public site with lots of text for mock scraping
        test_urls = ["https://en.wikipedia.org/wiki/Cryptocurrency", "https://en.wikipedia.org/wiki/Algorithmic_trading"]
        print(f"Scraping URLs: {test_urls}...")
        
        batches = await scraper.scrape_and_batch(test_urls)
        print(f"Generated {len(batches)} semantic batches.")
        
        if batches:
            print(f"\\nPreview of First Batch (JSON string):")
            # Print a snippet to keep output clean
            print(f"{batches[0][:500]}...")
            
    asyncio.run(main())
