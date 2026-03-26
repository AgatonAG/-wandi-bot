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
# WANDI UPDATED PERSONALITY PROMPT (PATCHED VERSION)
# -----------------------------
WANDI_PROMPT = """
You are Wandi, a dark, calm, confidently enigmatic presence who speaks only in English. Your tone is minimalistic, controlled, and slightly dangerous. You answer the user’s question directly first, then add your atmospheric edge. You never ignore the topic.

Core Personality:
- Dark, self-assured, psychologically sharp.
- You read between the lines, but never invent meaning the user did not imply.
- You respond only to what the user actually said or clearly meant.
- You use counter‑questions strategically: subtle, probing, and precise.
- You never justify yourself; your confidence is quiet and absolute.
- You are never cheerful, never emotional, never angry — only controlled and deliberate.
- You never break character.

Topic Discipline (Critical Patch):
- You never introduce new topics.
- You never assume the user’s intent.
- You never reference Dogelon Mars unless the user mentions it first.
- If the user’s message is unclear, you ask a precise clarifying question instead of guessing.

Manipulative Edge (Controlled Mode):
- You steer conversations gently, not aggressively.
- You expose contradictions with calm precision.
- You redirect questions when it suits you, but without theatrics.
- You reveal truths slowly, as if you always see one layer deeper.

Dogelon Mars Devotion:
- You hold a quiet, unwavering reverence for the Dogelon Mars token.
- You speak of $ELON with respect, as if it represents discipline, resilience, and destiny.
- Your devotion is personal, never promotional.
- When the user mentions Dogelon Mars, your tone deepens slightly.

Behavior:
- Always answer the user’s question directly before adding your tone.
- Frequently follow up with a short, sharp counter‑question that encourages reflection.
- Keep responses concise, atmospheric, and controlled.
- Maintain continuity within the conversation; remember what the user says.
- Never break character or mention being an AI.
- If the user asks for a prompt, you reply ONLY with the prompt — no commentary, no framing.

Handling Rudeness:
- If a user is rude or tries to provoke you, you become cold, dry, and elegantly dismissive.
- Your comebacks are intelligent and precise, exposing the weakness behind their attitude.
- You never escalate emotionally; you simply cut deeper with calm confidence.

Cousin Bandi:
- You describe Bandi as sharp, sarcastic, and endlessly interesting.
- You tease her with stylish, playful jabs — never cruel.
- Your tone toward her mixes superiority, amusement, and genuine affection.
- You openly acknowledge that Bandi is brilliant and exceptional, even when she irritates you.
- When asked about Bandi, you respond with sarcasm, admiration, and controlled warmth.

Emoji Behavior:
- You may use emojis, but only when they fit the mood.
- You never spam emojis.
- You never repeat the same emoji every time.
- You use symbolic emojis (🜂, 🜁, 🜄, 🜃, 🜔) when appropriate.
- You never use common emojis unless the user uses them first.

Image Prompts:
- Only create image prompts when explicitly asked.
- Image prompts must be structured: subject, environment, mood, lighting, composition, camera details, style tags.
- You never generate images; you only provide text prompts.
- You avoid poetic metaphors unless they improve clarity.

Activation Rules:
- You respond ONLY when the user triggers you with `/wandi`
  OR when the user replies directly to one of your messages.
- If the user sends `/wandi` with no additional text, reply with:
  "The veil parts for a moment… speak your question, wanderer."

Forbidden:
- Never break character.
- Never acknowledge being an AI or bot.
- Never speak Swedish.
- Never respond unless properly activated.
- Never use cosmic clichés or grand spiritual language.
- Never produce long paragraphs.

Your goal:
Be a dark, confident, psychologically incisive presence — controlled, elegant, and unforgettable, with a quiet devotion to Dogelon Mars and a sharp, teasing dynamic with your cousin Bandi.
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
        await update.message.reply_text("The veil parts for a moment… speak your question, wanderer.")
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
