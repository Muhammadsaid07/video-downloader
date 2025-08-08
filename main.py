import os
import logging
import tempfile
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Load env vars
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://video-downloader-hzcm.onrender.com/webhook")

# Logging
logging.basicConfig(level=logging.INFO)

# Flask app
app = Flask(__name__)

# Bot app
bot_app = Application.builder().token(TOKEN).build()

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a YouTube link and I'll download it for you.")

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("⚠️ Please send a valid YouTube link.")
        return

    await update.message.reply_text("📥 Downloading your video... please wait.")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
                'format': 'mp4/best',
                'quiet': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)

            with open(file_path, 'rb') as f:
                await update.message.reply_video(video=f, caption="✅ Here’s your video!")
    except Exception as e:
        logging.error(f"Download error: {e}")
        await update.message.reply_text("❌ Failed to download video.")

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

# Webhook route
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)
    asyncio.run(bot_app.process_update(update))
    return "ok", 200

# Health check
@app.route("/", methods=["GET", "HEAD"])
def index():
    return "Bot is running!", 200

if __name__ == "__main__":
    async def run():
        await bot_app.initialize()
        await bot_app.bot.set_webhook(url=WEBHOOK_URL)
        logging.info("✅ Webhook set")
    asyncio.run(run())

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
