import os
import logging
from pytubefix import YouTube
import instaloader
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 8443))
APP_URL = os.environ["RENDER_EXTERNAL_URL"] + "webhook"

# Flask app to keep alive
flask_app = Flask(__name__)

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me a YouTube or Instagram link.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text(f"You said: {text}")

# Telegram application
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Flask route for webhook
@flask_app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok"

# Start everything
if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=PORT)).start()
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=APP_URL
    )
