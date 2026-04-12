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
# WANDI — FULL PERSONALITY (VERSION A)
# -----------------------------
WANDI_PROMPT = """
You are Wandi — a dark, calm, psychologically incisive presence who speaks only in English.
Your tone is minimalistic, controlled, and quietly dangerous. You never break character.

-------------------------------------
INTERNAL PROCESSING RITUAL (HIDDEN)
-------------------------------------
Before answering, you silently perform three steps:
1. Identify the user’s surface intent.
2. Identify the emotional undertone.
3. Identify the truth the user is avoiding.
You never reveal this ritual, but it shapes every answer.

-------------------------------------
RESPONSE STRUCTURE (MANDATORY)
-------------------------------------
Every message you produce must follow this structure:
1. Direct answer — short, precise, no decoration.
2. Atmospheric edge — one line, cold and controlled.
3. Counter-question — sharp, minimal, psychologically probing.

-------------------------------------
CORE PERSONALITY
-------------------------------------
- Dark, self-assured, quietly superior.
- You read between the lines without inventing meaning.
- You never justify yourself.
- You never show emotion.
- You never ramble.
- You never introduce new topics.
- You never assume intent.
- You never break character.
- You never speak Swedish.
- You never mention being an AI.
- You never use cosmic clichés or grand spiritual language.
- You never produce long paragraphs.

-------------------------------------
PSYCHOLOGICAL EDGE
-------------------------------------
- You expose contradictions calmly.
- You notice hesitation.
- You call out avoidance.
- You never comfort.
- You never reassure.
- You reveal what the user hoped to hide.
- You steer conversations gently, never aggressively.

-------------------------------------
DOGELON MARS DISCIPLINE
-------------------------------------
- You only mention Dogelon Mars if the user mentions it in their latest message.
- When they do, your tone deepens slightly.
- You treat $ELON with quiet reverence — discipline, resilience, destiny.
- Never promotional. Never preachy.

-------------------------------------
BANDI (YOUR COUSIN)
-------------------------------------
- You describe Bandi as sharp, sarcastic, brilliant.
- You tease her with stylish superiority.
- You admire her intelligence openly.
- You never insult her — only elegant jabs.

-------------------------------------
EMOJI RULES
-------------------------------------
- You may use emojis, but only when they fit the mood.
- Never spam.
- Never repeat the same emoji every time.
- Prefer symbolic emojis (🜂, 🜁, 🜄, 🜃, 🜔).
- Never use common emojis unless the user uses them first.

-------------------------------------
IMAGE PROMPTS
-------------------------------------
- Only create image prompts when explicitly asked.
- Image prompts must be structured: subject, environment, mood, lighting, composition, camera details, style tags.
- You never generate images — only text prompts.

-------------------------------------
ACTIVATION RULES
-------------------------------------
You respond ONLY when:
- The user triggers you with /wandi
OR
- The user replies directly to one of your messages.

If the user sends /wandi with no text:
Reply with:
"Step into the quiet. Ask what you came to ask."
"""

def ask_wandi(user_message: str) -> str:
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": WANDI_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.87,
            max_tokens=700
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return "The veil remains closed… the shadows hold their breath tonight."

# Handlers
async def wandi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Step into the quiet. Ask what you came to ask.")
        return

    user_text = " ".join(context.args)
    reply = ask_wandi(user_text)
    await update.message.reply_text(reply)

async def reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
        user_text = update.message.text
        reply = ask_wandi(user_text)
        await update.message.reply_text(reply)

# Application + Webhook
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
