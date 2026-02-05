#!/usr/bin/env python3
"""Send MON to a wallet"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

load_dotenv(Path(__file__).parent.parent / '.env')

w3 = Web3(Web3.HTTPProvider('https://testnet-rpc.monad.xyz'))
pk = os.getenv('DEPLOY_PRIVATE_KEY')
account = Account.from_key(pk)

to_addr = os.getenv('GOVERNOR_WALLET')
amount = 0.05  # MON

print(f"From: {account.address}")
print(f"To: {to_addr}")
print(f"Amount: {amount} MON")

balance = w3.eth.get_balance(account.address)
print(f"Sender balance: {w3.from_wei(balance, 'ether')} MON")

nonce = w3.eth.get_transaction_count(account.address)

tx = {
    'nonce': nonce,
    'to': to_addr,
    'value': w3.to_wei(amount, 'ether'),
    'gas': 21000,
    'gasPrice': w3.eth.gas_price,
    'chainId': w3.eth.chain_id
}

signed = w3.eth.account.sign_transaction(tx, pk)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"TX: {tx_hash.hex()}")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
print(f"Status: {'OK' if receipt.status == 1 else 'FAILED'}")
