import ccxt.pro as ccxtpro
import asyncio
from typing import Dict, Any, List

class MarketFetcher:
    def __init__(self, exchange_id: str = "binance"):
        """
        Initialize the MarketFetcher for a specific exchange using CCXT Pro (WebSockets).
        """
        self.exchange_id = exchange_id
        exchange_class = getattr(ccxtpro, self.exchange_id)
        
        # We start with public data fetching, so no API keys required immediately.
        # Can be configured to use keys for higher rate limits or private endpoints if needed.
        self.exchange = exchange_class({
            'enableRateLimit': True,
        })
        
        # Memory cache for real-time data
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._streaming_tasks: List[asyncio.Task] = []

    async def start_ticker_stream(self, symbol: str):
        """
        Continuously stream ticker data and update the cache.
        """
        if symbol not in self.cache:
            self.cache[symbol] = {}
            
        while True:
            try:
                ticker = await self.exchange.watch_ticker(symbol)
                self.cache[symbol]['ticker'] = {
                    "symbol": symbol,
                    "last_price": ticker.get("last"),
                    "high": ticker.get("high"),
                    "low": ticker.get("low"),
                    "volume": ticker.get("baseVolume"),
                    "vwap": ticker.get("vwap"),
                    "timestamp": ticker.get("timestamp")
                }
            except Exception as e:
                print(f"Error streaming ticker for {symbol}: {e}")
                await asyncio.sleep(1) # Retry backoff on error

    async def start_order_book_stream(self, symbol: str, limit: int = 20):
        """
        Continuously stream order book data and update the cache.
        """
        if symbol not in self.cache:
            self.cache[symbol] = {}
            
        while True:
            try:
                order_book = await self.exchange.watch_order_book(symbol, limit)
                self.cache[symbol]['order_book'] = {
                    "symbol": symbol,
                    "bids": order_book.get("bids", []),  # [price, amount]
                    "asks": order_book.get("asks", []),  # [price, amount]
                    "timestamp": order_book.get("timestamp")
                }
            except Exception as e:
                print(f"Error streaming order book for {symbol}: {e}")
                await asyncio.sleep(1)

    def subscribe(self, symbol: str):
        """
        Subscribe to data streams for a specific symbol.
        """
        ticker_task = asyncio.create_task(self.start_ticker_stream(symbol))
        ob_task = asyncio.create_task(self.start_order_book_stream(symbol))
        self._streaming_tasks.extend([ticker_task, ob_task])
        print(f"Started streams for {symbol}")

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get the latest ticker from cache. (Synchronous, instant access)
        """
        return self.cache.get(symbol, {}).get('ticker', {})

    def get_order_book(self, symbol: str) -> Dict[str, Any]:
        """
        Get the latest order book from cache. (Synchronous, instant access)
        """
        return self.cache.get(symbol, {}).get('order_book', {})
        
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List[float]]:
        """
        Fetch OHLCV. We use watch_ohlcv with WebSockets.
        """
        try:
            ohlcv = await self.exchange.watch_ohlcv(symbol, timeframe, limit=limit)
            return ohlcv
        except Exception as e:
            print(f"Error streaming OHLCV for {symbol}: {e}")
            return []

    async def close(self):
        """
        Properly close the exchange session and cancel streaming tasks.
        """
        for task in self._streaming_tasks:
            task.cancel()
        await self.exchange.close()

# For local testing
if __name__ == "__main__":
    async def main():
        fetcher = MarketFetcher("binance")
        symbol = "BTC/USDT"
        
        # Subscribe starts the background tasks
        fetcher.subscribe(symbol)
        
        print("Waiting for data to populate...")
        await asyncio.sleep(5)  # Let the stream run for a few seconds
        
        print(f"\nLatest Ticker from Cache:")
        print(fetcher.get_ticker(symbol))
        
        print(f"\nLatest Order Book from Cache (Top 1 bid/ask):")
        ob = fetcher.get_order_book(symbol)
        print(f"Bids: {ob.get('bids')[:1] if ob.get('bids') else []}")
        print(f"Asks: {ob.get('asks')[:1] if ob.get('asks') else []}")
        
        await fetcher.close()

    asyncio.run(main())
