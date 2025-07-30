import os
import shutil
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from pytubefix import YouTube
import instaloader
import asyncio

TOKEN = os.environ["8359982751:AAHvsrsJXoABZe6kyQQoi-lJbEy5pxZ05mY"]
TEMP_DIR = "temp_download"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

app = Flask(__name__)
bot_app = None  # placeholder for telegram Application

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Please send a YouTube or Instagram link.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if not text.startswith("http"):
        await update.message.reply_text("❗️ Please send a valid URL.")
        return

    await update.message.reply_text("⏬ Downloading...")

    try:
        file_path = None

        if "youtube.com" in text or "youtu.be" in text:
            yt = YouTube(text)
            stream = yt.streams.get_highest_resolution()
            file_path = stream.download(output_path=TEMP_DIR)

        elif "instagram.com" in text:
            loader = instaloader.Instaloader(dirname_pattern=TEMP_DIR, save_metadata=False, download_comments=False)
            shortcode = text.split("/")[-2]
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            loader.download_post(post, target="insta_temp")
            folder_path = os.path.join(TEMP_DIR, "insta_temp")
            files = [f for f in os.listdir(folder_path) if f.endswith((".mp4", ".jpg"))]
            if files:
                file_path = os.path.join(folder_path, files[0])
            else:
                await update.message.reply_text("⚠️ No video found.")
                return

        else:
            await update.message.reply_text("❗️ Only Youtube or Instagram links are accepted.")
            return

        with open(file_path, 'rb') as f:
            await update.message.reply_video(video=f)

        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
        if "insta_temp" in file_path:
            shutil.rmtree(os.path.join(TEMP_DIR, "insta_temp"), ignore_errors=True)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error:\n{e}")

# --- Flask routes ---

@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put(update)
    return "ok"

@app.route("/")
def index():
    return "Bot is running."

# --- Main entry point ---

async def run_bot():
    global bot_app
    bot_app = (
        ApplicationBuilder()
        .token(TOKEN)
        .concurrent_updates(True)
        .build()
    )

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Webhook URL
    webhook_url = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/{TOKEN}"
    await bot_app.bot.set_webhook(url=webhook_url)

    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()  # needed for update_queue to work

if __name__ == "__main__":
    asyncio.run(run_bot())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
