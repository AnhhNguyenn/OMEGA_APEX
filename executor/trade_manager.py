import ccxt
import time
import traceback
from typing import Dict, Any

from data.db_manager import DatabaseManager
from agents.notifier import ApexNotifier
from config.logger_setup import setup_logger

logger = setup_logger("trade_manager")

class TradeManager:
    def __init__(self, exchange_id: str, api_key: str, secret: str, expected_profit: float = 0.0):
        """
        Initialize the execution engine with Trade-Only API keys.
        """
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
        })
        self.active_positions: Dict[str, Any] = {}
        
        # Circuit Breaker thresholds
        self.max_loss_threshold_usd = 500.0  # Safe default $R 
        self.expected_daily_profit = expected_profit
        self.total_api_costs = 0.0
        self.is_halted = False
        self.db = DatabaseManager()
        self.notifier = ApexNotifier()
        self.milestone_thresholds = [20000, 50000, 100000, 1000000, 1000000000, 30000000000]

    def verify_connection(self) -> bool:
        """
        Check if API keys are valid by fetching balances.
        """
        try:
            # We wrap this in a try-catch for local testing without real keys
            balance = self.exchange.fetch_balance()
            return True
        except ccxt.AuthenticationError:
            logger.error("Authentication failed: invalid keys.")
            return False
        except Exception as e:
            err_msg = traceback.format_exc()
            logger.error(f"Connection verification failed: \n{err_msg}")
            self.db.log_system_error("ERROR", err_msg, 0.0)
            return False

    def check_circuit_breaker(self, current_loss: float) -> bool:
        """
        Verify if the system should halt trading.
        Halts if:
        1. Current drawdown exceeds max allowed ($R threshold).
        2. Accumulated operational/API costs exceed 10% of the daily expected profit.
        """
        if current_loss > self.max_loss_threshold_usd:
            msg = f"Loss {current_loss} exceeds threshold {self.max_loss_threshold_usd}"
            logger.warning(f"CIRCUIT BREAKER TRIGGERED: {msg}")
            self.notifier.notify_circuit_breaker(msg)
            self.is_halted = True
            return True
            
        max_allowed_cost = self.expected_daily_profit * 0.10
        if self.total_api_costs > max_allowed_cost and self.expected_daily_profit > 0:
            msg = f"API Costs {self.total_api_costs} > 10% of target profit ({max_allowed_cost})"
            logger.warning(f"CIRCUIT BREAKER TRIGGERED: {msg}")
            self.notifier.notify_circuit_breaker(msg)
            self.is_halted = True
            return True
            
        return False

    def check_milestone(self, current_balance: float):
        """
        Check if current balance has reached a new milestone and notify.
        """
        achieved = []
        for threshold in self.milestone_thresholds:
            if current_balance >= threshold:
                self.notifier.notify_milestone(f"Crossed ${threshold:,.2f}!", current_balance)
                achieved.append(threshold)
                
        for t in achieved:
            self.milestone_thresholds.remove(t)

    def auto_rebalance(self, signals: Dict[str, Dict[str, Any]]):
        """
        Auto-Rebalancing Logic:
        Close underperforming positions or those that do not meet daily expected yield,
        and re-allocate funds to assets with strong BUY signals.
        """
        if self.is_halted:
            logger.warning("System halted by Circuit Breaker. Rebalancing aborted.")
            return

        logger.info("Executing Auto-Rebalancing...")
        
        # 1. Close underperforming positions
        for symbol, signal_data in signals.items():
            if symbol in self.active_positions:
                if signal_data.get("decision") == "SELL" and signal_data.get("confidence", 0) > 80:
                    logger.info(f"Closing position for {symbol} due to strong SELL signal.")
                    try:
                        # Assuming holding amount is tracked or fetched. For now, executing a close.
                        # We would ideally fetch the actual balance of the base currency here.
                        # Mocking balance amount for syntax:
                        amount_to_sell = self.active_positions[symbol].get("amount", 0)
                        if amount_to_sell > 0:
                            order = self.exchange.create_market_sell_order(symbol, amount_to_sell)
                            fee = order.get('fee', {}).get('cost', 0.5) # approximate if not returned
                            price = order.get('price', 0.0)
                            self.total_api_costs += fee
                            self.db.log_trade(symbol, "SELL", amount_to_sell, price, fee)
                        del self.active_positions[symbol]
                    except Exception as e:
                        err_msg = traceback.format_exc()
                        logger.error(f"Failed to sell {symbol}:\n{err_msg}")
                        self.db.log_system_error("ERROR", err_msg, 0.0)
                        
                elif signal_data.get("daily_yield", 1) < 0:
                    logger.info(f"Closing position for {symbol} due to negative internal yield.")
                    try:
                        amount_to_sell = self.active_positions[symbol].get("amount", 0)
                        if amount_to_sell > 0:
                            order = self.exchange.create_market_sell_order(symbol, amount_to_sell)
                            fee = order.get('fee', {}).get('cost', 0.5) 
                            price = order.get('price', 0.0)
                            self.total_api_costs += fee
                            self.db.log_trade(symbol, "SELL", amount_to_sell, price, fee)
                        del self.active_positions[symbol]
                    except Exception as e:
                        err_msg = traceback.format_exc()
                        logger.error(f"Failed to sell {symbol}:\n{err_msg}")
                        self.db.log_system_error("ERROR", err_msg, 0.0)

        # 2. Open new positions on strong signals
        for symbol, signal_data in signals.items():
            if signal_data.get("decision") == "BUY" and signal_data.get("confidence", 0) > 85:
                if symbol not in self.active_positions:
                    logger.info(f"Opening new position for {symbol} (Confidence: {signal_data.get('confidence')}%).")
                    try:
                        # Determine order size (normally done via calculating Kelly fraction from math_tools)
                        # Here we use a safe minimal standard or fractional split of capital for the demo code structure
                        amount_to_buy = 0.01 # Placeholder for exact size calculated elsewhere
                        order = self.exchange.create_market_buy_order(symbol, amount_to_buy)
                        
                        fee = order.get('fee', {}).get('cost', 0.5)
                        price = order.get('price', 0.0)
                        self.total_api_costs += fee
                        self.active_positions[symbol] = {"status": "ACTIVE", "amount": amount_to_buy}
                        self.db.log_trade(symbol, "BUY", amount_to_buy, price, fee)
                        self.notifier.notify_trade_approved(symbol, "BUY", amount_to_buy, signal_data.get('confidence', 0))
                    except Exception as e:
                        err_msg = traceback.format_exc()
                        logger.error(f"Failed to buy {symbol}:\n{err_msg}")
                        self.db.log_system_error("ERROR", err_msg, 0.0)


# Local Testing
if __name__ == "__main__":
    manager = TradeManager("binance", "MOCK_KEY", "MOCK_SECRET", expected_profit=100.0)
    
    mock_signals = {
        "ETH/USDT": {"decision": "SELL", "confidence": 95, "daily_yield": -0.05},
        "BTC/USDT": {"decision": "BUY", "confidence": 90, "daily_yield": 0.03}
    }
    
    # We mock having ETH before
    manager.active_positions["ETH/USDT"] = {"status": "ACTIVE", "amount": 0.05}
    logger.info(f"Initial Positions: {manager.active_positions}")
    
    manager.auto_rebalance(mock_signals)
    
    logger.info(f"Positions after rebalance: {manager.active_positions}")
    
    # Trigger breaker
    manager.check_circuit_breaker(current_loss=600)
    manager.auto_rebalance(mock_signals) # Should fail
