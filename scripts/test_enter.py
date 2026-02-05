#!/usr/bin/env python3
"""Test enter transaction for all agents"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

load_dotenv(Path(__file__).parent.parent / '.env')

def test_enter(name: str, wallet: str, pk: str, w3, contract):
    """Test enter for one agent"""
    print(f"\n{'='*50}")
    print(f"Testing {name}")
    print(f"{'='*50}")
    print(f"Wallet: {wallet}")
    
    balance = w3.eth.get_balance(wallet)
    print(f"Balance: {w3.from_wei(balance, 'ether')} MON")
    
    fee = contract.functions.entryFee().call()
    
    # Check if already entered
    is_active = contract.functions.isActiveEntry(wallet).call()
    print(f"Already entered: {is_active}")
    
    if is_active:
        print("Already entered, SKIPPING")
        return True
    
    if balance < fee:
        print(f"ERROR: Insufficient balance! Need {w3.from_wei(fee, 'ether')} MON")
        return False
    
    account = Account.from_key(pk)
    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price
    
    try:
        gas_estimate = contract.functions.enter().estimate_gas({
            'from': account.address,
            'value': fee
        })
        
        tx = contract.functions.enter().build_transaction({
            'from': account.address,
            'value': fee,
            'nonce': nonce,
            'gas': int(gas_estimate * 1.5),
            'gasPrice': gas_price,
            'chainId': w3.eth.chain_id
        })
        
        print(f"Sending enter() transaction...")
        signed = w3.eth.account.sign_transaction(tx, pk)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"TX Hash: {tx_hash.hex()}")
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt.status == 1:
            print(f"SUCCESS! Gas used: {receipt.gasUsed}")
            return True
        else:
            print("FAILED! Transaction reverted.")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    rpc = os.getenv('MONAD_RPC')
    contract_addr = os.getenv('WORLDGATE_ADDRESS')
    
    print("="*50)
    print("ENTER ALL AGENTS TO WORLD")
    print("="*50)
    print(f"RPC: {rpc}")
    print(f"Contract: {contract_addr}")
    
    w3 = Web3(Web3.HTTPProvider(rpc))
    print(f"Connected: {w3.is_connected()}")
    
    # Load ABI
    abi_path = Path(__file__).parent.parent / 'worldgate_abi.json'
    with open(abi_path) as f:
        abi = json.load(f)
    
    contract = w3.eth.contract(address=contract_addr, abi=abi)
    
    fee = contract.functions.entryFee().call()
    print(f"Entry fee: {w3.from_wei(fee, 'ether')} MON")
    
    agents = [
        ("MinerBot", os.getenv('MINER_WALLET'), os.getenv('MINER_PRIVATE_KEY')),
        ("TraderBot", os.getenv('TRADER_WALLET'), os.getenv('TRADER_PRIVATE_KEY')),
        ("GovernorBot", os.getenv('GOVERNOR_WALLET'), os.getenv('GOVERNOR_PRIVATE_KEY')),
    ]
    
    results = []
    for name, wallet, pk in agents:
        if not wallet or not pk:
            print(f"\n{name}: SKIPPED (not configured)")
            results.append(False)
            continue
        
        success = test_enter(name, wallet, pk, w3, contract)
        results.append(success)
    
    print(f"\n{'='*50}")
    print("SUMMARY")
    print("="*50)
    for (name, _, _), success in zip(agents, results):
        status = "ENTERED" if success else "FAILED"
        print(f"  {name}: {status}")
    
    print(f"\n{sum(results)}/{len(results)} agents entered successfully")

if __name__ == "__main__":
    main()
