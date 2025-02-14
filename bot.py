import os
from web3 import Web3
from telegram import Bot
import asyncio
import json
import time
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Then access them
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEB3_PROVIDER_URL = os.getenv('WEB3_PROVIDER_URL')
TOKEN_CONTRACT_ADDRESS = os.getenv('TOKEN_CONTRACT_ADDRESS')
TOKEN_ABI_FILE = os.getenv('TOKEN_ABI_FILE', 'token_abi.json')

# Now print them for debugging
print("Environment variables loaded:")
print(f"TELEGRAM_BOT_TOKEN: {'*' * 10}{TELEGRAM_BOT_TOKEN[-5:] if TELEGRAM_BOT_TOKEN else 'Not Found'}")
print(f"TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID if TELEGRAM_CHAT_ID else 'Not Found'}")
print(f"WEB3_PROVIDER_URL: {'*' * 10}{WEB3_PROVIDER_URL[-5:] if WEB3_PROVIDER_URL else 'Not Found'}")
print(f"TOKEN_CONTRACT_ADDRESS: {TOKEN_CONTRACT_ADDRESS if TOKEN_CONTRACT_ADDRESS else 'Not Found'}")
print(f"TOKEN_ABI_FILE: {TOKEN_ABI_FILE if TOKEN_ABI_FILE else 'Not Found'}")

# Add error checking
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables or .env file")

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEB3_PROVIDER_URL = os.getenv('WEB3_PROVIDER_URL')  # e.g. Infura, Alchemy, etc.
TOKEN_CONTRACT_ADDRESS = os.getenv('TOKEN_CONTRACT_ADDRESS')
TOKEN_ABI_FILE = os.getenv('TOKEN_ABI_FILE', 'token_abi.json')

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Initialize Web3 connection
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))

# Load token ABI
with open(TOKEN_ABI_FILE, 'r') as f:
    token_abi = json.load(f)

# Initialize contract
contract = w3.eth.contract(address=TOKEN_CONTRACT_ADDRESS, abi=token_abi)

# Dictionary to keep track of processed transactions
processed_tx_hashes = {}

async def send_telegram_message(message):
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='Markdown')

def format_amount(amount, decimals=18):
    return amount / (10 ** decimals)

async def check_transfers():
    try:
        # Get latest block number
        latest_block = w3.eth.block_number
        
        # Only check the last 10 blocks to avoid excessive load
        from_block = latest_block - 10
        
        # Get Transfer events
        transfer_filter = contract.events.Transfer.create_filter(fromBlock=from_block, toBlock='latest')
        transfers = transfer_filter.get_all_entries()
        
        for transfer in transfers:
            tx_hash = transfer.transactionHash.hex()
            
            # Skip if we've already processed this transaction
            if tx_hash in processed_tx_hashes:
                continue
            
            # Mark as processed
            processed_tx_hashes[tx_hash] = True
            
            # Check if this is a buy (transfer to someone other than zero address)
            if transfer.args['from'] != '0x0000000000000000000000000000000000000000':
                # Get transaction details
                tx = w3.eth.get_transaction(tx_hash)
                amount = format_amount(transfer.args.value)
                
                # Create message
                message = f"🚨 *New Buy Detected!* 🚨\n\n" \
                          f"Amount: {amount:.2f} tokens\n" \
                          f"Buyer: [{transfer.args.to[:6]}...{transfer.args.to[-4:]}](https://etherscan.io/address/{transfer.args.to})\n" \
                          f"[View Transaction](https://etherscan.io/tx/{tx_hash})"
                
                await send_telegram_message(message)
                
    except Exception as e:
        print(f"Error checking transfers: {e}")

async def main():
    # Clean up old entries every hour
    cleanup_interval = 3600  # 1 hour
    last_cleanup = time.time()
    
    print("Starting monitoring for buy transactions...")
    
    while True:
        await check_transfers()
        
        # Clean up old processed transactions to prevent memory buildup
        current_time = time.time()
        if current_time - last_cleanup > cleanup_interval:
            processed_tx_hashes.clear()
            last_cleanup = current_time
        
        # Wait before next check
        await asyncio.sleep(15)  # Check every 15 seconds

if __name__ == "__main__":
    asyncio.run(main())