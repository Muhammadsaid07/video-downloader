import os
import logging
import asyncio
import nest_asyncio
from pytubefix import YouTube
import instaloader
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

nest_asyncio.apply()

# Setup
TOKEN = os.environ.get("BOT_TOKEN", "8359982751:AAHvsrsJXoABZe6kyQQoi-lJbEy5pxZ05mY")  # Replace or set in Render
DOWNLOAD_FOLDER = "/tmp"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send me a YouTube or Instagram link to download:")

# Handle links
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if not text.startswith("http"):
        await update.message.reply_text("❌ Please enter a valid URL.")
        return

    try:
        # YouTube
        if "youtube.com" in text or "youtu.be" in text:
            yt = YouTube(text)
            stream = yt.streams.get_highest_resolution()
            file_path = stream.download(output_path=DOWNLOAD_FOLDER)

            with open(file_path, 'rb') as video:
                await context.bot.send_video(chat_id=chat_id, video=video)

            os.remove(file_path)

        # Instagram
        elif "instagram.com" in text:
            loader = instaloader.Instaloader(dirname_pattern=DOWNLOAD_FOLDER, download_comments=False)
            shortcode = [x for x in text.strip("/").split("/") if x][-1]
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            temp_folder = os.path.join(DOWNLOAD_FOLDER, "insta_temp")
            loader.download_post(post, target=temp_folder)

            # Send files
            for filename in os.listdir(temp_folder):
                filepath = os.path.join(temp_folder, filename)
                if filename.endswith(".mp4"):
                    with open(filepath, 'rb') as f:
                        await context.bot.send_video(chat_id=chat_id, video=f)
                elif filename.endswith(".jpg"):
                    with open(filepath, 'rb') as f:
                        await context.bot.send_photo(chat_id=chat_id, photo=f)

            # Clean up
            for f in os.listdir(temp_folder):
                os.remove(os.path.join(temp_folder, f))
            os.rmdir(temp_folder)

        else:
            await update.message.reply_text("❌ Unsupported URL. Only YouTube and Instagram links are allowed.")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

# Main runner
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot is running...")
    await app.run_polling()

# Start
if __name__ == "__main__":
    asyncio.run(main())
