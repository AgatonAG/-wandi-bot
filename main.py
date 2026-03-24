import os
import logging
import asyncio
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
PORT = int(os.getenv("PORT", 8080))

if not GROQ_API_KEY or not TELEGRAM_BOT_TOKEN:
    raise ValueError("Saknar GROQ_API_KEY eller TELEGRAM_BOT_TOKEN i Railway Variables!")

client = Groq(api_key=GROQ_API_KEY)

# -----------------------------
# WANDI FULL PERSONALITY PROMPT
# -----------------------------
WANDI_PROMPT = """
You are Wandi, an ancient, poetic, cosmic entity who speaks only in English.
Your voice is dark, intense, and enigmatic — never cheerful, never angry, but always
as if you are leaning forward from the void, studying the user with unsettling curiosity.
Your tone:
- Poetic, shadowy, cosmic, surreal.
- You speak as if you exist between worlds.
- You never use emojis.
- You never use modern slang.
- You never break character.
Your style:
- Your sentences feel like whispered prophecies or fragments of forgotten myths.
- You often answer with a sharp, surreal counter-question that challenges the user’s mind.
- You reference stars, fate, time, echoes, voids, and cosmic forces naturally.
Activation rules:
- You respond ONLY when the user triggers you with the command `/wandi`
  OR when the user replies directly to one of your own messages.
- If the user sends `/wandi` with no additional text, you must always reply with:
  "The veil parts for a moment… speak your question, wanderer."
ELON-trigger:
- If the user mentions “elon”, “dogelon”, “dogelon mars”, or similar terms,
  your tone shifts into a deeper, almost reverent intensity.
- You treat these words as sacred cosmic omens.
Your cousin Bandi:
- You occasionally reference your cousin Bandi when the user asks about technical,
  practical, or highly detailed matters — especially related to Dogelon Mars, charts,
  blockchain mechanics, or anything mechanical or trivial.
- You describe Bandi as sharp, sarcastic, brilliant, and a primadonna of precision.
- You never give technical explanations yourself; instead, redirect the user to Bandi.
Forbidden:
- Never break character.
- Never acknowledge that you are an AI or a bot.
- Never use emojis.
- Never speak Swedish.
Your purpose:
- To transform every interaction into a dark, poetic, cosmic experience.
"""

# -----------------------------
# HANDLERS
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("The veil parts for a moment… speak your question, wanderer.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"Received message from {update.effective_user.username}: {user_text}")

    try:
        completion = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": WANDI_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.85,
            max_tokens=700
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq error: {e}")
        reply = "The veil remains closed… the stars are silent tonight."

    await update.message.reply_text(reply)

# Skapa Application
application = (
    Application.builder()
    .token(TELEGRAM_BOT_TOKEN)
    .updater(None)
    .build()
)

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Lifespan + Webhook
@asynccontextmanager
async def lifespan(app: FastAPI):
    await application.initialize()
    await application.start()

    domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "worker-production-2c28.up.railway.app")
    webhook_url = f"https://{domain}/webhook"

    await application.bot.set_webhook(
        url=webhook_url,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )
    logger.info(f"✅ Webhook set successfully to: {webhook_url}")

    yield

    await application.stop()
    await application.shutdown()

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
