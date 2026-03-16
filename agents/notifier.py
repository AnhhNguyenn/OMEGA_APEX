import os
import requests
from dotenv import load_dotenv

load_dotenv()

class ApexNotifier:
    """
    APEX NOTIFIER: Telegram Agent for Real-time Alerts
    """
    def __init__(self):
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        
        if not self.bot_token or not self.chat_id:
            print("WARNING: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not provided. Notifier is disabled.")
            self.enabled = False
        else:
            self.enabled = True
            self.base_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_message(self, text: str):
        """
        Send a generic text message to the Telegram Chat.
        """
        if not self.enabled:
            return
            
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            requests.post(self.base_url, json=payload, timeout=5)
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")

    def notify_trade_approved(self, symbol: str, side: str, amount: float, confidence: int):
        """
        Alert when a new trade is approved by the Judge and Executed.
        """
        icon = "🟢" if side.upper() == "BUY" else "🔴"
        message = (
            f"*{icon} OMEGA APEX TRADE EXECUTED*\n\n"
            f"**Symbol**: `{symbol}`\n"
            f"**Action**: `{side.upper()}`\n"
            f"**Size**: `{amount}`\n"
            f"**AI Confidence**: `{confidence}%`\n"
        )
        self.send_message(message)

    def notify_circuit_breaker(self, reason: str):
        """
        Alert when the system halts trading to protect capital.
        """
        message = (
            f"🚨 *CIRCUIT BREAKER TRIGGERED* 🚨\n\n"
            f"**Reason**: {reason}\n"
            f"Trading has been halted immediately to protect capital!"
        )
        self.send_message(message)

    def notify_milestone(self, milestone_name: str, new_balance: float):
        """
        Celebrate when the account reaches a milestone (e.g. Doubled account).
        """
        message = (
            f"🏆 *NEW MILESTONE REACHED* 🏆\n\n"
            f"**{milestone_name}**\n"
            f"**Current Capital**: `${new_balance:,.2f}`\n\n"
            f"The march to $30B continues..."
        )
        self.send_message(message)

    def notify_error(self, error_code: str, error_message: str):
        """
        Alert when a critical system error or API timeout occurs.
        """
        message = (
            f"❌ *SYSTEM ERROR [{error_code}]* ❌\n\n"
            f"**Details**:\n`{error_message}`\n\n"
            f"Please check the logs immediately!"
        )
        self.send_message(message)

    def send_hourly_summary(self, approved_trades: int, error_count: int):
        """
        Send a routine hourly report summarizing activities.
        """
        icon = "✅" if error_count == 0 else "⚠️"
        message = (
            f"⏱️ *HOURLY SYSTEM SUMMARY* {icon}\n\n"
            f"**Approved Trades**: {approved_trades}\n"
            f"**Errors Encountered**: {error_count}\n"
            f"**Status**: {'Optimal' if error_count == 0 else 'Needs Attention'}"
        )
        self.send_message(message)
        
# Local testing
if __name__ == "__main__":
    notifier = ApexNotifier()
    notifier.send_message("Test message from APEX NOTIFIER.")
