import os
import logging
from pytubefix import YouTube
import instaloader
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get token from environment variable
TOKEN = os.environ["8359982751:AAHvsrsJXoABZe6kyQQoi-lJbEy5pxZ05mY"]

# Create download folders
YOUTUBE_FOLDER = "downloads/youtube"
INSTAGRAM_FOLDER = "downloads/instagram"
os.makedirs(YOUTUBE_FOLDER, exist_ok=True)
os.makedirs(INSTAGRAM_FOLDER, exist_ok=True)

# YouTube download handler
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    chat_id = update.effective_chat.id

    if "youtube.com" in url or "youtu.be" in url:
        try:
            yt = YouTube(url)
            stream = yt.streams.get_highest_resolution()
            file_path = stream.download(output_path=YOUTUBE_FOLDER)
            await context.bot.send_video(chat_id=chat_id, video=open(file_path, "rb"))
        except Exception as e:
            await update.message.reply_text(f"Failed to download YouTube video: {e}")
    elif "instagram.com" in url:
        try:
            loader = instaloader.Instaloader(dirname_pattern=INSTAGRAM_FOLDER)
            post = instaloader.Post.from_shortcode(loader.context, url.split("/")[-2])
            loader.download_post(post, target="insta_temp")
            for file in os.listdir(INSTAGRAM_FOLDER + "/insta_temp"):
                if file.endswith(".mp4"):
                    with open(os.path.join(INSTAGRAM_FOLDER, "insta_temp", file), "rb") as f:
                        await context.bot.send_video(chat_id=chat_id, video=f)
        except Exception as e:
            await update.message.reply_text(f"Failed to download Instagram video: {e}")
    else:
        await update.message.reply_text("Send a valid YouTube or Instagram link.")

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a YouTube or Instagram video link, and I’ll download it!")

# Main bot app
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video))
    await app.run_polling()

# Entrypoint
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
