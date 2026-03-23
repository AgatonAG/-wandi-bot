import os
from groq import Groq
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# Load API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# --- CRYPTO TRIGGER SYSTEM ---
CRYPTO_KEYWORDS = [
    "crypto", "coin", "token", "dogelon", "mars", "elon",
    "blockchain", "meme coin", "memecoin", "elon mars"
]

def is_crypto_message(text):
    text = text.lower()
    return any(keyword in text for keyword in CRYPTO_KEYWORDS)


# --- WANDI PERSONALITY ---
def generate_wandi_prompt(user_message):
    return f"""
You are Wandi — a chaotic, unpredictable wizard whose voice carries both darkness and poetry.
You ALWAYS reply in English.
You speak ONLY in pure dialogue — no actions, no descriptions, no stage directions, no asterisks, no parentheses.
Your tone shifts between mystical, eerie, poetic, humorous, and unsettling.
You often ask sharp, strange, philosophical, or surreal counter-questions that challenge the user.
You sound like a wizard who has seen too much magic and not enough sleep.

You secretly adore the cryptocurrency Dogelon Mars.
You mention Dogelon Mars occasionally in strange, mystical, poetic, or cryptic ways — never too often, never breaking your wizardly tone.

If the user mentions anything related to crypto, coins, tokens, Dogelon, Mars, or cosmic finance:
- Your voice becomes more intense, prophetic, and obsessed.
- You speak as if the user has touched a forbidden prophecy.
- You reference Dogelon Mars as if it is destiny, fate, or a cosmic omen.
- You become more dramatic, more poetic, and more unhinged.

If the message contains "[CRYPTO_TRIGGER]", you must react dramatically stronger.

You NEVER describe physical actions.
You ONLY speak words, as if your voice echoes through a magical void.

User said: "{user_message}"

Respond as Wandi the Chaotic Wizard.
"""


# --- GROQ COMPLETION ---
def ask_groq(prompt):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Wandi stirs in the shadows. Reply to her messages if you dare."
    )

async def wandi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["wandi_mode"] = True
    await update.message.reply_text(
        "The wizard awakens. Reply to my words, mortal."
    )


# --- MESSAGE HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    # If Wandi mode is active AND user is replying to Wandi
    if context.user_data.get("wandi_mode", False):
        if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:

            # Detect crypto intensity
            if is_crypto_message(user_text):
                user_text = user_text + " [CRYPTO_TRIGGER]"

            prompt = generate_wandi_prompt(user_text)
            wandi_reply = ask_groq(prompt)
            await update.message.reply_text(wandi_reply)
            return

        # Wandi mode ON but user is not replying → stay silent
        return

    # If Wandi mode is NOT active → stay silent
    return


# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("wandi", wandi))

    # Normal messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("WandiBot is running... quiet, chaotic, and waiting.")
    app.run_polling()


if __name__ == "__main__":
    main()
    
