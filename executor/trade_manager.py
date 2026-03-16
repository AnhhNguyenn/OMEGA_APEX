import ccxt
import time
from typing import Dict, Any

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
        self.active_positions = {}
        
        # Circuit Breaker thresholds
        self.max_loss_threshold_usd = 500  # Default $500 max loss ($R)
        self.expected_profit = expected_profit
        self.total_api_costs = 0.0
        self.is_halted = False

    def verify_connection(self) -> bool:
        """
        Check if API keys are valid by fetching balances.
        """
        try:
            # We wrap this in a try-catch for local testing without real keys
            balance = self.exchange.fetch_balance()
            return True
        except ccxt.AuthenticationError:
            print("Authentication failed: invalid keys.")
            return False
        except Exception as e:
            print(f"Connection verification failed: {e}")
            return False

    def check_circuit_breaker(self, current_loss: float) -> bool:
        """
        Verify if the system should halt trading.
        Halts if:
        1. Current drawdown exceeds max allowed ($R threshold).
        2. Accumulated operational/API costs exceed 10% of the daily expected profit.
        """
        if current_loss > self.max_loss_threshold_usd:
            print(f"CIRCUIT BREAKER TRIGGERED: Loss {current_loss} exceeds threshold {self.max_loss_threshold_usd}")
            self.is_halted = True
            return True
            
        max_allowed_cost = self.expected_profit * 0.10
        if self.total_api_costs > max_allowed_cost and self.expected_profit > 0:
            print(f"CIRCUIT BREAKER TRIGGERED: API Costs {self.total_api_costs} > 10% of target profit ({max_allowed_cost})")
            self.is_halted = True
            return True
            
        return False

    def auto_rebalance(self, signals: Dict[str, Dict[str, Any]]):
        """
        Auto-Rebalancing Logic:
        Close underperforming positions or those that do not meet daily expected yield,
        and re-allocate funds to assets with strong BUY signals.
        
        signals format:
        {
            "BTC/USDT": {"decision": "BUY", "confidence": 90, "daily_yield": 0.02},
            "ETH/USDT": {"decision": "SELL", "confidence": 85, "daily_yield": -0.01}
        }
        """
        if self.is_halted:
            print("System halted by Circuit Breaker. Rebalancing aborted.")
            return

        print("Executing Auto-Rebalancing...")
        
        # 1. Close underperforming positions
        for symbol, signal_data in signals.items():
            if signal_data.get("decision") == "SELL" and signal_data.get("confidence", 0) > 80:
                print(f"Closing position for {symbol} due to strong SELL signal.")
                # Mock execution:
                # self.exchange.create_market_sell_order(symbol, self.active_positions[symbol])
                if symbol in self.active_positions:
                    del self.active_positions[symbol]
                    
            elif signal_data.get("daily_yield", 1) < 0:
                print(f"Closing position for {symbol} due to negative internal yield.")
                if symbol in self.active_positions:
                    del self.active_positions[symbol]

        # 2. Open new positions on strong signals
        for symbol, signal_data in signals.items():
            if signal_data.get("decision") == "BUY" and signal_data.get("confidence", 0) > 85:
                if symbol not in self.active_positions:
                    print(f"Opening new position for {symbol} (Confidence: {signal_data.get('confidence')}%).")
                    # Mock execution:
                    # self.exchange.create_market_buy_order(symbol, amount)
                    self.active_positions[symbol] = "ACTIVE"
                    self.total_api_costs += 0.5 # Mock $0.5 API footprint per trade


# Local Testing
if __name__ == "__main__":
    manager = TradeManager("binance", "MOCK_KEY", "MOCK_SECRET", expected_profit=100.0)
    
    mock_signals = {
        "ETH/USDT": {"decision": "SELL", "confidence": 95, "daily_yield": -0.05},
        "BTC/USDT": {"decision": "BUY", "confidence": 90, "daily_yield": 0.03}
    }
    
    # We mock having ETH before
    manager.active_positions["ETH/USDT"] = "ACTIVE"
    print("Initial Positions:", manager.active_positions)
    
    manager.auto_rebalance(mock_signals)
    
    print("Positions after rebalance:", manager.active_positions)
    
    # Trigger breaker
    manager.check_circuit_breaker(current_loss=600)
    manager.auto_rebalance(mock_signals) # Should fail
