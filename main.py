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

# === Load environment variables ===
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://video-downloader-hzcm.onrender.com/webhook")

# === Configure logging ===
logging.basicConfig(level=logging.INFO)

# === Create Flask app ===
app = Flask(__name__)

# === Create Telegram bot application ===
bot_app = Application.builder().token(TOKEN).build()

# === Flag to avoid reinitializing bot multiple times ===
initialized = False

# === Telegram command handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Send me a YouTube link and I'll download it for you.")

# === Register handlers BEFORE starting the bot ===
bot_app.add_handler(CommandHandler("start", start))

# === Flask route to receive Telegram updates ===
@app.route('/webhook', methods=["POST"])
def webhook():
    global initialized

    async def handle():
        global initialized
        if not initialized:
            await bot_app.initialize()
            await bot_app.start()
            initialized = True

        data = request.get_json(force=True)
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)

    asyncio.run(handle())
    return "ok", 200


# === Optional health check route ===
@app.route('/', methods=["GET", "HEAD"])
def index():
    return "Bot is running!", 200

# === Start the webhook and Flask app ===
if __name__ == '__main__':
    async def set_webhook():
        await bot_app.bot.set_webhook(url=WEBHOOK_URL)
        logging.info("✅ Webhook has been set.")

    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=10000)
