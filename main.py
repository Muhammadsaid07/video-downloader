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

# Telegram bot application
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

# Handle messages (YouTube URLs)
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

# Register handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Global flag to ensure initialization only once
initialized = False

# Webhook route
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot_app.bot)

        # Create a new event loop for Flask context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def handle_update():
            global initialized
            if not initialized:
                await bot_app.initialize()
                initialized = True
            await bot_app.process_update(update)

        loop.run_until_complete(handle_update())
        loop.close()

    except Exception as e:
        logging.error(f"Webhook error: {e}")
    return "OK"

# Health check route
@app.route("/")
def index():
    return "✅ YouTube Downloader Bot is running."

# Initialize webhook and run server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    async def setup():
        await bot_app.initialize()
        await bot_app.bot.set_webhook(WEBHOOK_URL)
        logging.info("✅ Webhook has been set.")

    asyncio.run(setup())
    app.run(host="0.0.0.0", port=port)
