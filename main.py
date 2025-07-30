import os
import time
import telepot
from pytubefix import YouTube
import instaloader

TOKEN = "8359982751:AAHvsrsJXoABZe6kyQQoi-lJbEy5pxZ05mY"
bot = telepot.Bot(TOKEN)

TEMP_DIR = "temp_download"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def handle(msg):
    if 'text' not in msg:
        return

    chat_id = msg['chat']['id']
    text = msg['text'].strip()

    if text == "/start":
        bot.sendMessage(chat_id, "🎬 Please send a Youtube or an Instagram link.")
        return

    if not text.startswith("http"):
        bot.sendMessage(chat_id, "❗️ Please send a valid URL.")
        return

    try:
        bot.sendMessage(chat_id, "⏬ Downloading...")

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
                bot.sendMessage(chat_id, "⚠️ Hech qanday video topilmadi.")
                return

        else:
            bot.sendMessage(chat_id, "❗️ Faqat YouTube yoki Instagram linklar qabul qilinadi.")
            return

        with open(file_path, 'rb') as f:
            bot.sendVideo(chat_id, f)

        # Faylni o‘chirish
        if os.path.exists(file_path):
            os.remove(file_path)
        if "insta_temp" in file_path:
            import shutil
            shutil.rmtree(os.path.join(TEMP_DIR, "insta_temp"), ignore_errors=True)

    except Exception as e:
        bot.sendMessage(chat_id, f"⚠️ Xatolik yuz berdi:\n{e}")

bot.message_loop(handle)

print("🤖 Bot ishga tushdi. Kutilyapti...")
while True:
    time.sleep(10)
