import os
import logging
import tempfile
import asyncio
import threading
from flask import Flask, request, abort
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
from concurrent.futures import ThreadPoolExecutor

# -------------------------
# Configuration / Logging
# -------------------------
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")

# Auto-generate webhook URL for Render
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")  # Render sets this automatically
if RENDER_URL:
    WEBHOOK_URL = f"{RENDER_URL}/webhook"
else:
    WEBHOOK_URL = "https://video-downloader-hzcm.onrender.com/webhook"  # fallback for local/dev

PORT = int(os.environ.get("PORT", 10000))
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 4))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------
# Flask app
# -------------------------
app = Flask(__name__)

# -------------------------
# Telegram Application
# -------------------------
bot_app = Application.builder().token(TOKEN).build()

# Executor for blocking work (yt_dlp, file IO)
blocking_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Bot loop for async handling in background thread
bot_loop = None

# -------------------------
# Blocking helper: yt_dlp download
# -------------------------
def yt_dlp_download(url: str, out_dir: str) -> str:
    """
    Download the best mp4-compatible video with yt_dlp.
    Always merges to H.264 + AAC MP4 so Telegram accepts it.
    Returns absolute path to the downloaded file.
    """
    ydl_opts = {
        "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferredformat": "mp4"
            }
        ]
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    # Force .mp4 extension if needed
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
    await update.message.reply_text("👋 Send me a YouTube link and I'll download it for you.")

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("⚠️ Please send a valid link (http/https).")
        return

    msg = await update.message.reply_text("📥 Download started. This can take a while for big videos.")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = asyncio.get_running_loop()
            logger.info("Downloading from URL: %s", url)
            file_path = await loop.run_in_executor(blocking_executor, yt_dlp_download, url, tmpdir)

            if not os.path.exists(file_path):
                logger.error("Downloaded file not found: %s", file_path)
                await update.message.reply_text("❌ Download failed (file missing).")
                return

            await msg.edit_text("📤 Uploading to Telegram...")

            # Send as video if size < 50MB, else send as document
            file_size = os.path.getsize(file_path)
            with open(file_path, "rb") as f:
                if file_size < 50 * 1024 * 1024:
                    await update.message.reply_video(video=f, caption="✅ Here’s your video!")
                else:
                    await update.message.reply_document(document=f, caption="✅ Here’s your video! (Sent as file)")

            await msg.edit_text("✅ Done — video sent.")

    except Exception as e:
        logger.exception("Download/upload error:")
        try:
            await update.message.reply_text(f"❌ Failed: {e}")
        except Exception:
            logger.exception("Failed to send error message to user.")

# Register handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

# -------------------------
# Background bot runner
# -------------------------
async def _bot_runner():
    await bot_app.initialize()
    await bot_app.bot.set_webhook(WEBHOOK_URL)
    logger.info("Webhook set to %s", WEBHOOK_URL)
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
# Webhook endpoint
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
        logger.exception("Webhook error")
        abort(400)

    return "ok", 200

@app.route("/", methods=["GET", "HEAD"])
def index():
    return "Bot is running!", 200

if __name__ == "__main__":
    ensure_bot_loop_running()
    logger.info("Starting Flask app on port %d", PORT)
    app.run(host="0.0.0.0", port=PORT)
