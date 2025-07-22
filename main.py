import os
import logging
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from web3 import Web3

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
TOKEN = os.getenv("TELEGRAM_TOKEN")
PRIVATE_KEY = os.getenv("SENDER_PRIVATE_KEY")
CELO_NODE = os.getenv("CELO_NODE", "https://forno.celo.org")

if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set in environment variables.")
if not PRIVATE_KEY:
    raise ValueError("SENDER_PRIVATE_KEY is not set in environment variables.")

SENDER_ADDRESS = Web3().eth.account.from_key(PRIVATE_KEY).address

# Web3 setup
web3 = Web3(Web3.HTTPProvider(CELO_NODE))

# Sample quiz data
quiz = [
    {"question": "What is the capital of France?", "answer": "Paris"},
    {"question": "2 + 2 = ?", "answer": "4"},
    {"question": "What color is the sky on a clear day?", "answer": "Blue"}
]

user_state = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to the Quiz Bot!\nType /quiz to begin playing.")

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = {"score": 0, "current": 0}
    await send_question(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current = user_state[user_id]["current"]
    if current >= len(quiz):
        await update.message.reply_text(
            f"✅ You got {user_state[user_id]['score']} out of {len(quiz)}.\nSend your Celo wallet address to claim your G$ reward."
        )
        user_state[user_id]["awaiting_wallet"] = True
        return
    question = quiz[current]["question"]
    await update.message.reply_text(f"❓ Question {current + 1}: {question}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id in user_state:
        state = user_state[user_id]
        # Check if awaiting wallet address
        if state.get("awaiting_wallet"):
            if Web3.is_address(text):
                await update.message.reply_text("💸 Sending G$ reward...")
                success = send_gs_reward(text)
                if success:
                    await update.message.reply_text("✅ Reward sent successfully! Thanks for playing.")
                else:
                    await update.message.reply_text("❌ Failed to send reward.")
                user_state.pop(user_id)
            else:
                await update.message.reply_text("❌ Invalid wallet address. Please send a valid Celo wallet address.")
            return

        # If not awaiting wallet, check answer
        current = state["current"]
        correct_answer = quiz[current]["answer"].lower()
        if text.lower() == correct_answer:
            state["score"] += 1
            await update.message.reply_text("✅ Correct!")
        else:
            await update.message.reply_text(f"❌ Wrong! The correct answer was: {quiz[current]['answer']}")

        # Move to next question
        state["current"] += 1
        await send_question(update, context)
    else:
        await update.message.reply_text("Please start the quiz with /quiz.")

def send_gs_reward(wallet_address: str) -> bool:
    # Dummy implementation: Replace with your actual payment logic using web3.py
    print(f"Sending G$ reward to {wallet_address} from {SENDER_ADDRESS}")
    # Example: return True if successful, False otherwise
    return True

import asyncio

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("Starting bot...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
