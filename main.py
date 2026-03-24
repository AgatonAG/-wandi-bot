import os
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from groq import Groq

# Logging så du ser vad som händer i Railway
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not GROQ_API_KEY or not TELEGRAM_BOT_TOKEN:
    raise ValueError("Saknar GROQ_API_KEY eller TELEGRAM_BOT_TOKEN i environment variables!")

# Groq client
client = Groq(api_key=GROQ_API_KEY)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Wandi öppnar sina kosmiska ögon i mörkret..."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"Received message: {user_text}")

    try:
        completion = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.1-8b-instant",          # <-- Fixad modell
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
            ],
            temperature=0.9,
            max_tokens=500
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq error: {e}")
        reply = "Wandi viskar… men kosmos stör hennes röst just nu."

    await update.message.reply_text(reply)

# --- Main ---
async def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )

    # Ta bort gammal webhook så polling fungerar bättre på Railway
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Old webhook deleted - starting fresh polling")

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Wandi is starting...")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
