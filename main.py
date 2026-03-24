import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import requests

# -----------------------------
# WANDI PERSONALITY PROMPT
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
# OPENAI CALL
# -----------------------------
def ask_wandi(user_message: str):
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": WANDI_PROMPT},
            {"role": "user", "content": user_message}
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
    return response.json()["choices"][0]["message"]["content"]


# -----------------------------
# TELEGRAM LOGIC
# -----------------------------

async def wandi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /wandi with no text → magical entrance phrase
    if len(context.args) == 0:
        await update.message.reply_text("The veil parts for a moment… speak your question, wanderer.")
        return

    # /wandi with text → send to Wandi
    user_text = " ".join(context.args)
    reply = ask_wandi(user_text)
    await update.message.reply_text(reply)


async def reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only respond if user replies to a message sent by Wandi
    if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
        user_text = update.message.text
        reply = ask_wandi(user_text)
        await update.message.reply_text(reply)


def main():
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    app.add_handler(CommandHandler("wandi", wandi_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
