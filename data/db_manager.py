import os
import yaml
import json
from typing import Dict, Any, List
import datetime
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self):
        """
        Mocked DatabaseManager to run without Supabase locally.
        """
        print("Supabase client mocked (dependency removed for local build). Logs will go to local files.")
        self.client = None # Keeps structure intact

    def log_agent_debate(self, symbol: str, state: Dict[str, Any]):
        """Save the entire agent debate round to a local file."""
        try:
            data = {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "symbol": symbol,
                "round_number": state.get("round_number", 0),
                "scout_report": str(state.get("scout_report", "")),
                "analyst_report": str(state.get("analyst_report", "")),
                "skeptic_report": str(state.get("skeptic_report", "")),
                "final_decision": state.get("final_decision", {})
            }
            with open("mock_db_debates.jsonl", "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            print(f"Error logging agent debate to Local Mock: {e}")

    def log_trade(self, symbol: str, side: str, amount: float, price: float, fee: float):
        """Save executed trade details (Buy/Sell) to a local file."""
        try:
            data = {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
                "fee": fee
            }
            with open("mock_db_trades.jsonl", "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            print(f"Error logging trade to Local Mock: {e}")

    def log_balance_update(self, total_balance: float, max_drawdown: float = 0.0):
        """Log account balance variation over time."""
        pass

    def log_system_error(self, error_level: str, error_message: str, current_capital: float = 0.0):
        """Log critical system errors to a local file."""
        try:
            data = {
                "error_level": error_level,
                "error_message": error_message,
                "current_capital": current_capital,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            with open("mock_db_errors.jsonl", "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            print(f"Error logging system error to Local Mock: {e}")

    def get_recent_errors(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Query system errors in the last X hours."""
        return []

    def sync_config_to_supabase(self, config_path: str = "config.yaml"):
        """Mocked sync."""
        print("Mocked config sync completed.")

# For testing locally
if __name__ == "__main__":
    db = DatabaseManager()
    db.sync_config_to_supabase()
