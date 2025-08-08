import os
import logging
import tempfile
import asyncio
import threading
from flask import Flask, request, abort
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pytubefix import YouTube
from concurrent.futures import ThreadPoolExecutor

# -------------------------
# Configuration / Logging
# -------------------------
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-app.onrender.com/webhook")  # MUST match Render URL exactly
PORT = int(os.environ.get("PORT", 10000))
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 4))
TELEGRAM_FILE_LIMIT = 50 * 1024 * 1024  # 50 MB for normal accounts

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

# Executor for blocking work
blocking_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
bot_loop = None


# -------------------------
# pytubefix downloader
# -------------------------
def pytube_download(url: str, out_dir: str) -> str:
    # Fix Shorts URL format
    if "youtube.com/shorts/" in url:
        url = url.replace("youtube.com/shorts/", "youtube.com/watch?v=")

    yt = YouTube(url)

    # Try progressive first, then fallback to highest resolution
    stream = (yt.streams.filter(progressive=True, file_extension='mp4')
              .order_by('resolution').desc().first()
              or yt.streams.get_highest_resolution())

    if not stream:
        raise Exception("No downloadable streams found.")

    return stream.download(output_path=out_dir)


# -------------------------
# Telegram Handlers
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a YouTube link (video or Shorts) and I'll download it for you.")


async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("⚠️ Please send a valid link starting with http or https.")
        return

    msg = await update.message.reply_text("📥 Downloading video...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = asyncio.get_running_loop()
            logger.info("Downloading YouTube video: %s", url)

            file_path = await loop.run_in_executor(blocking_executor, pytube_download, url, tmpdir)

            if not os.path.exists(file_path):
                logger.error("Downloaded file not found: %s", file_path)
                await msg.edit_text("❌ Download failed — no file found.")
                return

            file_size = os.path.getsize(file_path)
            if file_size > TELEGRAM_FILE_LIMIT:
                await msg.edit_text("⚠️ This video is too large for Telegram (max 50 MB).")
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
        logger.exception("Download error:")
        await msg.edit_text(f"❌ Failed to download: {e}")


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
    except Exception:
        logger.exception("Invalid JSON in incoming webhook")
        abort(400)

    try:
        update = Update.de_json(data, bot_app.bot)
    except Exception:
        logger.exception("Failed to create Update from JSON")
        abort(400)

    try:
        asyncio.run_coroutine_threadsafe(bot_app.process_update(update), bot_loop)
    except Exception:
        logger.exception("Failed to schedule process_update")
        abort(500)

    return "ok", 200


@app.route("/", methods=["GET", "HEAD"])
def index():
    return "Bot is running!", 200


if __name__ == "__main__":
    ensure_bot_loop_running()
    logger.info("Starting Flask app on port %d", PORT)
    app.run(host="0.0.0.0", port=PORT)
