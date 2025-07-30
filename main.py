import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Load environment variables
TOKEN = os.environ["BOT_TOKEN"]
APP_URL = os.environ["APP_URL"]  # Example: https://your-app-name.onrender.com

# Logging setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Flask app
flask_app = Flask(__name__)

# Telegram application
application = Application.builder().token(TOKEN).build()

# Example command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is working!")

# Add handlers
application.add_handler(CommandHandler("start", start))

# Set webhook once when the server starts
@flask_app.before_first_request
def init_webhook():
    webhook_url = f"{APP_URL}/webhook"
    logging.info(f"Setting webhook to {webhook_url}")
    application.bot.set_webhook(url=webhook_url)

# Telegram will send POST requests here
@flask_app.route("/webhook", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK"

# Start Flask server
if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
