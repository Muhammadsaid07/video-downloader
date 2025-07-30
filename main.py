import os
import logging
from pytubefix import YouTube
import instaloader
import shutil
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Logging (optional but useful for debugging)
logging.basicConfig(level=logging.INFO)

# Get your token from environment variable
TOKEN = os.environ["8359982751:AAHvsrsJXoABZe6kyQQoi-lJbEy5pxZ05mY"]

TEMP_DIR = "temp_download"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Please send a YouTube or Instagram link.")

# Handle links
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.message.chat_id

    if not text.startswith("http"):
        await update.message.reply_text("❗️ Please send a valid link.")
        return

    await update.message.reply_text("⏬ Downloading...")

    try:
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
            await update.message.reply_text("❗️ Only YouTube or Instagram links are supported.")
            return

        await context.bot.send_video(chat_id=chat_id, video=open(file_path, 'rb'))

        # Clean up
        os.remove(file_path)
        if "insta_temp" in file_path:
            shutil.rmtree(folder_path, ignore_errors=True)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error:\n{e}")

# Main
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
