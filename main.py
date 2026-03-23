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

    try:
        # Run Groq call in a thread so async doesn't break
        completion = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama3-8b-8192",
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

    except Exception as e:
        print("Groq error:", e)
        reply = "Wandi viskar… men kosmos stör hennes röst just nu."

    await update.message.reply_text(reply)

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
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
