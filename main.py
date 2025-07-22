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
                await update.message.reply_text("⚠️ Invalid wallet address. Please try again.")
        else:
            current = state["current"]
            correct_answer = quiz[current]["answer"]
            if text.lower() == correct_answer.lower():
                state["score"] += 1
                await update.message.reply_text("✅ Correct!")
            else:
                await update.message.reply_text(f"❌ Incorrect. The correct answer was: {correct_answer}")
            state["current"] += 1
            await send_question(update, context)
    else:
        await update.message.reply_text("Type /quiz to begin.")

def send_gs_reward(to_address):
    try:
        contract_address = Web3.to_checksum_address("0xdD2FD4581271e230360230F9337D5c0430Bf44C0")  # Replace with actual G$ token address
        token_abi = [{
            "constant": False,
            "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function"
        }]
        contract = web3.eth.contract(address=contract_address, abi=token_abi)
        nonce = web3.eth.get_transaction_count(SENDER_ADDRESS)
        tx = contract.functions.transfer(to_address, Web3.to_wei(0.1, 'ether')).build_transaction({
            'from': SENDER_ADDRESS,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': web3.to_wei('0.5', 'gwei')
        })
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print("Transaction sent:", tx_hash.hex())
        return True
    except Exception as e:
        print("Error sending reward:", e)
        return False

if __name__ == '__main__':
    print("Starting bot...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
