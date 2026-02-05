#!/usr/bin/env python3
"""Deploy WorldGate using Hardhat-compiled bytecode for verification compatibility"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

# Load .env
load_dotenv(Path(__file__).parent.parent / '.env')

def deploy():
    # Load Hardhat artifacts
    artifact_path = Path(__file__).parent.parent / 'contracts' / 'artifacts' / 'src' / 'WorldGate.sol' / 'WorldGate.json'
    
    if not artifact_path.exists():
        print(f"ERROR: Artifact not found at {artifact_path}")
        print("Run 'npx hardhat compile' in contracts/ first")
        return
    
    with open(artifact_path) as f:
        artifact = json.load(f)
    
    bytecode = artifact['bytecode']
    abi = artifact['abi']
    
    print(f"Loaded artifact: {len(bytecode)} bytes bytecode")
    
    # Connect
    rpc = os.getenv('MONAD_RPC', 'https://testnet-rpc.monad.xyz')
    pk = os.getenv('DEPLOY_PRIVATE_KEY')
    
    if not pk:
        print("ERROR: DEPLOYER_PRIVATE_KEY not set")
        return
    
    w3 = Web3(Web3.HTTPProvider(rpc))
    print(f"Connected: {w3.is_connected()}")
    print(f"Chain ID: {w3.eth.chain_id}")
    
    account = Account.from_key(pk)
    print(f"Deployer: {account.address}")
    
    balance = w3.eth.get_balance(account.address)
    print(f"Balance: {w3.from_wei(balance, 'ether')} MON")
    
    # Check if have enough balance
    if balance < w3.to_wei(0.1, 'ether'):
        print("WARNING: Low balance, might not be enough for deployment")
    
    # Build deploy transaction
    WorldGate = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price
    
    print(f"\nNonce: {nonce}")
    print(f"Gas price: {w3.from_wei(gas_price, 'gwei')} gwei")
    
    # Estimate gas
    try:
        gas_estimate = WorldGate.constructor().estimate_gas({'from': account.address})
        print(f"Gas estimate: {gas_estimate}")
    except Exception as e:
        print(f"Gas estimation failed: {e}")
        gas_estimate = 2000000
    
    tx = WorldGate.constructor().build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': int(gas_estimate * 1.5),
        'gasPrice': gas_price,
        'chainId': w3.eth.chain_id
    })
    
    print(f"\nDeploying WorldGate (Hardhat-compiled)...")
    signed = w3.eth.account.sign_transaction(tx, pk)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"TX Hash: {tx_hash.hex()}")
    
    print("Waiting for receipt...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    if receipt.status == 1:
        contract_address = receipt.contractAddress
        print(f"\nSUCCESS!")
        print(f"Contract deployed at: {contract_address}")
        print(f"Gas used: {receipt.gasUsed}")
        print(f"Block: {receipt.blockNumber}")
        
        # Save deployment info
        deployment_info = {
            "address": contract_address,
            "tx_hash": tx_hash.hex(),
            "deployer": account.address,
            "chain_id": w3.eth.chain_id,
            "block_number": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
            "compiler": "hardhat-0.8.20-no-optimizer"
        }
        
        # Save to files
        deployment_path = Path(__file__).parent.parent / 'worldgate_deployment_v2.json'
        with open(deployment_path, 'w') as f:
            json.dump(deployment_info, f, indent=2)
        print(f"\nDeployment info saved to: {deployment_path}")
        
        # Update .env
        env_path = Path(__file__).parent.parent / '.env'
        with open(env_path, 'r') as f:
            env_content = f.read()
        
        if 'WORLDGATE_ADDRESS=' in env_content:
            lines = env_content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('WORLDGATE_ADDRESS='):
                    lines[i] = f'WORLDGATE_ADDRESS={contract_address}'
            env_content = '\n'.join(lines)
        else:
            env_content += f'\nWORLDGATE_ADDRESS={contract_address}\n'
        
        with open(env_path, 'w') as f:
            f.write(env_content)
        print(f"Updated .env with new contract address")
        
        print(f"\n{'='*50}")
        print(f"NEXT STEP: Verify the contract")
        print(f"{'='*50}")
        print(f"cd contracts")
        print(f"npx hardhat verify --network monad --contract src/WorldGate.sol:WorldGate {contract_address}")
        
    else:
        print(f"\nFAILED! Transaction reverted.")

if __name__ == "__main__":
    deploy()
