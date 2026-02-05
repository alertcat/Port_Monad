#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy WorldGateV2 to Monad Mainnet

This script:
1. Compiles WorldGateV2.sol using solcx
2. Deploys to Monad mainnet
3. Funds the reward pool
4. Updates .env with new contract address

Requirements:
    pip install web3 py-solc-x python-dotenv

Usage:
    python deploy_mainnet.py
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# Monad Mainnet Configuration
MONAD_MAINNET_RPC = "https://rpc.monad.xyz"
MONAD_MAINNET_CHAIN_ID = 143

# Deploy wallet
PRIVATE_KEY = os.getenv("DEPLOY_PRIVATE_KEY")
if not PRIVATE_KEY:
    print("ERROR: DEPLOY_PRIVATE_KEY not set in .env")
    sys.exit(1)

def compile_contract():
    """Compile WorldGateV2.sol using solcx"""
    print("\n[1/4] Compiling contract...")
    
    try:
        import solcx
        
        # Install solc if needed
        try:
            solcx.get_solc_version()
        except:
            print("  Installing solc 0.8.20...")
            solcx.install_solc('0.8.20')
        
        solcx.set_solc_version('0.8.20')
        
        # Read contract source
        contract_path = Path(__file__).parent.parent / "contracts" / "src" / "WorldGateV2.sol"
        with open(contract_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Compile
        compiled = solcx.compile_source(
            source,
            output_values=['abi', 'bin'],
            solc_version='0.8.20'
        )
        
        # Get contract
        contract_key = '<stdin>:WorldGateV2'
        contract_data = compiled[contract_key]
        
        print(f"  Compiled successfully!")
        print(f"  Bytecode size: {len(contract_data['bin']) // 2} bytes")
        
        return contract_data['abi'], contract_data['bin']
        
    except ImportError:
        print("  ERROR: py-solc-x not installed. Run: pip install py-solc-x")
        sys.exit(1)

def deploy_contract(abi, bytecode):
    """Deploy contract to Monad mainnet"""
    print("\n[2/4] Deploying to Monad Mainnet...")
    
    from web3 import Web3
    from eth_account import Account
    
    # Connect to mainnet
    w3 = Web3(Web3.HTTPProvider(MONAD_MAINNET_RPC))
    
    if not w3.is_connected():
        print(f"  ERROR: Cannot connect to {MONAD_MAINNET_RPC}")
        sys.exit(1)
    
    print(f"  Connected to Monad Mainnet (Chain ID: {w3.eth.chain_id})")
    
    # Get deployer account
    account = Account.from_key(PRIVATE_KEY)
    deployer = account.address
    
    balance = w3.eth.get_balance(deployer)
    balance_mon = w3.from_wei(balance, 'ether')
    print(f"  Deployer: {deployer}")
    print(f"  Balance: {balance_mon} MON")
    
    if balance_mon < 0.1:
        print(f"  WARNING: Low balance! Deployment may fail.")
    
    # Create contract
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Build deploy transaction
    nonce = w3.eth.get_transaction_count(deployer)
    
    # Estimate gas
    try:
        gas_estimate = Contract.constructor().estimate_gas({'from': deployer})
        gas_limit = int(gas_estimate * 1.2)  # 20% buffer
    except:
        gas_limit = 2000000  # Fallback
    
    print(f"  Gas estimate: {gas_limit}")
    
    tx = Contract.constructor().build_transaction({
        'from': deployer,
        'nonce': nonce,
        'gas': gas_limit,
        'gasPrice': w3.eth.gas_price,
        'chainId': MONAD_MAINNET_CHAIN_ID
    })
    
    # Sign and send
    print(f"  Signing transaction...")
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    
    print(f"  Sending transaction...")
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"  TX Hash: {tx_hash.hex()}")
    
    # Wait for receipt
    print(f"  Waiting for confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    if receipt.status == 1:
        contract_address = receipt.contractAddress
        print(f"  SUCCESS! Contract deployed at: {contract_address}")
        print(f"  Gas used: {receipt.gasUsed}")
        return w3, contract_address
    else:
        print(f"  FAILED! Transaction reverted.")
        sys.exit(1)

def fund_reward_pool(w3, contract_address, abi, amount_mon=1.0):
    """Fund the reward pool"""
    print(f"\n[3/4] Funding reward pool with {amount_mon} MON...")
    
    from eth_account import Account
    
    account = Account.from_key(PRIVATE_KEY)
    deployer = account.address
    
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    # Build transaction
    nonce = w3.eth.get_transaction_count(deployer)
    
    tx = contract.functions.fundRewardPool().build_transaction({
        'from': deployer,
        'value': w3.to_wei(amount_mon, 'ether'),
        'nonce': nonce,
        'gas': 100000,
        'gasPrice': w3.eth.gas_price,
        'chainId': MONAD_MAINNET_CHAIN_ID
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    print(f"  TX Hash: {tx_hash.hex()}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    
    if receipt.status == 1:
        print(f"  Reward pool funded with {amount_mon} MON!")
        
        # Check pool balance
        pool = contract.functions.rewardPool().call()
        print(f"  Current reward pool: {w3.from_wei(pool, 'ether')} MON")
    else:
        print(f"  WARNING: Fund transaction failed")

def update_config(contract_address, abi):
    """Update .env and save ABI"""
    print("\n[4/4] Updating configuration...")
    
    # Save ABI
    abi_path = Path(__file__).parent.parent / "worldgate_v2_abi.json"
    with open(abi_path, 'w') as f:
        json.dump(abi, f, indent=2)
    print(f"  Saved ABI to: {abi_path}")
    
    # Save deployment info
    deployment_path = Path(__file__).parent.parent / "worldgate_v2_mainnet.json"
    deployment_info = {
        "network": "monad_mainnet",
        "chain_id": MONAD_MAINNET_CHAIN_ID,
        "rpc": MONAD_MAINNET_RPC,
        "contract_address": contract_address,
        "deployed_at": __import__('datetime').datetime.now().isoformat()
    }
    with open(deployment_path, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    print(f"  Saved deployment info to: {deployment_path}")
    
    # Update .env
    env_path = Path(__file__).parent.parent / ".env"
    with open(env_path, 'r', encoding='utf-8') as f:
        env_content = f.read()
    
    # Update RPC
    if "MONAD_RPC=" in env_content:
        env_content = env_content.replace(
            "MONAD_RPC=https://testnet-rpc.monad.xyz",
            f"MONAD_RPC={MONAD_MAINNET_RPC}"
        )
    
    # Update contract address
    if "WORLDGATE_ADDRESS=" in env_content:
        import re
        env_content = re.sub(
            r'WORLDGATE_ADDRESS=0x[a-fA-F0-9]+',
            f'WORLDGATE_ADDRESS={contract_address}',
            env_content
        )
    
    # Add chain ID if not present
    if "MONAD_CHAIN_ID=" not in env_content:
        env_content += f"\n# Monad Mainnet\nMONAD_CHAIN_ID={MONAD_MAINNET_CHAIN_ID}\n"
    
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)
    print(f"  Updated .env with mainnet config")
    
    print(f"\n{'='*60}")
    print(f"DEPLOYMENT COMPLETE!")
    print(f"{'='*60}")
    print(f"Contract: {contract_address}")
    print(f"Network: Monad Mainnet (Chain ID: {MONAD_MAINNET_CHAIN_ID})")
    print(f"Explorer: https://explorer.monad.xyz/address/{contract_address}")

def main():
    print("="*60)
    print("WorldGateV2 - Monad Mainnet Deployment")
    print("="*60)
    
    # Confirm
    print(f"\nThis will deploy to MONAD MAINNET using real MON!")
    print(f"Deployer: Check .env DEPLOY_PRIVATE_KEY")
    
    confirm = input("\nProceed? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Cancelled.")
        return
    
    # Compile
    abi, bytecode = compile_contract()
    
    # Deploy
    w3, contract_address = deploy_contract(abi, bytecode)
    
    # Fund reward pool (1 MON initial)
    fund_confirm = input("\nFund reward pool with 1 MON? (yes/no): ").strip().lower()
    if fund_confirm == 'yes':
        fund_reward_pool(w3, contract_address, abi, 1.0)
    
    # Update config
    update_config(contract_address, abi)

if __name__ == "__main__":
    main()
