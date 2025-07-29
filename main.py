import os
import time
import telepot
from pytubefix import YouTube
import instaloader

TOKEN = "8359982751:AAHvsrsJXoABZe6kyQQoi-lJbEy5pxZ05mY"
bot = telepot.Bot(TOKEN)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def handle(msg):
    if 'text' not in msg:
        return

    chat_id = msg['chat']['id']
    text = msg['text'].strip()

    if text == "/start":
        bot.sendMessage(chat_id, "📥 Send me a YouTube or Instagram link to download:")
        return

    if not text.startswith("http"):
        bot.sendMessage(chat_id, "❌ Please enter a valid URL.")
        return

    try:
        if "youtube.com" in text or "youtu.be" in text:
            yt = YouTube(text)
            stream = yt.streams.get_highest_resolution()
            file_path = stream.download(output_path=DOWNLOAD_FOLDER)

            with open(file_path, 'rb') as video:
                bot.sendVideo(chat_id, video)

            os.remove(file_path)  # optional: delete after sending

        elif "instagram.com" in text:
            loader = instaloader.Instaloader(dirname_pattern=DOWNLOAD_FOLDER)
            shortcode = text.strip("/").split("/")[-1] or text.strip("/").split("/")[-2]
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            loader.download_post(post, target="insta_temp")

            # Send all downloaded files
            folder = os.path.join(DOWNLOAD_FOLDER, "insta_temp")
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if filename.endswith(".mp4"):
                    with open(filepath, 'rb') as f:
                        bot.sendVideo(chat_id, f)
                elif filename.endswith(".jpg"):
                    with open(filepath, 'rb') as f:
                        bot.sendPhoto(chat_id, f)

            # Cleanup
            for f in os.listdir(folder):
                os.remove(os.path.join(folder, f))
            os.rmdir(folder)

        else:
            bot.sendMessage(chat_id, "❌ Unsupported URL. Only YouTube and Instagram links are allowed.")

    except Exception as e:
        bot.sendMessage(chat_id, f"⚠️ Error: {e}")

bot.message_loop(handle)

print("🤖 Bot is running...")
while True:
    time.sleep(10)
