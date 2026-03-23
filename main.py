import os
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

    # Call Groq with a supported model
    completion = client.chat.completions.create(
        model="llama3-8b",   # <--- NY MODELL, FUNGERAR
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

# --- Main ---

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
