import os
import logging
import yt_dlp
from flask import Flask, request
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio

# Load bot token and webhook URL from environment
TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://your-app-name.onrender.com/webhook")  # Replace if needed

# Set up Flask
app = Flask(__name__)

# Set up Telegram bot application
bot_app = Application.builder().token(TOKEN).build()

# Logging config
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Function to download video using yt_dlp
def download_video(url: str) -> str:
    ydl_opts = {
        'outtmpl': 'video.%(ext)s',
        'format': 'best',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Send me a YouTube link and I'll download it for you.")

# Handler for any message (expects YouTube link)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    try:
        await update.message.reply_text("📥 Downloading... please wait.")
        file_path = download_video(url)

        with open(file_path, 'rb') as f:
            await update.message.reply_video(InputFile(f))

        os.remove(file_path)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# Add command and message handlers to the bot
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook route for Telegram
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    print("📬 Received Telegram update:", data)
    update = Update.de_json(data, bot_app.bot)
    asyncio.get_event_loop().create_task(bot_app.process_update(update))
    return "OK"

# Health check route
@app.route("/")
def index():
    return "✅ YouTube Downloader Bot is running."

# Run Flask server and set webhook
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    # Set webhook before starting server
    asyncio.run(bot_app.bot.set_webhook(WEBHOOK_URL))

    # Start Flask
    app.run(host="0.0.0.0", port=port)
