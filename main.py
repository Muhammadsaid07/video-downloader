import os
import logging
from pytubefix import YouTube
import instaloader
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Setup
TOKEN = "8359982751:AAHvsrsJXoABZe6kyQQoi-lJbEy5pxZ05mY"  # Replace with your actual token
DOWNLOAD_FOLDER = "/tmp"  # Safe for Render

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Logging (helps debug)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send me a YouTube or Instagram link to download:")

# Handle video links
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if not text.startswith("http"):
        await update.message.reply_text("❌ Please enter a valid URL.")
        return

    try:
        if "youtube.com" in text or "youtu.be" in text:
            yt = YouTube(text)
            stream = yt.streams.get_highest_resolution()
            file_path = stream.download(output_path=DOWNLOAD_FOLDER)

            with open(file_path, 'rb') as video:
                await context.bot.send_video(chat_id=chat_id, video=video)

            os.remove(file_path)

        elif "instagram.com" in text:
            loader = instaloader.Instaloader(dirname_pattern=DOWNLOAD_FOLDER)
            shortcode = text.strip("/").split("/")[-1] or text.strip("/").split("/")[-2]
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            loader.download_post(post, target="insta_temp")

            folder = os.path.join(DOWNLOAD_FOLDER, "insta_temp")
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if filename.endswith(".mp4"):
                    with open(filepath, 'rb') as f:
                        await context.bot.send_video(chat_id=chat_id, video=f)
                elif filename.endswith(".jpg"):
                    with open(filepath, 'rb') as f:
                        await context.bot.send_photo(chat_id=chat_id, photo=f)

            for f in os.listdir(folder):
                os.remove(os.path.join(folder, f))
            os.rmdir(folder)

        else:
            await update.message.reply_text("❌ Unsupported URL. Only YouTube and Instagram links are allowed.")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

# Entry point
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is running...")
    await app.run_polling()

# Run bot
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
