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
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://video-downloader-hzcm.onrender.com/webhook")
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

# We'll run the Application on its own asyncio loop running in a background thread.
bot_loop = None  # will hold the asyncio loop instance


# -------------------------
# Blocking helper: download with yt_dlp (runs in threadpool)
# -------------------------
def yt_dlp_download(url: str, out_dir: str) -> str:
    """
    Synchronously download the best mp4-compatible file using yt_dlp.
    Returns absolute path to the downloaded file.
    """
    ydl_opts = {
        # Template ensures safe filenames
        "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
        # Prefer mp4/m4a so Telegram accepts it, but fallback to best available
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        # Avoid overwriting
        "nocheckcertificate": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    return filename


# -------------------------
# Telegram Handlers
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a YouTube link and I'll download it for you.")


async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Async handler that schedules the blocking yt_dlp download into the executor.
    Keeps the file present while uploading to Telegram.
    """
    url = (update.message.text or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("⚠️ Please send a valid link (http/https).")
        return

    msg = await update.message.reply_text("📥 Download started. This can take a while for big videos.")
    try:
        # Use a temporary directory so file is auto-removed afterwards
        with tempfile.TemporaryDirectory() as tmpdir:
            # Schedule blocking download in threadpool
            loop = asyncio.get_running_loop()
            logger.info("Scheduling yt_dlp download for URL: %s", url)
            file_path = await loop.run_in_executor(blocking_executor, yt_dlp_download, url, tmpdir)

            # Ensure file exists
            if not os.path.exists(file_path):
                logger.error("Downloaded file not found: %s", file_path)
                await update.message.reply_text("❌ Download failed (file missing).")
                return

            # Inform user about upload beginning
            await msg.edit_text("📤 Uploading to Telegram...")

            # Send video (keep file open so Telegram library can stream it)
            # Use context.bot.send_video to ensure upload happens asynchronously
            with open(file_path, "rb") as f:
                # If file is larger than allowed by Telegram you'll still get an error — consider using file size checks.
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=f,
                    caption="✅ Here’s your video!"
                )

            await msg.edit_text("✅ Done — video sent. Temporary file removed.")
    except Exception as e:
        logger.exception("Download/upload error:")
        try:
            await update.message.reply_text("❌ Failed to download or send the video.")
        except Exception:
            logger.exception("Failed to send error message to user.")


# Register handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))


# -------------------------
# Background bot runner
# -------------------------
async def _bot_runner():
    """
    Coroutine run inside a dedicated loop on a background thread.
    Initializes the Application and sets webhook.
    Keeps running forever so we can process incoming updates via process_update().
    """
    # Initialize the application (register handlers, etc.)
    await bot_app.initialize()

    # Set webhook
    # make sure to set drop_pending_updates=False if you don't want to drop updates that arrived between restarts
    await bot_app.bot.set_webhook(WEBHOOK_URL)
    logger.info("Webhook set to %s", WEBHOOK_URL)

    # Note: we don't call bot_app.start_polling() because we use process_update via webhook.
    # Keep the loop alive indefinitely
    logger.info("Bot runner started; background loop is running.")
    await asyncio.Future()  # run forever


def start_background_loop(loop: asyncio.AbstractEventLoop):
    """
    Start the bot runner coroutine on the provided loop.
    This will be used by the background thread.
    """
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_bot_runner())


def ensure_bot_loop_running():
    global bot_loop
    if bot_loop is not None and bot_loop.is_running():
        return bot_loop

    # Create a new loop and run it in a background thread
    bot_loop = asyncio.new_event_loop()
    t = threading.Thread(target=start_background_loop, args=(bot_loop,), daemon=True)
    t.start()
    logger.info("Started background bot loop thread.")
    return bot_loop


# -------------------------
# Webhook endpoint (Flask)
# -------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Flask webhook route. Converts incoming JSON to Update and schedules
    bot_app.process_update(update) on the bot asyncio loop using
    asyncio.run_coroutine_threadsafe.
    """
    if not bot_loop or not bot_loop.is_running():
        # Try to start the loop if it's not running
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
        # Schedule processing of the update on the bot loop
        future = asyncio.run_coroutine_threadsafe(bot_app.process_update(update), bot_loop)
        # Optionally, we could wait for result or set a timeout, but it's fine to fire-and-forget here:
        # future.result(timeout=10)
    except Exception:
        logger.exception("Failed to schedule process_update on bot loop")
        abort(500)

    return "ok", 200


# Healthcheck
@app.route("/", methods=["GET", "HEAD"])
def index():
    return "Bot is running!", 200


# -------------------------
# Entry point
# -------------------------
if __name__ == "__main__":
    # Ensure the background loop is started before Flask receives requests
    ensure_bot_loop_running()
    logger.info("Starting Flask app on port %d", PORT)
    # On Render, the default WSGI server will run this file; app.run is fine for local testing.
    app.run(host="0.0.0.0", port=PORT)
