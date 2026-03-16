import ccxt.async_support as ccxt
import asyncio
from typing import Dict, Any, List

class MarketFetcher:
    def __init__(self, exchange_id: str = "binance"):
        """
        Initialize the MarketFetcher for a specific exchange using CCXT.
        """
        self.exchange_id = exchange_id
        exchange_class = getattr(ccxt, self.exchange_id)
        
        # We start with public data fetching, so no API keys required immediately.
        # Can be configured to use keys for higher rate limits or private endpoints if needed.
        self.exchange = exchange_class({
            'enableRateLimit': True,
        })

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch real-time ticker data for a specific symbol.
        """
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "last_price": ticker.get("last"),
                "high": ticker.get("high"),
                "low": ticker.get("low"),
                "volume": ticker.get("baseVolume"),
                "vwap": ticker.get("vwap"),
                "timestamp": ticker.get("timestamp")
            }
        except Exception as e:
            print(f"Error fetching ticker for {symbol}: {e}")
            return {}

    async def fetch_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Fetch order book (L2 Data) for market depth analysis.
        """
        try:
            order_book = await self.exchange.fetch_order_book(symbol, limit)
            return {
                "symbol": symbol,
                "bids": order_book.get("bids", []),  # [price, amount]
                "asks": order_book.get("asks", []),  # [price, amount]
                "timestamp": order_book.get("timestamp")
            }
        except Exception as e:
            print(f"Error fetching order book for {symbol}: {e}")
            return {}
            
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List[float]]:
        """
        Fetch OHLCV (Open, High, Low, Close, Volume) data for technical analysis.
        """
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return ohlcv
        except Exception as e:
            print(f"Error fetching OHLCV for {symbol}: {e}")
            return []

    async def close(self):
        """
        Properly close the exchange session.
        """
        await self.exchange.close()

# For local testing
if __name__ == "__main__":
    async def main():
        fetcher = MarketFetcher("binance")
        symbol = "BTC/USDT"
        print(f"Fetching Ticker for {symbol}...")
        ticker = await fetcher.fetch_ticker(symbol)
        print(ticker)
        
        print(f"\\nFetching Order Book for {symbol}...")
        ob = await fetcher.fetch_order_book(symbol, limit=5)
        print(f"Top 5 Bids: {ob.get('bids')}")
        print(f"Top 5 Asks: {ob.get('asks')}")
        
        await fetcher.close()

    asyncio.run(main())
