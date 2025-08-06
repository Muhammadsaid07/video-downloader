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
    return "OK"import os
import uuid
import yt_dlp
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram.ext import filters

# --- Config ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")
DOWNLOAD_DIR = "./downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- Flask App ---
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
application = Application.builder().token(BOT_TOKEN).build()

# --- Download Logic ---
def download_video(url):
    uid = str(uuid.uuid4())
    output = os.path.join(DOWNLOAD_DIR, uid + ".%(ext)s")
    options = {
        "outtmpl": output,
        "format": "bestvideo+bestaudio/best",
        "quiet": True,
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(uid):
            return os.path.join(DOWNLOAD_DIR, f)
    return None

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a YouTube or Instagram link to download!")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    if "youtu" not in text and "instagram" not in text:
        await context.bot.send_message(chat_id=chat_id, text="❌ Send a YouTube or Instagram link.")
        return

    await context.bot.send_message(chat_id=chat_id, text="⏳ Downloading...")

    try:
        file_path = download_video(text)
        if file_path:
            with open(file_path, "rb") as vid:
                await context.bot.send_video(chat_id=chat_id, video=vid)
            os.remove(file_path)
        else:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Download failed.")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {e}")

# --- Add Handlers ---
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video))

# --- Webhook route ---
@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return "OK"

@app.route("/")
def index():
    return "✅ Bot is live!"

# --- Start Flask ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# ✅ THIS PART IS ESSENTIAL FOR RENDER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
