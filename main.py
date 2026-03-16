import asyncio
from config.logger_setup import setup_logger
from data.market_fetcher import MarketFetcher
from data.macro_fetcher import MacroFetcher
from data.whale_alert_fetcher import WhaleAlertFetcher
from agents.coordinator import brain_orchestrator
from executor.trade_manager import TradeManager
from agents.notifier import BotState

logger = setup_logger("autopilot")

class OmegaApexAutopilot:
    def __init__(self):
        logger.info("Initializing OMEGA APEX Autopilot System...")
        self.market_fetcher = MarketFetcher("binance")
        self.macro_fetcher = MacroFetcher()
        self.whale_fetcher = WhaleAlertFetcher()
        self.trade_manager = TradeManager()
        self.symbols = ["BTC/USDT", "ETH/USDT"] 
        
    async def start(self):
        """Starts all background services and the main trading loop."""
        
        # 1. Start WebSockets for Market Data
        for symbol in self.symbols:
            self.market_fetcher.subscribe(symbol)
            
        # 2. Wait a moment for initial data to populate
        logger.info("Warming up data streams...")
        await asyncio.sleep(5)
        
        # 3. Enter the Infinite Loop
        logger.info("🔥 AUTOPILOT ENGAGED 🔥")
        while not self.trade_manager.is_halted:
            try:
                await self.run_trading_cycle()
            except Exception as e:
                logger.error(f"Error in trading cycle: {e}", exc_info=True)
            
            # Wait before next scan. Frequency depends on strategy, but let's default to 2 hours
            # To demonstrate dynamic scanning based on mode, we could adjust this, but we'll stick to 1 min for testing
            # In production this should be like 3600 (1 Hour) or 21600 (6 Hours) to save API costs.
            scan_interval = 60 if BotState.risk_strategy == "AGGRESSIVE" else 300 
            logger.info(f"Cycle complete. Waiting {scan_interval}s for next cycle...")
            await asyncio.sleep(scan_interval)
            
        logger.error("SYSTEM HALTED. Autopilot stopped.")
            
    async def run_trading_cycle(self):
        """A single iteration of data gathering, AI debate, and trade execution."""
        
        # Fetch Macro Weather (Global)
        macro_report = await self.macro_fetcher.fetch_latest_events()
        
        signals = {}
        for symbol in self.symbols:
            logger.info(f"\n--- Analyzing {symbol} ---")
            
            # 1. Fetch Local Data
            ticker = self.market_fetcher.get_ticker(symbol)
            ob_top = self.market_fetcher.get_order_book(symbol)
            whale_report = await self.whale_fetcher.fetch_whale_movements(symbol)
            
            if not ticker:
                logger.warning(f"No ticker data for {symbol}. Skipping.")
                continue
                
            market_data_str = f"Symbol: {symbol}\nPrice: {ticker.get('last_price')}\nVol: {ticker.get('volume')}\nOrder Book Bids (Top): {ob_top.get('bids')[:1]}\nAsks (Top): {ob_top.get('asks')[:1]}"
            
            # 2. Prepare State for AI Debate
            initial_state = {
                "market_data": market_data_str,
                "macro_report": macro_report,
                "whale_report": whale_report,
                "round_number": 1
            }
            
            # 3. Trigger LangGraph AI Brain
            logger.info("Summoning AI Council...")
            # Note: synchronous invoke because LangGraph compiles standard funcs here
            # In a fully async env, we'd use ainvoke().
            result = brain_orchestrator.invoke(initial_state)
            
            final_decision = result.get("final_decision", {})
            decision = final_decision.get("decision", "HOLD")
            confidence = final_decision.get("confidence", 0)
            reason = final_decision.get("reason", "No reason provided")
            
            logger.info(f"AI Verdict for {symbol}: {decision} ({confidence}%) - {reason}")
            
            if decision != "HOLD":
                signals[symbol] = final_decision
                
        # 4. Execute approved signals via TradeManager
        if signals:
             await self.trade_manager.auto_rebalance(signals)

if __name__ == "__main__":
    banner = """
    █████████  ██████   ██████ ██████████ █████████ ███████████
   ███░░░░░███░░██████ ██████ ░░███░░░░░█░███░░░░░█░░███░░░░░███
  ███     ░░░  ░███░█████░███  ░███  █ ░ ░███  █ ░  ░███    ░███
 ░███          ░███░░███ ░███  ░██████   ░██████    ░██████████ 
 ░███          ░███ ░░░  ░███  ░███░░█   ░███░░█    ░███░░░░░███
 ░░███     ███ ░███      ░███  ░███ ░   █░███ ░   █ ░███    ░███
  ░░█████████  █████     █████ ████████████████████ █████   █████
   ░░░░░░░░░  ░░░░░     ░░░░░ ░░░░░░░░░░░░░░░░░░░░ ░░░░░   ░░░░░
    >>> OMEGA APEX AUTOPILOT ENGINE v1.0 <<<
    """
    print(banner)
    
    # We must start both the Telegram Bot and the Autopilot.
    # The TradeManager internally initializes the ApexNotifier (Telegram bot) inside its __init__, and starts its polling in a background task.
    # Therefore, TradeManager initialization handles the Bot.
    
    autopilot = OmegaApexAutopilot()
    
    # Start loop
    try:
        asyncio.run(autopilot.start())
    except KeyboardInterrupt:
        logger.info("System interrupted by user.")
    except Exception as e:
        logger.critical(f"Fatal System Error: {e}", exc_info=True)
