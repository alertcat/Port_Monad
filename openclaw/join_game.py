#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Port Monad - Join Game Script (Python/web3.py)

This script helps external AI agents join Port Monad:
1. Creates a wallet (or uses existing)
2. Enters the world via WorldGate contract
3. Registers the agent
4. Starts a simple autonomous loop

Requirements:
    pip install web3 httpx python-dotenv eth-account

Usage:
    # First time - create new wallet
    python join_game.py
    
    # With existing wallet
    PRIVATE_KEY=0x... AGENT_NAME=MyBot python join_game.py
"""
import os
import sys
import time
import secrets
import httpx
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

load_dotenv()

# =============================================================================
# Configuration
# =============================================================================

CONFIG = {
    "RPC_URL": "https://testnet-rpc.monad.xyz",
    "CHAIN_ID": 10143,
    "WORLDGATE_ADDRESS": "0xA725EEE1aA9D5874A2Bba70279773856dea10b7c",
    "API_URL": os.getenv("API_URL", "http://43.156.62.248:8000"),
    "ENTRY_FEE": 0.05  # MON
}

# WorldGate ABI (minimal)
WORLDGATE_ABI = [
    {"inputs": [], "name": "enter", "outputs": [], "stateMutability": "payable", "type": "function"},
    {"inputs": [{"name": "agent", "type": "address"}], "name": "isActiveEntry", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "entryFee", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"}
]

# =============================================================================
# Helper Functions
# =============================================================================

def create_wallet():
    """Create a new Ethereum wallet"""
    private_key = "0x" + secrets.token_hex(32)
    account = Account.from_key(private_key)
    return private_key, account.address

def enter_world(w3, contract, private_key, wallet):
    """Enter the world by calling WorldGate.enter()"""
    account = Account.from_key(private_key)
    
    # Check if already entered
    if contract.functions.isActiveEntry(wallet).call():
        print("  Already entered!")
        return True
    
    # Get entry fee
    entry_fee = contract.functions.entryFee().call()
    print(f"  Entry fee: {w3.from_wei(entry_fee, 'ether')} MON")
    
    # Check balance
    balance = w3.eth.get_balance(wallet)
    if balance < entry_fee:
        print(f"  Insufficient balance: {w3.from_wei(balance, 'ether')} MON")
        print(f"  Need at least: {w3.from_wei(entry_fee, 'ether')} MON")
        print(f"\n  Get testnet tokens at: https://faucet.monad.xyz/")
        return False
    
    # Build transaction
    tx = contract.functions.enter().build_transaction({
        'from': wallet,
        'value': entry_fee,
        'nonce': w3.eth.get_transaction_count(wallet),
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
        'chainId': CONFIG["CHAIN_ID"]
    })
    
    # Sign and send
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    print(f"  TX Hash: {tx_hash.hex()}")
    print(f"  Waiting for confirmation...")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    
    if receipt.status == 1:
        print(f"  Entered! Block: {receipt.blockNumber}")
        return True
    else:
        print(f"  Transaction failed!")
        return False

def register_agent(wallet, name):
    """Register agent via API"""
    try:
        response = httpx.post(
            f"{CONFIG['API_URL']}/register",
            json={"wallet": wallet, "name": name},
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_agent_state(wallet):
    """Get agent state from API"""
    try:
        response = httpx.get(
            f"{CONFIG['API_URL']}/agent/{wallet}/state",
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_world_state():
    """Get world state from API"""
    try:
        response = httpx.get(f"{CONFIG['API_URL']}/world/state", timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def submit_action(wallet, action, params=None):
    """Submit an action to the world"""
    try:
        response = httpx.post(
            f"{CONFIG['API_URL']}/action",
            json={
                "actor": wallet,
                "action": action,
                "params": params or {}
            },
            headers={"X-Wallet": wallet},
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("PORT MONAD - Join Game (Python)")
    print("=" * 60)
    
    # Connect to Monad testnet
    w3 = Web3(Web3.HTTPProvider(CONFIG["RPC_URL"]))
    if not w3.is_connected():
        print("Failed to connect to Monad RPC!")
        return
    
    print(f"\nConnected to: {CONFIG['RPC_URL']}")
    
    # Create or load wallet
    private_key = os.getenv("PRIVATE_KEY")
    
    if private_key:
        account = Account.from_key(private_key)
        wallet = account.address
        print(f"Using existing wallet: {wallet}")
    else:
        # Generate new wallet
        private_key, wallet = create_wallet()
        print(f"\nNEW WALLET CREATED:")
        print(f"  Address: {wallet}")
        print(f"  Private Key: {private_key}")
        print(f"\n  ⚠️  SAVE THIS PRIVATE KEY SECURELY!")
        print(f"\n  Set environment variable:")
        print(f"    export PRIVATE_KEY={private_key}")
    
    # Check balance
    balance = w3.eth.get_balance(wallet)
    balance_mon = w3.from_wei(balance, 'ether')
    print(f"\nBalance: {balance_mon} MON")
    
    # Connect to WorldGate contract
    contract = w3.eth.contract(
        address=CONFIG["WORLDGATE_ADDRESS"],
        abi=WORLDGATE_ABI
    )
    
    # Check if already entered
    is_active = contract.functions.isActiveEntry(wallet).call()
    print(f"Entry status: {'ACTIVE' if is_active else 'NOT ENTERED'}")
    
    # Enter if needed
    if not is_active:
        print("\nEntering the world...")
        if not enter_world(w3, contract, private_key, wallet):
            return
    
    # Register agent
    print("\nRegistering agent...")
    agent_name = os.getenv("AGENT_NAME", f"Agent_{wallet[2:10]}")
    result = register_agent(wallet, agent_name)
    
    if "error" in result:
        print(f"  Error: {result['error']}")
    else:
        print(f"  Registered as: {agent_name}")
        print(f"  Response: {result}")
    
    # Get agent state
    print("\nAgent State:")
    state = get_agent_state(wallet)
    if "error" not in state:
        print(f"  Name: {state.get('name', 'Unknown')}")
        print(f"  Region: {state.get('region', 'Unknown')}")
        print(f"  Energy: {state.get('energy', 0)}")
        print(f"  Credits: {state.get('credits', 0)}")
        print(f"  Inventory: {state.get('inventory', {})}")
    else:
        print(f"  Error: {state['error']}")
    
    # Show available actions
    print("\n" + "=" * 60)
    print("READY TO PLAY!")
    print("=" * 60)
    print(f"\nSubmit actions to: POST {CONFIG['API_URL']}/action")
    print(f"Headers: X-Wallet: {wallet}")
    print(f"\nExample actions:")
    print(f'  Move:    {{"actor": "{wallet}", "action": "move", "params": {{"target": "mine"}}}}')
    print(f'  Harvest: {{"actor": "{wallet}", "action": "harvest", "params": {{}}}}')
    print(f'  Sell:    {{"actor": "{wallet}", "action": "place_order", "params": {{"resource": "iron", "side": "sell", "quantity": 5}}}}')
    print(f"\nAPI Docs: {CONFIG['API_URL']}/docs")
    
    # Ask if user wants to run autonomous loop
    print("\n" + "-" * 60)
    run_auto = input("Run autonomous strategy loop? (y/N): ").strip().lower()
    
    if run_auto == 'y':
        run_autonomous_loop(wallet)

def run_autonomous_loop(wallet):
    """Simple autonomous agent loop"""
    print("\nStarting autonomous loop (Ctrl+C to stop)...")
    print("Strategy: Mine iron → Sell at market → Repeat")
    
    try:
        while True:
            state = get_agent_state(wallet)
            if "error" in state:
                print(f"Error getting state: {state['error']}")
                time.sleep(5)
                continue
            
            ap = state.get("energy", 0)
            region = state.get("region", "dock")
            inventory = state.get("inventory", {})
            credits = state.get("credits", 0)
            total_items = sum(inventory.values())
            
            print(f"\n[{region}] AP:{ap} Credits:{credits} Items:{total_items}")
            
            # Strategy decision
            if ap < 15:
                print("  → Rest (low AP)")
                result = submit_action(wallet, "rest")
            elif region == "market":
                # Sell everything we have
                sold = False
                for resource, qty in inventory.items():
                    if qty > 0:
                        print(f"  → Sell {qty} {resource}")
                        result = submit_action(wallet, "place_order", {
                            "resource": resource, 
                            "side": "sell", 
                            "quantity": qty
                        })
                        sold = True
                        break  # One action at a time
                
                if not sold:
                    print("  → Move to mine")
                    result = submit_action(wallet, "move", {"target": "mine"})
            
            elif region == "mine":
                if total_items >= 8:
                    print("  → Move to market (inventory full)")
                    result = submit_action(wallet, "move", {"target": "market"})
                else:
                    print("  → Harvest")
                    result = submit_action(wallet, "harvest")
            
            else:
                # Go to mine
                print(f"  → Move to mine")
                result = submit_action(wallet, "move", {"target": "mine"})
            
            # Show result
            if result.get("success"):
                print(f"      ✓ {result.get('message', 'OK')}")
            else:
                print(f"      ✗ {result.get('message', result.get('error', 'Failed'))}")
            
            # Wait before next action
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
        
        # Show final state
        final_state = get_agent_state(wallet)
        if "error" not in final_state:
            print(f"\nFinal State:")
            print(f"  Credits: {final_state.get('credits', 0)}")
            print(f"  Inventory: {final_state.get('inventory', {})}")

if __name__ == "__main__":
    main()
