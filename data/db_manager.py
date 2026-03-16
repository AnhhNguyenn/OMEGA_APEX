import os
import yaml
from typing import Dict, Any, List
from supabase import create_client, Client
import datetime
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self):
        """
        Initialize Supabase connection using environment variables.
        """
        self.supabase_url: str = os.environ.get("SUPABASE_URL", "")
        self.supabase_key: str = os.environ.get("SUPABASE_KEY", "")
        
        if not self.supabase_url or not self.supabase_key:
            print("WARNING: SUPABASE_URL or SUPABASE_KEY not found in .env. Database features will be mocked/disabled.")
            self.client = None
        else:
            try:
                self.client: Client = create_client(self.supabase_url, self.supabase_key)
                print("Supabase client initialized successfully.")
            except Exception as e:
                print(f"Failed to initialize Supabase client: {e}")
                self.client = None

    def log_agent_debate(self, symbol: str, state: Dict[str, Any]):
        """
        Save the entire agent debate round to Supabase.
        """
        if not self.client:
            return
            
        try:
            data = {
                "symbol": symbol,
                "round_number": state.get("round_number", 0),
                "scout_report": str(state.get("scout_report", "")),
                "analyst_report": str(state.get("analyst_report", "")),
                "skeptic_report": str(state.get("skeptic_report", "")),
                "final_decision": state.get("final_decision", {})
            }
            self.client.table("agent_debates").insert(data).execute()
        except Exception as e:
            print(f"Error logging agent debate to Supabase: {e}")

    def log_trade(self, symbol: str, side: str, amount: float, price: float, fee: float):
        """
        Save executed trade details (Buy/Sell) to Supabase.
        """
        if not self.client:
            return
            
        try:
            data = {
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
                "fee": fee
            }
            self.client.table("trade_history").insert(data).execute()
        except Exception as e:
            print(f"Error logging trade to Supabase: {e}")

    def log_balance_update(self, total_balance: float, max_drawdown: float = 0.0):
        """
        Log account balance variation over time.
        """
        if not self.client:
            return
            
        try:
            data = {
                "total_balance": total_balance,
                "max_drawdown": max_drawdown
            }
            self.client.table("balance_history").insert(data).execute()
        except Exception as e:
            print(f"Error logging balance to Supabase: {e}")

    def log_system_error(self, error_level: str, error_message: str, current_capital: float = 0.0):
        """
        Log critical system errors to Supabase.
        """
        if not self.client:
            return
            
        try:
            data = {
                "error_level": error_level,
                "error_message": error_message,
                "current_capital": current_capital,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            self.client.table("system_logs").insert(data).execute()
        except Exception as e:
            print(f"Error logging system error to Supabase: {e}")

    def get_recent_errors(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Query system errors in the last X hours.
        """
        if not self.client:
            return []
            
        try:
            time_threshold = (datetime.datetime.utcnow() - datetime.timedelta(hours=hours)).isoformat()
            response = self.client.table("system_logs").select("*").gte("timestamp", time_threshold).order("timestamp", desc=True).execute()
            return response.data
        except Exception as e:
            print(f"Error fetching recent errors from Supabase: {e}")
            return []

    def sync_config_to_supabase(self, config_path: str = "config.yaml"):
        """
        Read config.yaml and sync parameters (Capital, Goal, Timeframe) to Supabase.
        """
        if not self.client:
            return
            
        try:
            # We assume config_path is relative to the root or absolute.
            # In a real deployed environment, os.path.join with base dir is safer.
            if not os.path.exists(config_path):
                print(f"Config file not found at {config_path}")
                return

            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                
            # Upsert into a configuration table. Assuming a single row with id=1
            data = {
                "id": 1, 
                "capital": config_data.get("capital", 10000),
                "target_goal": config_data.get("target_goal", 30000000000),
                "timeframe_days": config_data.get("timeframe_days", 365)
            }
            
            # Using upsert to update the remote config without duplicating
            self.client.table("app_config").upsert(data).execute()
            print("Successfully synced config.yaml to Supabase 'app_config' table.")
        except Exception as e:
            print(f"Error syncing config to Supabase: {e}")

# For testing locally
if __name__ == "__main__":
    db = DatabaseManager()
    db.sync_config_to_supabase()
