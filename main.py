import os
import logging
import yt_dlp
import uuid
from flask import Flask, request
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio

# Load environment variables
TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://video-downloader-hzcm.onrender.com/webhook")

# Flask app
app = Flask(__name__)

# Telegram bot app
bot_app = Application.builder().token(TOKEN).build()

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Download video using yt_dlp
def download_video(url: str) -> str:
    unique_id = str(uuid.uuid4())[:8]
    output_template = f"video_{unique_id}.%(ext)s"
    ydl_opts = {
        'outtmpl': output_template,
        'format': 'best',
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Send me a YouTube link and I'll download it for you.")

# Handle text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    try:
        await update.message.reply_text("📥 Downloading... please wait.")
        file_path = await asyncio.to_thread(download_video, url)

        with open(file_path, 'rb') as f:
            await update.message.reply_video(InputFile(f))

        os.remove(file_path)

    except Exception as e:
        logging.error(f"Download error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

# Register bot handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot_app.bot)
        asyncio.create_task(bot_app.process_update(update))
    except Exception as e:
        logging.error(f"Webhook error: {e}")
    return "OK"

# Health check
@app.route("/")
def index():
    return "✅ YouTube Downloader Bot is running."

# Set webhook *once*, then run Flask app
async def setup_webhook():
    await bot_app.bot.set_webhook(WEBHOOK_URL)

# Only Flask app runs forever
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    # Start webhook setup in background
    loop = asyncio.get_event_loop()
    loop.create_task(setup_webhook())

    # Run Flask server (non-blocking)
    app.run(host="0.0.0.0", port=port)
