import os
import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters
import yt_dlp

# Environment variables
TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

# Logging
logging.basicConfig(level=logging.INFO)

# Telegram Bot Setup
bot = Bot(token=TOKEN)
app = Flask(__name__)

# Set up dispatcher
dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)

# /start handler
def start(update, context):
    update.message.reply_text("👋 Send me a YouTube or Instagram link and I'll download it!")

# Video handler
def handle_video(update, context):
    url = update.message.text
    chat_id = update.effective_chat.id
    filename = f"video_{chat_id}.mp4"
    try:
        ydl_opts = {
            'outtmpl': filename,
            'format': 'best',
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        with open(filename, "rb") as video:
            bot.send_video(chat_id=chat_id, video=video)
    except Exception as e:
        bot.send_message(chat_id=chat_id, text=f"❌ Error: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

# Add handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video))

# Flask routes
@app.route("/", methods=["GET"])
def home():
    return "Bot is running."

@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

# ✅ THIS PART IS ESSENTIAL FOR RENDER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
