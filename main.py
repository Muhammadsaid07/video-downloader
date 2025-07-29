import os
import time
import telepot
import yt_dlp

# Set your bot token here
TOKEN = "8359982751:AAHvsrsJXoABZe6kyQQoi-lJbEy5pxZ05mY"  # 🔁 Replace with your real bot token
bot = telepot.Bot(TOKEN)

# Create a temp download folder
TEMP_FOLDER = "temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)

def handle(msg):
    if 'text' not in msg:
        return

    chat_id = msg['chat']['id']
    text = msg['text'].strip()

    if text == "/start":
        bot.sendMessage(chat_id, "👋 Welcome! Send me a YouTube **Shorts or video link**, and I’ll download it for you.")
        return

    if not text.startswith("http"):
        bot.sendMessage(chat_id, "❌ Please send a valid YouTube video link.")
        return

    bot.sendMessage(chat_id, "⏬ Downloading your video...")

    try:
        ydl_opts = {
            'outtmpl': f'{TEMP_FOLDER}/%(id)s.%(ext)s',
            'format': 'mp4',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(text, download=True)
            file_path = ydl.prepare_filename(info)

        with open(file_path, 'rb') as video:
            bot.sendVideo(chat_id, video)

        os.remove(file_path)

    except Exception as e:
        bot.sendMessage(chat_id, f"⚠️ Error: {e}")

bot.message_loop(handle)

print("🤖 Bot is running...")
while True:
    time.sleep(10)
