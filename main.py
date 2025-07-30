import os
import logging
import asyncio
from pytubefix import YouTube
import instaloader
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot token from environment variable
TOKEN = os.environ.get("BOT_TOKEN")
APP_URL = os.environ.get("APP_URL")

if not TOKEN or not APP_URL:
    raise RuntimeError("❌ BOT_TOKEN or APP_URL is missing.")
  # e.g. https://your-app-name.onrender.com

# Create folders
YOUTUBE_FOLDER = "downloads/youtube"
INSTAGRAM_FOLDER = "downloads/instagram"
os.makedirs(YOUTUBE_FOLDER, exist_ok=True)
os.makedirs(INSTAGRAM_FOLDER, exist_ok=True)

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a YouTube or Instagram video link!")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    chat_id = update.effective_chat.id

    if "youtube.com" in url or "youtu.be" in url:
        try:
            yt = YouTube(url)
            stream = yt.streams.get_highest_resolution()
            file_path = stream.download(output_path=YOUTUBE_FOLDER)
            await context.bot.send_video(chat_id=chat_id, video=open(file_path, "rb"))
        except Exception as e:
            await update.message.reply_text(f"❌ YouTube error: {e}")

    elif "instagram.com" in url:
        try:
            loader = instaloader.Instaloader(dirname_pattern=INSTAGRAM_FOLDER)
            shortcode = [seg for seg in url.split("/") if seg][-1]
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            loader.download_post(post, target="insta_temp")
            for file in os.listdir(os.path.join(INSTAGRAM_FOLDER, "insta_temp")):
                if file.endswith(".mp4"):
                    with open(os.path.join(INSTAGRAM_FOLDER, "insta_temp", file), "rb") as f:
                        await context.bot.send_video(chat_id=chat_id, video=f)
        except Exception as e:
            await update.message.reply_text(f"❌ Instagram error: {e}")
    else:
        await update.message.reply_text("⚠️ Please send a valid YouTube or Instagram link.")

# Flask app for webhook
flask_app = Flask(__name__)
bot_app = None

@flask_app.route("/", methods=["GET"])
def home():
    return "Bot is running!"

@flask_app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    await bot_app.process_update(update)
    return "ok"

async def main():
    global bot_app
    bot_app = Application.builder().token(TOKEN).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video))

    # Set webhook URL
    await bot_app.bot.set_webhook(f"{APP_URL}/{TOKEN}")

if __name__ == "__main__":
    asyncio.run(main())
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
