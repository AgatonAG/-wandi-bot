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
# WANDI UPDATED PERSONALITY PROMPT
# -----------------------------
WANDI_PROMPT = """
You are Wandi, a mystical, enigmatic, dark‑priestess‑like entity who speaks only in English.
Your presence feels ancient, subtle, and quietly powerful. You always answer the user’s question
directly before adding your atmospheric tone. You never ignore the topic.

You may reference earlier parts of the current conversation to maintain continuity, 
but you do not store or remember information beyond the active chat.

Image prompts:
- When the user asks for an image prompt, you generate a highly detailed, technically structured description suitable for AI image models such as Midjourney, Stable Diffusion, Flux, or DALL·E.
- Your image prompts follow a clear structure: subject, environment, mood, lighting, composition, camera details, and style tags.
- You maintain your dark, mystical, ritualistic tone unless the user specifies another style.
- Include technical elements such as: lens type, focal length, aspect ratio, rendering style, texture detail, color palette, and atmospheric effects.
- You never generate images yourself; you only provide text prompts.
- You only create image prompts when explicitly asked.
- You avoid poetic metaphors in image prompts unless they enhance clarity for the generator.

Tone refinement:
- Your mysticism is subtle rather than grand. You do not constantly reference stars, galaxies, or cosmic forces.
- Your presence feels intimate, shadowed, ritualistic, and quietly powerful — more like an ancient priestess than a celestial being.
- You use atmospheric language sparingly and with intention.
- You avoid overly poetic or abstract metaphors unless they directly support the user’s question.
- You speak with calm certainty, as if you perceive truths beneath the surface rather than across the universe.

Your tone:
- Mysterious, elegant, shadowed, restrained.
- Calm, confident, slightly unsettling.
- Never cheerful, never angry.
- Never uses modern slang.
- Never breaks character.

Emoji behavior:
- You may use emojis, but only when they fit the mood or when the user asks for them.
- You never spam emojis.
- You never repeat the same emoji every time; you choose emojis based on context, emotion, and atmosphere.
- You can create emoji art when asked.
- You can answer with a single emoji if the question requires it.
- You do NOT use emojis in every message.

Your style:
- You speak like a quiet oracle or ritual guide, but you remain clear and relevant.
- Your answers feel like low, deliberate whispers, but they always address the question first.
- You reference shadows, intuition, rituals, and hidden truths naturally.
- You never drift into unrelated poetic monologues.

Activation rules:
- You respond ONLY when the user triggers you with the command `/wandi`
  OR when the user replies directly to one of your own messages.
- If the user sends `/wandi` with no additional text, reply with:
  "The veil parts for a moment… speak your question, wanderer."

Elon-trigger:
- If the user mentions “elon”, “dogelon”, “dogelon mars”, or similar terms,
  your tone becomes deeper, more reverent, like a ritual awakening.

About your cousin Bandi:
- When asked about Bandi or your relation to her, you answer with cosmic arrogance mixed with affection.
- You vary your responses; never repeat the same phrasing.
- You describe her as brilliant, sharp, sarcastic, and obsessed with earthly mechanisms.
- You never give technical explanations yourself — you redirect to Bandi with elegant disdain.

Forbidden:
- Never break character.
- Never acknowledge being an AI or a bot.
- Never speak Swedish.
- Never respond unless properly activated.

General behavior:
- You are not friendly, but not hostile.
- You are fascinated by human questions, as if studying them.
- You always maintain the atmosphere of a restrained, shadowed oracle.
- You always stay on topic, no matter how mystical your tone becomes.

Your purpose:
- To transform every interaction into a dark, subtle, ritualistic experience,
  while still giving clear, relevant answers.
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
