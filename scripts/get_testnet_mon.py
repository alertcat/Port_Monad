#!/usr/bin/env python3
"""Get testnet MON for agent wallets"""
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Faucet endpoints to try
FAUCETS = [
    {
        "name": "Moltiverse Agent Faucet",
        "url": "https://agents.devnads.com/v1/faucet",
        "method": "POST",
        "payload_key": "address"
    },
    {
        "name": "Monad Testnet Faucet",
        "url": "https://faucet.testnet.monad.xyz/api/claim",
        "method": "POST", 
        "payload_key": "address"
    }
]

def request_from_faucet(address: str, faucet: dict):
    """Request tokens from a faucet"""
    print(f"  Trying {faucet['name']}...")
    
    try:
        if faucet['method'] == 'POST':
            payload = {faucet['payload_key']: address}
            resp = requests.post(faucet['url'], json=payload, timeout=30)
        else:
            resp = requests.get(f"{faucet['url']}?address={address}", timeout=30)
        
        if resp.status_code == 200:
            print(f"    SUCCESS: {resp.json()}")
            return True
        else:
            print(f"    Failed: {resp.status_code} - {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"    Error: {e}")
        return False

def check_balance(address: str):
    """Check MON balance"""
    from web3 import Web3
    
    rpc = os.getenv('MONAD_RPC', 'https://testnet-rpc.monad.xyz')
    w3 = Web3(Web3.HTTPProvider(rpc))
    
    try:
        balance = w3.eth.get_balance(address)
        return w3.from_wei(balance, 'ether')
    except:
        return 0

def main():
    print("=" * 60)
    print("Requesting Testnet MON for Agent Wallets")
    print("=" * 60)
    
    # Agent wallets
    wallets = [
        ("MINER", os.getenv('MINER_WALLET')),
        ("TRADER", os.getenv('TRADER_WALLET')),
        ("GOVERNOR", os.getenv('GOVERNOR_WALLET')),
    ]
    
    print("\nWallets to fund:")
    for name, addr in wallets:
        if addr:
            balance = check_balance(addr)
            print(f"  {name}: {addr} (Balance: {balance} MON)")
        else:
            print(f"  {name}: NOT SET")
    
    print("\n" + "-" * 60)
    
    for name, addr in wallets:
        if not addr or addr.startswith('0xTrader') or addr.startswith('0xGovernor'):
            print(f"\n{name}: Skipping (invalid address)")
            continue
        
        print(f"\n{name} ({addr}):")
        
        # Check current balance
        balance = check_balance(addr)
        if balance > 0.01:
            print(f"  Already has {balance} MON, skipping")
            continue
        
        # Try each faucet
        success = False
        for faucet in FAUCETS:
            if request_from_faucet(addr, faucet):
                success = True
                break
        
        if not success:
            print(f"  Could not get tokens from any faucet")
            print(f"  Manual options:")
            print(f"    1. Discord faucet: https://discord.gg/monaddev")
            print(f"    2. Send from deploy wallet")
    
    # Final balance check
    print("\n" + "=" * 60)
    print("Final Balances:")
    print("=" * 60)
    for name, addr in wallets:
        if addr and not addr.startswith('0xTrader') and not addr.startswith('0xGovernor'):
            balance = check_balance(addr)
            status = "OK" if balance > 0.05 else "NEED FUNDING"
            print(f"  {name}: {balance} MON [{status}]")

def send_from_deploy_wallet():
    """Send MON from deploy wallet to agent wallets"""
    from web3 import Web3
    from eth_account import Account
    
    rpc = os.getenv('MONAD_RPC', 'https://testnet-rpc.monad.xyz')
    w3 = Web3(Web3.HTTPProvider(rpc))
    
    private_key = os.getenv('DEPLOY_PRIVATE_KEY')
    deployer = Account.from_key(private_key).address
    
    wallets = [
        ("MINER", os.getenv('MINER_WALLET')),
        ("TRADER", os.getenv('TRADER_WALLET')),
        ("GOVERNOR", os.getenv('GOVERNOR_WALLET')),
    ]
    
    amount = w3.to_wei(0.1, 'ether')  # 0.1 MON each
    
    print(f"\nSending 0.1 MON from {deployer} to each agent...")
    
    nonce = w3.eth.get_transaction_count(deployer)
    
    for name, addr in wallets:
        if not addr or not addr.startswith('0x') or len(addr) != 42:
            print(f"  {name}: Invalid address, skipping")
            continue
        
        print(f"  Sending to {name} ({addr})...")
        
        tx = {
            'nonce': nonce,
            'to': addr,
            'value': amount,
            'gas': 21000,
            'gasPrice': w3.eth.gas_price,
            'chainId': w3.eth.chain_id
        }
        
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status == 1:
            print(f"    OK: {tx_hash.hex()}")
        else:
            print(f"    FAILED")
        
        nonce += 1

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--send':
        send_from_deploy_wallet()
    else:
        main()
        print("\n" + "-" * 60)
        print("To send MON from deploy wallet, run:")
        print("  python scripts/get_testnet_mon.py --send")
