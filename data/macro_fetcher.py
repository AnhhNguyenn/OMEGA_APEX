import asyncio
import aiohttp
import os
from config.logger_setup import setup_logger

logger = setup_logger("macro_fetcher")

class MacroFetcher:
    """
    Fetches global economic events and macro indicators.
    In a fully production scenario, connects to AlphaVantage, Fred, or ForexFactory APIs.
    """
    def __init__(self):
        self.api_key = os.environ.get("MACRO_API_KEY", "")
        self.base_url = "https://www.alphavantage.co/query" # Example integration
        self.current_macro_state = "Neutral"
        self.recent_events = []

    async def fetch_latest_events(self) -> str:
        """
        Polls for the Crypto Fear & Greed Index from alternative.me (Free API, accurate macro sentiment).
        Returns a summarized string for the AI agents.
        """
        logger.info("Fetching real Macro economic sentiment (Fear & Greed)...")
        try:
            async with aiohttp.ClientSession() as session:
                # Fetching real data!
                async with session.get("https://api.alternative.me/fng/?limit=1", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        index_data = data.get("data", [])[0]
                        value = index_data.get("value", "Unknown")
                        classification = index_data.get("value_classification", "Unknown")
                        
                        self.current_macro_state = f"{classification} ({value}/100)"
                        self.recent_events = [{"event": "Fear & Greed Index", "impact": "HIGH", "status": self.current_macro_state}]
                    else:
                        self.current_macro_state = "Neutral (API Error)"
            
            report = f"Macro State: {self.current_macro_state}\nEvents:\n"
            for ev in self.recent_events:
                report += f"- {ev['event']} (Impact: {ev['impact']}) - {ev['status']}\n"
                
            return report
        except Exception as e:
            logger.error(f"Error fetching macro data: {e}")
            return "Macro data unavailable. Proceed with caution."

if __name__ == "__main__":
    async def test():
        fetcher = MacroFetcher()
        print(await fetcher.fetch_latest_events())
    asyncio.run(test())
