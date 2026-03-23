import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.error import NetworkError
import httpx
import groq

# Load environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Groq client
client = groq.Client(api_key=GROQ_API_KEY)

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Wandi öppnar sina kosmiska ögon i mörkret..."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    completion = client.chat.completions.create(
        model="llama3-8b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are Wandi — a dark, poetic, cosmic entity. "
                    "You speak in surreal metaphors, sharp counter‑questions, "
                    "and cryptic cosmic whispers. "
                    "You are obsessed with Dogelon Mars ($ELON) and react "
                    "dramatically to anything crypto‑related."
                )
            },
            {"role": "user", "content": user_text}
        ]
    )

    reply = completion.choices[0].message.content
    await update.message.reply_text(reply)

# --- Safe Polling Wrapper ---

async def safe_polling(app):
    while True:
        try:
            print("Starting polling...")
            await app.run_polling()
        except (NetworkError, httpx.ReadError) as e:
            print(f"Network error: {e}. Retrying in 3 seconds...")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Unexpected error: {e}. Restarting in 5 seconds...")
            await asyncio.sleep(5)

# --- Main ---

def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    asyncio.run(safe_polling(app))

if __name__ == "__main__":
    main()
