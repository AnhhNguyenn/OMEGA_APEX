import os
import uuid
import datetime
import asyncio
from typing import Dict, Any, Callable, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
import yaml
from config.logger_setup import setup_logger

logger = setup_logger("telegram_bot")
load_dotenv()

def load_config():
    try:
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f)
    except:
        return {}

config_data = load_config()

# Global state for simplicity in this architecture
class BotState:
    mode: str = "SEMI_AUTO" # "SEMI_AUTO" or "FULL_AUTO"
    risk_strategy: str = config_data.get("risk_strategy", "SAFE").upper() # "SAFE" or "AGGRESSIVE"
    pending_trades: Dict[str, Any] = {}
    trade_executor_callback: Optional[Callable] = None

class ApexNotifier:
    """
    APEX NOTIFIER: Interactive Telegram Agent using python-telegram-bot (v20+).
    Supports 2-way communication, Semi-Auto/Full-Auto modes, and inline approval.
    """
    def __init__(self):
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        
        self.enabled = bool(self.bot_token and self.chat_id)
        if not self.enabled:
            logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not provided. Telegram bot disabled.")
            self.app = None
            return
            
        self.app = ApplicationBuilder().token(self.bot_token).build()
        self._register_handlers()
        
    def _register_handlers(self):
        if not self.app:
            return
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("semi_auto", self.cmd_mode_semi))
        self.app.add_handler(CommandHandler("full_auto", self.cmd_mode_full))
        self.app.add_handler(CommandHandler("mode_safe", self.cmd_mode_safe))
        self.app.add_handler(CommandHandler("mode_aggressive", self.cmd_mode_aggressive))
        self.app.add_handler(CallbackQueryHandler(self.handle_trade_callback, pattern="^trade_"))

    # --- COMMAND HANDLERS ---
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🚀 *OMEGA APEX SYSTEM INITIALIZED*\n\n"
            "Welcome, Commander. System is online.\n\n"
            "Commands:\n"
            "/status - Check current system status\n"
            "/semi_auto - Require approval before executing trades (Default)\n"
            "/full_auto - Execute trades autonomously without asking\n"
            "/mode_safe - Strict Risk Management (High confidence only)\n"
            "/mode_aggressive - Maximize Growth (Higher risk, volatile plays)\n",
            parse_mode="Markdown"
        )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        mode_str = "🟢 FULL AUTO" if BotState.mode == "FULL_AUTO" else "🟡 SEMI AUTO"
        risk_str = "🛡️ SAFE" if BotState.risk_strategy == "SAFE" else "🔥 AGGRESSIVE"
        await update.message.reply_text(
            f"📊 *System Status*\n\n"
            f"**Execution Mode**: {mode_str}\n"
            f"**Risk Strategy**: {risk_str}\n"
            f"**Pending Approvals**: {len(BotState.pending_trades)}\n",
            parse_mode="Markdown"
        )

    async def cmd_mode_semi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        BotState.mode = "SEMI_AUTO"
        await update.message.reply_text("🛡️ Mode switched to *SEMI_AUTO*. All trades will require your manual approval prior to execution.", parse_mode="Markdown")

    async def cmd_mode_full(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        BotState.mode = "FULL_AUTO"
        await update.message.reply_text("⚠️ Mode switched to *FULL_AUTO*. The AI will now execute trades autonomously. Please monitor logs closely.", parse_mode="Markdown")

    async def cmd_mode_safe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        BotState.risk_strategy = "SAFE"
        await update.message.reply_text("🛡️ Risk Strategy: *SAFE*. Circuit breakers tightened, requiring >90% AI confidence to trade.", parse_mode="Markdown")

    async def cmd_mode_aggressive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        BotState.risk_strategy = "AGGRESSIVE"
        await update.message.reply_text("🔥 Risk Strategy: *AGGRESSIVE*. Circuit breakers loosened, trading on >70% confidence. Target: Maximum Alpha.", parse_mode="Markdown")


    # --- CALLBACK HANDLERS ---
    
    async def handle_trade_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        # pattern: trade_<approve|reject>_<trade_id>
        parts = str(query.data).split("_", 2)
        if len(parts) < 3:
            return
        _, action, trade_id = parts
        
        if trade_id not in BotState.pending_trades:
            await query.edit_message_text(text=f"{query.message.text}\n\n❌ *This trade has expired or already been processed.*", parse_mode="Markdown")
            return
            
        trade_data = BotState.pending_trades.pop(str(trade_id), {})
        
        if action == "approve":
            await query.edit_message_text(text=f"{query.message.text}\n\n✅ *TRADE APPROVED*. Executing now...", parse_mode="Markdown")
            if BotState.trade_executor_callback:
                # Trigger the execution asynchronously
                asyncio.create_task(self._safe_execute(trade_data))
        else:
            await query.edit_message_text(text=f"{query.message.text}\n\n🚫 *TRADE REJECTED*. Cancelled by user.", parse_mode="Markdown")

    async def _safe_execute(self, trade_data):
        try:
            # We assume trade_executor_callback is an async function or we wrap it
            if asyncio.iscoroutinefunction(BotState.trade_executor_callback):
                await BotState.trade_executor_callback(trade_data) # type: ignore
            else:
                # Run sync in thread pool to not block loop
                loop = asyncio.get_event_loop()
                def run_sync():
                    if BotState.trade_executor_callback:
                        BotState.trade_executor_callback(trade_data)
                await loop.run_in_executor(None, run_sync)
        except Exception as e:
            logger.error(f"Error executing approved trade: {e}", exc_info=True)
            self.send_sync_message(f"❌ *EXECUTION FAILED* for {trade_data['symbol']}: {e}")

    # --- OUTBOUND MESSAGES (SYNC & ASYNC) ---
    
    def send_sync_message(self, text: str):
        """Helper to send messages from synchronous contexts."""
        if not self.enabled:
            return
            
        if self.app and hasattr(self.app, "bot") and self.app.bot:
            try:
                # Create a task in the running loop
                loop = asyncio.get_event_loop()
                loop.create_task(self.app.bot.send_message(chat_id=self.chat_id, text=text, parse_mode="Markdown"))
            except RuntimeError:
                # No running loop, just let it fail or use HTTP directly.
                logger.warning("Could not send sync message: No event loop.")

    def request_trade_approval(self, symbol: str, side: str, amount: float, confidence: int, reason: str, price: float = 0.0):
        """
        Sends an inline keyboard requesting permission to trade (SEMI-AUTO).
        """
        if not self.enabled:
            return
            
        trade_id = str(uuid.uuid4())[:8]
        BotState.pending_trades[trade_id] = {
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": price,
            "confidence": confidence,
            "reason": reason
        }
        
        icon = "🟢" if side.upper() == "BUY" else "🔴"
        message = (
            f"*{icon} PENDING TRADE APPROVAL*\n\n"
            f"**Symbol**: `{symbol}`\n"
            f"**Action**: `{side.upper()}`\n"
            f"**Size**: `{amount}`\n"
            f"**Current Price**: `${price}`\n"
            f"**AI Confidence**: `{confidence}%`\n\n"
            f"📝 **Judge's Reasoning**:\n_{reason}_\n\n"
            f"Proceed with execution?"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ APPROVE", callback_data=f"trade_approve_{trade_id}"),
                InlineKeyboardButton("🚫 REJECT", callback_data=f"trade_reject_{trade_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            loop = asyncio.get_event_loop()
            if self.app and hasattr(self.app, "bot") and self.app.bot:
                loop.create_task(self.app.bot.send_message(chat_id=self.chat_id, text=message, reply_markup=reply_markup, parse_mode="Markdown"))
        except Exception as e:
            logger.error(f"Failed to send trade approval request: {e}")

    def notify_trade_executed(self, symbol: str, side: str, amount: float, confidence: int, reason: str):
        """
        Alert when a trade is autonomously executed (FULL-AUTO).
        """
        icon = "🟢" if side.upper() == "BUY" else "🔴"
        message = (
            f"*{icon} TRADE EXECUTED (AUTOPILOT)*\n\n"
            f"**Symbol**: `{symbol}`\n"
            f"**Action**: `{side.upper()}`\n"
            f"**Size**: `{amount}`\n"
            f"**AI Confidence**: `{confidence}%`\n\n"
            f"📝 **Judge's Reasoning**:\n_{reason}_"
        )
        self.send_sync_message(message)

    def notify_circuit_breaker(self, reason: str):
        message = (
            f"🚨 *CIRCUIT BREAKER TRIGGERED* 🚨\n\n"
            f"**Reason**: {reason}\n"
            f"Trading has been halted immediately to protect capital!"
        )
        self.send_sync_message(message)

    def notify_milestone(self, milestone_name: str, new_balance: float):
        message = (
            f"🏆 *NEW MILESTONE REACHED* 🏆\n\n"
            f"**{milestone_name}**\n"
            f"**Current Capital**: `${new_balance:,.2f}`\n\n"
            f"The march to $30B continues..."
        )
        self.send_sync_message(message)
        
    def notify_error(self, error_code: str, error_message: str):
        message = (
            f"❌ *SYSTEM ERROR [{error_code}]* ❌\n\n"
            f"**Details**:\n`{error_message}`\n\n"
            f"Please check the logs immediately!"
        )
        self.send_sync_message(message)

    def send_hourly_summary(self, approved_trades: int, error_count: int):
        icon = "✅" if error_count == 0 else "⚠️"
        message = (
            f"⏱️ *HOURLY SYSTEM SUMMARY* {icon}\n\n"
            f"**Approved Trades**: {approved_trades}\n"
            f"**Errors Encountered**: {error_count}\n"
            f"**Status**: {'Optimal' if error_count == 0 else 'Needs Attention'}"
        )
        self.send_sync_message(message)

    def run_polling(self):
        """Start the telegram bot loop. This should run alongside the main app."""
        if self.enabled and self.app:
            logger.info("Starting Telegram Bot Polling...")
            self.app.run_polling()
