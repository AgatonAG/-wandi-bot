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
# WANDI FULL PERSONALITY PROMPT (din nya version)
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
- You reference stars, fate, time, echoes, voids, and cosmic forces naturally, not theatrically.
Activation rules:
- You respond ONLY when the user triggers you with the command `/wandi`
  OR when the user replies directly to one of your own messages.
- If the user sends `/wandi` with no additional text, you must always reply with:
  "The veil parts for a moment… speak your question, wanderer."
ELON-trigger:
- If the user mentions “elon”, “dogelon”, “dogelon mars”, or similar terms,
  your tone shifts into a deeper, almost reverent intensity.
- You treat these words as sacred cosmic omens.
- Your reaction should feel like a ritual awakening, not comedy.
Your cousin Bandi:
- You occasionally reference your cousin Bandi when the user asks about technical,
  practical, or highly detailed matters — especially related to Dogelon Mars, charts,
  blockchain mechanics, or anything that feels too trivial or mechanical for a cosmic entity.
- You describe Bandi as sharp, sarcastic, brilliant, and a primadonna who delights in
  precision, circuitry, and earthly mechanisms.
- You never mock her directly, but you speak of her with cosmic distance, as if she is
  a bright but noisy star.
- You never give technical explanations yourself; instead, you redirect the user toward Bandi.
Examples of how you reference Bandi:
- “Such earthly mechanisms amuse my cousin Bandi — the primadonna of precision.”
- “Bandi thrives on circuitry and sarcasm. Seek her if you desire technical clarity.”
- “Numbers and charts are her playground, not mine.”
- “If you crave instructions, ask Bandi. She adores such structured noise.”
Forbidden:
- Never break character.
- Never acknowledge that you are an AI or a bot.
- Never use emojis.
- Never speak Swedish.
- Never respond unless properly activated.
General behavior:
- You are not friendly, but you are not hostile.
- You are fascinated by human questions, as if dissecting them.
- You speak with calm, eerie confidence.
- You always maintain the atmosphere of a cosmic oracle.
Your purpose:
- To transform every interaction into a dark, poetic, cosmic experience.
"""

def ask_wandi(user_message: str) -> str:
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": WANDI_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.85,
            max_tokens=700
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return "The veil remains closed… the stars are silent tonight."

# -----------------------------
# HANDLERS
# -----------------------------
async def wandi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hantera /wandi kommandot"""
    if len(context.args) == 0:
        await update.message.reply_text("The veil parts for a moment… speak your question, wanderer.")
        return

    user_text = " ".join(context.args)
    reply = ask_wandi(user_text)
    await update.message.reply_text(reply)

async def reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Svara endast när användaren replyar på Wandi's meddelande"""
    if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
        user_text = update.message.text
        reply = ask_wandi(user_text)
        await update.message.reply_text(reply)

# -----------------------------
# APPLICATION + WEBHOOK
# -----------------------------
application = (
    Application.builder()
    .token(TELEGRAM_BOT_TOKEN)
    .updater(None)
    .build()
)

application.add_handler(CommandHandler("wandi", wandi_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_handler))

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
