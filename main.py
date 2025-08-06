import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
import asyncio

TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")  # Replace or set env var
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-domain.com/webhook")  # Replace

# Set up logging
logging.basicConfig(level=logging.INFO)

# Flask app
app = Flask(__name__)

# Telegram application
bot_app = Application.builder().token(TOKEN).build()

# Flag to check if bot initialized
initialized = False


# === Telegram command handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Send me a YouTube link and I'll download it for you.")


# === Flask route for webhook ===
@app.route('/webhook', methods=["POST"])
async def webhook():
    global initialized
    if not initialized:
        await bot_app.initialize()
        await bot_app.start()
        initialized = True

    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return "ok", 200


# === Flask healthcheck ===
@app.route('/', methods=["GET", "HEAD"])
def index():
    return "Bot is running!", 200


# === Run Flask app ===
if __name__ == '__main__':
    # Set webhook on startup
    async def set_webhook():
        await bot_app.bot.set_webhook(url=WEBHOOK_URL)
        logging.info("✅ Webhook has been set.")

    asyncio.run(set_webhook())

    # Add handlers
    bot_app.add_handler(CommandHandler("start", start))

    # Start Flask app
    app.run(host="0.0.0.0", port=10000)
