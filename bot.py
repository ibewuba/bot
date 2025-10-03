import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
# import requests
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


# Store states (A simple in-memory dictionary)
user_state = {}

# Define package details for cleaner logic and better display
PACKAGE_DETAILS = {
    "package_2h": "2 hours | 0.3 SOL",
    "package_4h": "4 hours | 0.6 SOL",
    "package_8h": "8 hours | 1.4 SOL",
    "package_12h": "12 hours | 2 SOL",
    "package_15h": "15 hours | 2.4 SOL",
    "package_18h": "18 hours | 2.8 SOL",
    "package_20h": "20 hours | 3.1 SOL",
    "package_24h": "24 hours | 3.5 SOL",
}

# --- Dexscreener API Function ---
def get_token_info(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    res = requests.get(url).json()

    if "pairs" in res and res["pairs"]:
        pair = res["pairs"][0]
        # Format the numbers for readability
        price = f"${float(pair.get('priceUsd', 0)):,.8f}" if pair.get('priceUsd') else "N/A"
        market_cap = f"${int(pair.get('fdv', 0)):,}" if pair.get('fdv') else "N/A"
        liquidity = f"${int(pair.get('liquidity', {}).get('usd', 0)):,}" if pair.get('liquidity', {}).get('usd') else "N/A"
        
        return {
            "price": price,
            "market_cap": market_cap,
            "liquidity": liquidity,
            "dex": pair.get("dexId"),
            "base_token": pair.get("baseToken", {}).get("name"),
            "symbol": pair.get("baseToken", {}).get("symbol")
        }
    else:
        return None

# --- Command Handlers ---

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

# Handle token address input (Message Handler)
async def handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_state.get(user_id) == "awaiting_token":
        token_address = update.message.text.strip()
        
        # Simple validation to prevent unnecessary API calls on short text
        if not (30 < len(token_address) < 60):
             await update.message.reply_text("❌ That doesn't look like a valid Solana contract address (usually 32-44 characters). Please try again.")
             return

        info = get_token_info(token_address)

        if info:
            msg = (
                f"💎 *{info['base_token']}* ({info['symbol']})\n"
                f"💰 Price: {info['price']}\n"
                f"📊 Market Cap: {info['market_cap']}\n"
                f"💦 Liquidity: {info['liquidity']}\n"
                f"📍 DEX: {info['dex']}"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")

            # Now show package buttons
            keyboard = [
                [InlineKeyboardButton(PACKAGE_DETAILS["package_2h"], callback_data="package_2h"),
                 InlineKeyboardButton(PACKAGE_DETAILS["package_4h"], callback_data="package_4h")],
                [InlineKeyboardButton(PACKAGE_DETAILS["package_8h"], callback_data="package_8h"),
                 InlineKeyboardButton(PACKAGE_DETAILS["package_12h"], callback_data="package_12h")],
                [InlineKeyboardButton(PACKAGE_DETAILS["package_15h"], callback_data="package_15h"),
                 InlineKeyboardButton(PACKAGE_DETAILS["package_18h"], callback_data="package_18h")],
                [InlineKeyboardButton(PACKAGE_DETAILS["package_20h"], callback_data="package_20h"),
                 InlineKeyboardButton(PACKAGE_DETAILS["package_24h"], callback_data="package_24h")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # This is the message that will be edited later
            await update.message.reply_text("📦 Select your promotion package:", reply_markup=reply_markup)

            user_state[user_id] = None  # Reset state
        else:
            await update.message.reply_text("❌ Token not found on supported DEXs. Please check the address.")
    else:
        # Acknowledge message if state is not set, prompting user to start
        await update.message.reply_text("ℹ️ Please start with /start to submit a token address.")

# Handle package selection (Callback Handler)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Acknowledge the button press
    
    selected_package_key = query.data # e.g., "package_2h"
    selected_package_text = PACKAGE_DETAILS.get(selected_package_key, "an unknown package")

    # Create an inline button for easy copying of the address
    # Telegram will often allow long text buttons to be copied easily
    payment_keyboard = [
        [InlineKeyboardButton("🔗 Tap Above To Copy Address", url=f"https://t.me/share/url?url={MAIN_WALLET_ADDRESS}")]
    ]
    reply_markup = InlineKeyboardMarkup(payment_keyboard)
    
    # EDIT THE MESSAGE TEXT, replacing the package buttons with payment info
    await query.edit_message_text(
        text=f"✅ You selected: *{selected_package_text}*\n\n"
             f"Please proceed to make payment to the following address. \n"
             f"*Send the exact SOL amount indicated on the button.*\n\n"
             f"💳 **Payment Address:**\n`{MAIN_WALLET_ADDRESS}`\n\n"
             f"⏳ Your promotion will begin shortly after the transaction is confirmed.",
        parse_mode="Markdown", # Enable rich text formatting
        reply_markup=reply_markup # Attach the new inline keyboard
    )

# --- Main Runner ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    # This handler processes any text that is NOT a command
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token))
    
    logger.info("Bot is running... Press CTRL+C to stop.")
    app.run_polling()
