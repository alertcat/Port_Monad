#!/usr/bin/env python3
"""Deploy WorldGate contract using web3.py (no Foundry needed)"""
import os
import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def compile_contract():
    """Compile WorldGate.sol using py-solc-x"""
    print("Compiling contract...")
    
    import solcx
    
    # Install solc if not present
    try:
        solcx.get_solc_version()
    except:
        print("Installing solc 0.8.20...")
        solcx.install_solc('0.8.20')
    
    solcx.set_solc_version('0.8.20')
    
    contract_path = Path(__file__).parent.parent / 'contracts' / 'src' / 'WorldGate.sol'
    
    with open(contract_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    compiled = solcx.compile_source(
        source,
        output_values=['abi', 'bin'],
        solc_version='0.8.20'
    )
    
    # Get the contract
    contract_id = '<stdin>:WorldGate'
    contract_interface = compiled[contract_id]
    
    bytecode = contract_interface['bin']
    abi = contract_interface['abi']
    
    print(f"Compiled successfully!")
    print(f"Bytecode size: {len(bytecode)} bytes")
    
    return bytecode, abi

def deploy():
    """Deploy WorldGate contract"""
    from web3 import Web3
    from eth_account import Account
    
    # Compile
    bytecode, abi = compile_contract()
    
    # Connect to Monad testnet
    rpc_url = os.getenv('MONAD_RPC', 'https://testnet-rpc.monad.xyz')
    print(f"\nConnecting to: {rpc_url}")
    
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print(f"ERROR: Cannot connect to {rpc_url}")
        print("Please check your internet connection and RPC URL")
        return None
    
    print(f"Connected! Chain ID: {w3.eth.chain_id}")
    
    # Load deploy wallet
    private_key = os.getenv('DEPLOY_PRIVATE_KEY')
    if not private_key:
        print("ERROR: DEPLOY_PRIVATE_KEY not set in .env")
        return None
    
    account = Account.from_key(private_key)
    deployer = account.address
    
    balance = w3.eth.get_balance(deployer)
    balance_eth = w3.from_wei(balance, 'ether')
    print(f"\nDeployer: {deployer}")
    print(f"Balance: {balance_eth} MON")
    
    if balance == 0:
        print("ERROR: Deployer has no balance!")
        print("Please fund your wallet with testnet MON")
        return None
    
    # Create contract instance
    WorldGate = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Build transaction
    nonce = w3.eth.get_transaction_count(deployer)
    
    # Get gas price
    try:
        gas_price = w3.eth.gas_price
    except:
        gas_price = w3.to_wei(50, 'gwei')  # Default
    
    print(f"\nGas price: {w3.from_wei(gas_price, 'gwei')} gwei")
    
    # Build deploy transaction
    print("Building transaction...")
    tx = WorldGate.constructor().build_transaction({
        'from': deployer,
        'nonce': nonce,
        'gas': 2000000,  # Increased gas limit for deployment
        'gasPrice': gas_price,
        'chainId': w3.eth.chain_id
    })
    
    # Sign and send
    print("Signing transaction...")
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    
    print("Sending transaction...")
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Transaction hash: {tx_hash.hex()}")
    
    # Wait for receipt
    print("Waiting for confirmation (may take up to 60 seconds)...")
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    except Exception as e:
        print(f"Timeout waiting for receipt: {e}")
        print(f"Check transaction status at explorer with hash: {tx_hash.hex()}")
        return None
    
    if receipt.status == 1:
        contract_address = receipt.contractAddress
        print("\n" + "=" * 60)
        print("DEPLOYMENT SUCCESSFUL!")
        print("=" * 60)
        print(f"Contract Address: {contract_address}")
        print(f"Transaction Hash: {tx_hash.hex()}")
        print(f"Gas Used: {receipt.gasUsed}")
        print(f"Block Number: {receipt.blockNumber}")
        print("=" * 60)
        
        # Save to file
        deployment_info = {
            'address': contract_address,
            'tx_hash': tx_hash.hex(),
            'deployer': deployer,
            'chain_id': w3.eth.chain_id,
            'block_number': receipt.blockNumber,
            'gas_used': receipt.gasUsed,
            'abi': abi
        }
        
        output_path = Path(__file__).parent.parent / 'worldgate_deployment.json'
        with open(output_path, 'w') as f:
            json.dump(deployment_info, f, indent=2)
        
        print(f"\nDeployment info saved to: {output_path}")
        
        # Also save ABI separately for easy use
        abi_path = Path(__file__).parent.parent / 'worldgate_abi.json'
        with open(abi_path, 'w') as f:
            json.dump(abi, f, indent=2)
        print(f"ABI saved to: {abi_path}")
        
        print(f"\n>>> Update your .env file:")
        print(f"WORLDGATE_ADDRESS={contract_address}")
        
        return contract_address
    else:
        print("\nERROR: Transaction failed!")
        print(f"Receipt: {receipt}")
        return None

def verify_deployment(address: str = None):
    """Verify a deployed contract"""
    from web3 import Web3
    
    if not address:
        address = os.getenv('WORLDGATE_ADDRESS')
    
    if not address:
        print("No contract address provided")
        return
    
    rpc_url = os.getenv('MONAD_RPC', 'https://testnet-rpc.monad.xyz')
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    # Load ABI
    abi_path = Path(__file__).parent.parent / 'worldgate_abi.json'
    if abi_path.exists():
        with open(abi_path) as f:
            abi = json.load(f)
    else:
        print("ABI file not found, using minimal ABI")
        abi = [
            {"inputs": [], "name": "entryFee", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "entryDuration", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "owner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
        ]
    
    contract = w3.eth.contract(address=address, abi=abi)
    
    print(f"\nVerifying contract at: {address}")
    print("-" * 40)
    
    try:
        entry_fee = contract.functions.entryFee().call()
        entry_duration = contract.functions.entryDuration().call()
        owner = contract.functions.owner().call()
        
        print(f"Entry Fee: {w3.from_wei(entry_fee, 'ether')} MON")
        print(f"Entry Duration: {entry_duration // 86400} days")
        print(f"Owner: {owner}")
        print("\nContract is working correctly!")
    except Exception as e:
        print(f"Error reading contract: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Deploy or verify WorldGate contract')
    parser.add_argument('--verify', type=str, help='Verify contract at address')
    args = parser.parse_args()
    
    if args.verify:
        verify_deployment(args.verify)
    else:
        deploy()
