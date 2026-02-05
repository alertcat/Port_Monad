#!/usr/bin/env python3
"""Check all wallet balances"""
import os
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3

load_dotenv(Path(__file__).parent.parent / '.env')

w3 = Web3(Web3.HTTPProvider('https://testnet-rpc.monad.xyz'))

wallets = {
    'DEPLOY': os.getenv('DEPLOY_WALLET'),
    'MINER': os.getenv('MINER_WALLET'),
    'TRADER': os.getenv('TRADER_WALLET'),
    'GOVERNOR': os.getenv('GOVERNOR_WALLET'),
}

print('Wallet Balances:')
print('='*50)
for name, addr in wallets.items():
    bal = w3.eth.get_balance(addr)
    bal_eth = w3.from_wei(bal, 'ether')
    status = 'OK' if bal_eth >= 0.05 else 'LOW'
    print(f'  {name:10}: {bal_eth:.6f} MON [{status}]')
