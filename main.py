import os
import uuid
import yt_dlp
from flask import Flask, request
from telegram import Bot

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")
bot = Bot(token=BOT_TOKEN)

app = Flask(__name__)
DOWNLOAD_DIR = "./downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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

@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    data = request.get_json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text")

    if not chat_id or not text:
        return "Invalid", 200

    if "youtu" not in text and "instagram" not in text:
        bot.send_message(chat_id=chat_id, text="❌ Send a YouTube or Instagram link.")
        return "OK", 200

    bot.send_message(chat_id=chat_id, text="⏳ Downloading...")

    try:
        file_path = download_video(text)
        if file_path:
            with open(file_path, "rb") as vid:
                bot.send_video(chat_id=chat_id, video=vid)
            os.remove(file_path)
        else:
            bot.send_message(chat_id=chat_id, text="⚠️ Download failed.")
    except Exception as e:
        bot.send_message(chat_id=chat_id, text=f"❌ Error: {e}")

    return "OK", 200

@app.route("/")
def index():
    return "✅ Bot is live!"
