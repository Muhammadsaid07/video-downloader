import os
import logging
from flask import Flask, request
from pytubefix import YouTube
import instaloader
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Env Vars ===
TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 8443))
APP_URL = os.environ["RENDER_EXTERNAL_URL"] + "webhook"

# === Telegram Bot Setup ===
application = Application.builder().token(TOKEN).build()

# === Flask App ===
flask_app = Flask(__name__)

# === Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a YouTube or Instagram video link!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    chat_id = update.effective_chat.id

    # Create a temporary download folder
    DOWNLOAD_DIR = "temp_videos"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    try:
        if "youtube.com" in url or "youtu.be" in url:
            yt = YouTube(url)
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            file_path = stream.download(output_path=DOWNLOAD_DIR)
        elif "instagram.com" in url:
            loader = instaloader.Instaloader(dirname_pattern=DOWNLOAD_DIR, save_metadata=False)
            post = instaloader.Post.from_shortcode(loader.context, url.split("/")[-2])
            loader.download_post(post, target="")
            file_path = next((os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR) if f.endswith(".mp4")), None)
        else:
            await update.message.reply_text("Unsupported link.")
            return

        if file_path and os.path.exists(file_path):
            await context.bot.send_video(chat_id=chat_id, video=open(file_path, 'rb'))
            os.remove(file_path)  # ✅ Delete after sending
        else:
            await update.message.reply_text("Failed to download the video.")

    except Exception as e:
        logger.exception(e)
        await update.message.reply_text(f"Error: {e}")

# === Add Handlers ===
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# === Webhook Endpoint ===
@flask_app.post("/webhook")
def webhook():
    update_data = request.get_json(force=True)
    update = Update.de_json(update_data, application.bot)
    application.create_task(application.process_update(update))
    return "ok"

# === Start Everything ===
if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=PORT)).start()
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=APP_URL,
    )
