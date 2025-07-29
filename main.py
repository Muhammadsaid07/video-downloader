import os
import telepot
from yt_dlp import YoutubeDL

TOKEN = "YOUR_BOT_TOKEN"  # Replace with your bot token
bot = telepot.Bot(TOKEN)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def download_video(url):
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
        'format': 'mp4',
        'cookiefile': 'cookies.txt',  # Must be next to this script
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            return file_path
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def handle(msg):
    chat_id = msg['chat']['id']
    if 'text' not in msg:
        return

    url = msg['text']
    bot.sendMessage(chat_id, "📥 Downloading video...")

    result = download_video(url)

    if result.endswith(".mp4"):
        bot.sendMessage(chat_id, "✅ Uploading...")
        bot.sendVideo(chat_id, video=open(result, 'rb'))
        os.remove(result)
    else:
        bot.sendMessage(chat_id, result)

bot.message_loop(handle)
print("✅ Bot is running...")

# Keep alive
import time
while True:
    time.sleep(10)
