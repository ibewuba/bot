import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import requests
import logging

# --- Setup logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get the bot token from Render environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")
MAIN_WALLET_ADDRESS = os.getenv("MAIN_WALLET_ADDRESS")

if not BOT_TOKEN and not MAIN_WALLET_ADDRESS:
    raise ValueError("No BOT_TOKEN found. Please set it in Render Environment Variables.")



# Store states
user_state = {}

# Get token info from Dexscreener
def get_token_info(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    res = requests.get(url).json()

    if "pairs" in res and res["pairs"]:
        pair = res["pairs"][0]
        return {
            "price": pair.get("priceUsd"),
            "market_cap": pair.get("fdv"),
            "liquidity": pair.get("liquidity", {}).get("usd"),
            "dex": pair.get("dexId"),
            "base_token": pair.get("baseToken", {}).get("name"),
            "symbol": pair.get("baseToken", {}).get("symbol")
        }
    else:
        return None

# Handle token address input
async def handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_state.get(user_id) == "awaiting_token":
        token_address = update.message.text.strip()
        info = get_token_info(token_address)

        if info:
            msg = (
                f"💎 *{info['base_token']}* ({info['symbol']})\n"
                f"💰 Price: ${info['price']}\n"
                f"📊 Market Cap: ${info['market_cap']}\n"
                f"💦 Liquidity: ${info['liquidity']}\n"
                f"📍 DEX: {info['dex']}"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")

            # Now show package buttons
            keyboard = [
                [InlineKeyboardButton("2 hours | 0.3 SOL", callback_data="package_2h"),
                 InlineKeyboardButton("4 hours | 0.6 SOL", callback_data="package_4h")],
                [InlineKeyboardButton("8 hours | 1.4 SOL", callback_data="package_8h"),
                 InlineKeyboardButton("12 hours |  2 SOL", callback_data="package_12h")],
                [InlineKeyboardButton("15 hours | 2.4 SOL", callback_data="package_15h"),
                 InlineKeyboardButton("18 hours | 2.8 SOL", callback_data="package_18h")],
                [InlineKeyboardButton("20 hours | 3.1 SOL", callback_data="package_20h"),
                 InlineKeyboardButton("24 hours | 3.5 SOL", callback_data="package_24h")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("📦 Select your promotion package:", reply_markup=reply_markup)

            user_state[user_id] = None  # Reset state
        else:
            await update.message.reply_text("❌ Token not found. Please check the address.")
    else:
        await update.message.reply_text("ℹ️ Please start with /start")

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 Welcome to Solana Official Promotion Bot!\n\n"
        "Your one-step tool for checking tokens🔍 and boosting your project visibility 🚀 \n"
        "With me, you can promote your meme coins and pump.fun coins easily. \n Guarantee your spot with fast-track! no queue.\n"
    )
    await update.message.reply_text(welcome_text)

    # Ask for contract address immediately
    await update.message.reply_text("💳 Please send your coin's contract address:")

    # Set state to expect token
    user_state[update.message.from_user.id] = "awaiting_token"

# Handle package selection
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        
        text=f"✅ You selected: {query.data}\n\nPlease proceed to make payment to this address: 47DJ8qLjivGgD6JrLyFygcjy84wYwfZVbrnESnUfv9P3"
        
        )

# Main runner
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token))
    logger.info("Bot is running... Press CTRL+C to stop.")
    app.run_polling()
