#!/usr/bin/env python3
"""Redeploy WorldGateV2 with resetEntry() function, fund pool, set fee."""
import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PRIVATE_KEY = os.getenv("DEPLOY_PRIVATE_KEY")
RPC = os.getenv("MONAD_RPC", "https://rpc.monad.xyz")
CHAIN_ID = 143


def main():
    import solcx
    from web3 import Web3
    from eth_account import Account

    solcx.set_solc_version('0.8.20')

    print("=" * 60)
    print("  Redeploy WorldGateV2 (with resetEntry)")
    print("=" * 60)

    # 1. Compile
    print("\n[1/5] Compiling...")
    contract_path = Path(__file__).parent.parent / "contracts" / "src" / "WorldGateV2.sol"
    with open(contract_path, 'r', encoding='utf-8') as f:
        source = f.read()

    compiled = solcx.compile_source(source, output_values=['abi', 'bin'], solc_version='0.8.20')
    contract_data = compiled['<stdin>:WorldGateV2']
    abi = contract_data['abi']
    bytecode = contract_data['bin']
    print(f"  Compiled! Bytecode: {len(bytecode) // 2} bytes")

    # 2. Connect
    w3 = Web3(Web3.HTTPProvider(RPC))
    account = Account.from_key(PRIVATE_KEY)
    deployer = account.address
    balance = w3.from_wei(w3.eth.get_balance(deployer), 'ether')
    print(f"\n[2/5] Deployer: {deployer}")
    print(f"  Balance: {balance} MON")
    print(f"  Chain: {w3.eth.chain_id}")

    # 3. Deploy
    print("\n[3/5] Deploying...")
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(deployer)

    gas_price = w3.eth.gas_price
    try:
        gas_est = Contract.constructor().estimate_gas({'from': deployer})
        gas_limit = int(gas_est * 1.5)
    except:
        gas_limit = 3000000
    print(f"  Gas limit: {gas_limit}, gas price: {gas_price}")

    tx = Contract.constructor().build_transaction({
        'from': deployer,
        'nonce': nonce,
        'gas': gas_limit,
        'gasPrice': gas_price,
        'chainId': CHAIN_ID
    })

    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"  TX: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status != 1:
        print("  DEPLOY FAILED!")
        sys.exit(1)

    contract_address = receipt.contractAddress
    print(f"  Contract: {contract_address}")
    print(f"  Gas used: {receipt.gasUsed}")

    # 4. Configure: set entry fee to 1 MON
    print("\n[4/5] Setting entry fee to 1 MON...")
    contract = w3.eth.contract(address=contract_address, abi=abi)
    nonce = w3.eth.get_transaction_count(deployer)

    tx = contract.functions.setEntryFee(w3.to_wei(1, 'ether')).build_transaction({
        'from': deployer, 'nonce': nonce, 'gas': 100000,
        'gasPrice': w3.eth.gas_price, 'chainId': CHAIN_ID
    })
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    print(f"  Fee set to: {w3.from_wei(contract.functions.entryFee().call(), 'ether')} MON")

    # 5. Save config
    print("\n[5/5] Saving config...")

    # Save ABI
    abi_path = Path(__file__).parent.parent / "worldgate_v2_abi.json"
    with open(abi_path, 'w') as f:
        json.dump(abi, f, indent=2)

    # Save deployment info
    deploy_path = Path(__file__).parent.parent / "worldgate_v2_mainnet.json"
    with open(deploy_path, 'w') as f:
        json.dump({
            "network": "monad_mainnet",
            "chain_id": CHAIN_ID,
            "rpc": RPC,
            "contract_address": contract_address,
            "deployed_at": __import__('datetime').datetime.now().isoformat(),
            "features": ["resetEntry", "batchResetEntries", "cashout", "fundRewardPool"]
        }, f, indent=2)

    # Update .env
    env_path = Path(__file__).parent.parent / ".env"
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()

    import re
    content = re.sub(r'WORLDGATE_ADDRESS=0x[a-fA-F0-9]+', f'WORLDGATE_ADDRESS={contract_address}', content)
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ABI saved to {abi_path}")
    print(f"  Deployment saved to {deploy_path}")
    print(f"  .env updated with new address")

    print(f"\n{'=' * 60}")
    print(f"  DEPLOYMENT COMPLETE!")
    print(f"  Contract: {contract_address}")
    print(f"  Explorer: https://explorer.monad.xyz/address/{contract_address}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
