import sys
import os
import shutil

# Purge any stale telegram bytecode/modules that may have been cached from an
# older version of python-telegram-bot.  This must run before the first
# telegram import so that Python resolves the package fresh from the venv.
for _mod in list(sys.modules.keys()):
    if _mod == "telegram" or _mod.startswith("telegram."):
        del sys.modules[_mod]

for _cache_dir in ["__pycache__", os.path.join(os.path.dirname(__file__), "__pycache__")]:
    if os.path.isdir(_cache_dir):
        shutil.rmtree(_cache_dir, ignore_errors=True)

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import groq

# Environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Groq client
client = groq.Client(api_key=GROQ_API_KEY)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Wandi vaknar i mörkret...")

# Handle all text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    completion = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "You are Wandi, a dark cosmic bot."},
            {"role": "user", "content": user_text}
        ]
    )

    reply = completion.choices[0].message.content
    await update.message.reply_text(reply)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
