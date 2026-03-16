import asyncio
import ccxt.pro as ccxtpro
from config.logger_setup import setup_logger

logger = setup_logger("whale_fetcher")

class WhaleAlertFetcher:
    """
    Monitors large exchange trades by fetching recent trade history via CCXT.
    Identifies 'Whale' transactions (e.g., > $100,000 in a single market order).
    """
    def __init__(self, exchange_id: str = "binance"):
        self.exchange = getattr(ccxtpro, exchange_id)({"enableRateLimit": True})
        self.whale_threshold_usd = 100000  # $100k USD
        self.recent_alerts = []

    async def fetch_whale_movements(self, symbol: str) -> str:
        """
        Fetches recent public trades for the symbol and filters for massive orders.
        """
        logger.info(f"Scanning real-time whale movements for {symbol}...")
        try:
            # Fetch last 1000 trades (limit varies by exchange, 1000 is typical max for Binance public API)
            # We use the REST fallback for a quick snapshot, though watch_trades is better for streams.
            trades = await self.exchange.fetch_trades(symbol, limit=100)
            
            whales_buy = 0
            whales_sell = 0
            largest_trade = None
            max_usd = 0
            
            for t in trades:
                price = t.get('price', 0)
                amount = t.get('amount', 0)
                usd_value = price * amount
                
                if usd_value >= self.whale_threshold_usd:
                    side = t.get('side', 'unknown').upper()
                    if side == 'BUY':
                        whales_buy += usd_value
                    elif side == 'SELL':
                        whales_sell += usd_value
                        
                    if usd_value > max_usd:
                        max_usd = usd_value
                        largest_trade = {"side": side, "value": usd_value, "amount": amount}

            self.recent_alerts = []
            if largest_trade:
                self.recent_alerts.append(f"🔥 LARGEST TRADE: {largest_trade['side']} {largest_trade['amount']} {symbol.split('/')[0]} (${largest_trade['value']:,.0f})")
                
            if whales_buy > 0 or whales_sell > 0:
                self.recent_alerts.append(f"Total Whale Buy Volume: ${whales_buy:,.0f}")
                self.recent_alerts.append(f"Total Whale Sell Volume: ${whales_sell:,.0f}")
                net_flow = whales_buy - whales_sell
                self.recent_alerts.append(f"Net Whale Flow: ${net_flow:,.0f} ({'BULLISH' if net_flow > 0 else 'BEARISH'})")
            else:
                self.recent_alerts.append(f"No single trade > ${self.whale_threshold_usd:,.0f} detected in recent history.")
                
            report = f"Whale Radar for {symbol}:\n" + "\n".join([f"- {a}" for a in self.recent_alerts])
            return report
            
        except Exception as e:
            logger.error(f"Error fetching whale data: {e}", exc_info=True)
            return "Whale data unavailable."

if __name__ == "__main__":
    async def test():
        fetcher = WhaleAlertFetcher()
        print(await fetcher.fetch_whale_movements("BTC/USDT"))
        await fetcher.exchange.close()
    asyncio.run(test())
