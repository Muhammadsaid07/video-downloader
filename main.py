import os
import logging
import tempfile
import asyncio
import threading
from flask import Flask, request, abort
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
from pytubefix import YouTube
from concurrent.futures import ThreadPoolExecutor

# -------------------------
# Config
# -------------------------
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-app-name.onrender.com/webhook")
PORT = int(os.environ.get("PORT", 10000))
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 4))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot_app = Application.builder().token(TOKEN).build()

blocking_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
bot_loop = None

# -------------------------
# Hybrid Downloader
# -------------------------
def download_video_any(url: str, out_dir: str) -> str:
    if "youtube.com" in url or "youtu.be" in url:
        logger.info("Using pytubefix for YouTube link")
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4') \
                           .order_by('resolution').desc().first()
        file_path = stream.download(output_path=out_dir)
        return file_path
    else:
        logger.info("Using yt_dlp for non-YouTube link")
        ydl_opts = {
            "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        if not filename.lower().endswith(".mp4"):
            base = os.path.splitext(filename)[0]
            mp4_path = base + ".mp4"
            if os.path.exists(mp4_path):
                filename = mp4_path
        return filename

# -------------------------
# Telegram Handlers
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a link (YouTube, TikTok, Instagram, etc.) and I'll download it for you.")

async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("⚠️ Please send a valid link (http/https).")
        return
    msg = await update.message.reply_text("📥 Download started. Please wait...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = asyncio.get_running_loop()
            file_path = await loop.run_in_executor(blocking_executor, download_video_any, url, tmpdir)
            if not os.path.exists(file_path):
                await msg.edit_text("❌ Download failed.")
                return
            await msg.edit_text("📤 Uploading to Telegram...")
            with open(file_path, "rb") as f:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=f,
                    caption="✅ Here’s your video!"
                )
            await msg.edit_text("✅ Done — video sent.")
    except Exception as e:
        logger.exception("Error downloading video:")
        await update.message.reply_text("❌ Failed to download or send the video.")

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))

# -------------------------
# Bot Loop & Webhook
# -------------------------
async def _bot_runner():
    await bot_app.initialize()
    await bot_app.bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")
    await asyncio.Future()

def start_background_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_bot_runner())

def ensure_bot_loop_running():
    global bot_loop
    if bot_loop is not None and bot_loop.is_running():
        return bot_loop
    bot_loop = asyncio.new_event_loop()
    t = threading.Thread(target=start_background_loop, args=(bot_loop,), daemon=True)
    t.start()
    logger.info("Started background bot loop thread.")
    return bot_loop

# -------------------------
# Flask Routes
# -------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    if not bot_loop or not bot_loop.is_running():
        ensure_bot_loop_running()
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot_app.bot)
        asyncio.run_coroutine_threadsafe(bot_app.process_update(update), bot_loop)
    except Exception:
        logger.exception("Webhook processing error")
        abort(400)
    return "ok", 200

@app.route("/", methods=["GET", "HEAD"])
def index():
    return "Bot is running!", 200

if __name__ == "__main__":
    ensure_bot_loop_running()
    logger.info(f"Starting Flask app on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
