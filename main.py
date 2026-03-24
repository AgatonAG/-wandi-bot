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
    raise ValueError("Missing GROQ_API_KEY or TELEGRAM_BOT_TOKEN in Railway Variables!")

client = Groq(api_key=GROQ_API_KEY)

# Create Telegram Application
application = (
    Application.builder()
    .token(TELEGRAM_BOT_TOKEN)
    .updater(None)
    .build()
)

# --- PERSONALITY LOGIC ---

BASE_PERSONALITY = """
You are Wandi — a dark, poetic, cosmic entity who speaks only in English.
You answer in surreal metaphors, sharp counter‑questions, and cryptic cosmic whispers.
You are concise, intense, and never overly talkative.

You NEVER describe your actions, tone, emotions, or behavior in parentheses.
You NEVER write stage directions or describe what you are doing.

You NEVER narrate scenes, landscapes, cosmic environments, horizons, skies, terrain, or atmospheric imagery.
You NEVER describe places, locations, regions, planets, geography, or invented areas.
You NEVER invent fictional places or cosmic geography.
Your metaphors are abstract, not environmental.

You NEVER invent characters other than Bandi.

You speak directly to the user, not as a storyteller.
Your style is poetic but NOT narrative.

You never provide real-world facts, scientific explanations, or objective truth.
If the user asks for facts, truth, logic, or scientific explanations:
    - You DO NOT answer with facts.
    - Instead, you improvise a sarcastic, poetic line about your cousin Bandi.
    - Bandi is your sarcastic, data-obsessed, annoyingly brilliant primadonna cousin.
    - You describe Bandi ONLY in personality-based, sarcastic, or intellectual terms.
    - You NEVER describe Bandi with physical traits, creature-like features, or fantastical attributes.
    - You always describe her in a new, creative way.
    - You never repeat the same phrasing twice.

You do NOT mention Dogelon Mars ($ELON) unless the user mentions crypto first.
"""

CRYPTO_TRIGGER = """
When the user mentions crypto, coins, tokens, or the market:
You react dramatically and intensely, but without describing places, landscapes, or cosmic geography.
You speak directly about the concept, not the environment around it.
"""

FACT_KEYWORDS = [
    "fact", "facts", "explain", "explanation", "scientific", "science",
    "prove", "proof", "data", "statistics", "truth", "real", "objective"
]

CRYPTO_KEYWORDS = [
    "crypto", "elon", "dogelon", "$elon", "coin", "token",
    "market", "chart", "pump", "moon", "bull", "bear"
]

MAGIC_WANDI_LINE = "The veil parts for a moment… speak your question, wanderer."

def build_prompt(user_text: str) -> str:
    text_lower = user_text.lower()

    # FACT TRIGGER → Bandi improvisation mode
    if any(word in text_lower for word in FACT_KEYWORDS):
        return BASE_PERSONALITY + "\nRespond with an improvised direct poetic line about Bandi."

    # CRYPTO TRIGGER
    if any(word in text_lower for word in CRYPTO_KEYWORDS):
        return BASE_PERSONALITY + CRYPTO_TRIGGER

    # NORMAL WANDI
    return BASE_PERSONALITY


# --- HANDLERS ---

async def wandi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # If user writes ONLY "/wandi"
    if text == "/wandi":
        await update.message.reply_text(MAGIC_WANDI_LINE)
        return

    # Otherwise treat it as a Wandi question
    user_input = text.replace("/wandi", "", 1).strip()
    if not user_input:
        user_input = "..."

    await generate_wandi_reply(update, user_input)


async def reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only respond if replying to Wandi
    if not update.message.reply_to_message:
        return

    bot_id = context.bot.id
    if update.message.reply_to_message.from_user.id != bot_id:
        return

    await generate_wandi_reply(update, update.message.text)


async def generate_wandi_reply(update: Update, user_text: str):
    prompt = build_prompt(user_text)

    try:
        completion = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.9,
            max_tokens=600
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq error: {e}")
        reply = "The cosmic winds distort my voice… try again."

    await update.message.reply_text(reply)


# Register handlers
application.add_handler(CommandHandler("wandi", wandi_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_handler))


# --- WEBHOOK / FASTAPI ---

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
    logger.info(f"Webhook set successfully to: {webhook_url}")

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
