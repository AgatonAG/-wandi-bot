import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from groq import Groq

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))          # Railway ger dig denna port

if not GROQ_API_KEY or not TELEGRAM_BOT_TOKEN:
    raise ValueError("Saknar GROQ_API_KEY eller TELEGRAM_BOT_TOKEN i Railway Variables!")

client = Groq(api_key=GROQ_API_KEY)

# Skapa Application (utan updater eftersom vi använder webhook)
application = (
    Application.builder()
    .token(TELEGRAM_BOT_TOKEN)
    .updater(None)          # Viktigt för webhook!
    .build()
)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Wandi öppnar sina kosmiska ögon i mörkret...")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"Received message: {user_text}")

    try:
        completion = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.1-8b-instant",
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
            max_tokens=600
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq error: {e}")
        reply = "Wandi viskar… men kosmos stör hennes röst just nu."

    await update.message.reply_text(reply)

# Lägg till handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Lifespan för FastAPI (startar/stänger botten snyggt)
@asynccontextmanager
async def lifespan(app: FastAPI):
    await application.initialize()
    await application.start()
    
    # Sätt webhook automatiskt när appen startar
    webhook_url = f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN', 'din-app.railway.app')}/webhook"
    await application.bot.set_webhook(
        url=webhook_url,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )
    logger.info(f"Webhook set to: {webhook_url}")
    
    yield
    
    await application.stop()
    await application.shutdown()

# FastAPI app
app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data=data, bot=application.bot)
        await application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error"}

# Starta servern med uvicorn (Railway kör detta automatiskt)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
