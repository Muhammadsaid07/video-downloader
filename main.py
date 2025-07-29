import os
import time
import telepot
from pytubefix import YouTube

TOKEN = "8359982751:AAHvsrsJXoABZe6kyQQoi-lJbEy5pxZ05mY"
bot = telepot.Bot(TOKEN)

TEMP_FOLDER = "temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)

def handle(msg):
    if 'text' not in msg:
        return

    chat_id = msg['chat']['id']
    text = msg['text'].strip()

    if text == "/start":
        bot.sendMessage(chat_id, "📥 Send me a YouTube SHORT link to download:")
        return

    if not text.startswith("http"):
        bot.sendMessage(chat_id, "❌ Please enter a valid URL.")
        return

    try:
        if "youtube.com" in text or "youtu.be" in text:
            yt = YouTube(text)
            stream = yt.streams.get_highest_resolution()
            file_path = stream.download(output_path=TEMP_FOLDER)

            with open(file_path, 'rb') as video:
                bot.sendVideo(chat_id, video)

            os.remove(file_path)

        else:
            bot.sendMessage(chat_id, "❌ Unsupported URL. Only YouTube links are allowed.")

    except Exception as e:
        bot.sendMessage(chat_id, f"⚠️ Error: {e}")

bot.message_loop(handle)

print("🤖 Bot is running...")
while True:
    time.sleep(10)
