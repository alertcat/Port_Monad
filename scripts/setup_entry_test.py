#!/usr/bin/env python3
"""
Setup script for entry/exit MON flow test.

Phase 1: Preparation
  1. Set entry fee to 1 MON (via owner setEntryFee)
  2. Send 2 MON from deploy wallet to each agent wallet
  3. Verify all balances

Usage:
    python setup_entry_test.py
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'world-api'))
from engine.blockchain import WorldGateClient

# Config
DEPLOY_PK = os.getenv("DEPLOY_PRIVATE_KEY")
ENTRY_FEE_MON = 1.0   # New entry fee
SEND_AMOUNT_MON = 2.0  # Amount to send to each agent

AGENTS = {
    "MinerBot": {
        "wallet": os.getenv("MINER_WALLET"),
        "pk": os.getenv("MINER_PRIVATE_KEY"),
    },
    "TraderBot": {
        "wallet": os.getenv("TRADER_WALLET"),
        "pk": os.getenv("TRADER_PRIVATE_KEY"),
    },
    "GovernorBot": {
        "wallet": os.getenv("GOVERNOR_WALLET"),
        "pk": os.getenv("GOVERNOR_PRIVATE_KEY"),
    },
}


def main():
    print("=" * 60)
    print("  PORT MONAD - Entry Test Setup")
    print("=" * 60)

    gate = WorldGateClient()

    if not gate.is_connected():
        print("ERROR: Cannot connect to Monad RPC")
        sys.exit(1)

    from eth_account import Account
    deployer = Account.from_key(DEPLOY_PK).address
    deploy_balance = gate.w3.from_wei(gate.get_balance(deployer), 'ether')
    print(f"\nDeployer: {deployer}")
    print(f"Balance:  {deploy_balance} MON")
    print(f"Contract: {gate.contract_address}")

    # Check deployer has enough MON
    needed = SEND_AMOUNT_MON * len(AGENTS) + 0.1  # buffer for gas
    if float(deploy_balance) < needed:
        print(f"\nERROR: Need at least {needed} MON, have {deploy_balance}")
        sys.exit(1)

    # --- Step 1: Set entry fee ---
    current_fee = gate.get_entry_fee()
    current_fee_mon = float(gate.w3.from_wei(current_fee, 'ether'))
    print(f"\n--- Step 1: Set Entry Fee ---")
    print(f"Current fee: {current_fee_mon} MON")

    if abs(current_fee_mon - ENTRY_FEE_MON) > 0.001:
        new_fee_wei = gate.w3.to_wei(ENTRY_FEE_MON, 'ether')
        print(f"Setting entry fee to {ENTRY_FEE_MON} MON...")
        ok, result = gate.set_entry_fee(DEPLOY_PK, new_fee_wei)
        if ok:
            print(f"  TX: {result}")
            time.sleep(2)
            # Verify
            new_fee = gate.w3.from_wei(gate.get_entry_fee(), 'ether')
            print(f"  Verified new fee: {new_fee} MON")
        else:
            print(f"  FAILED: {result}")
            sys.exit(1)
    else:
        print(f"Fee already set to {ENTRY_FEE_MON} MON, skipping")

    # --- Step 2: Send MON to agents ---
    print(f"\n--- Step 2: Send {SEND_AMOUNT_MON} MON to each agent ---")
    amount_wei = gate.w3.to_wei(SEND_AMOUNT_MON, 'ether')

    for name, info in AGENTS.items():
        wallet = info["wallet"]
        balance = gate.w3.from_wei(gate.get_balance(wallet), 'ether')
        print(f"\n{name} ({wallet[:10]}...)")
        print(f"  Current balance: {balance} MON")

        if float(balance) >= SEND_AMOUNT_MON:
            print(f"  Already has >= {SEND_AMOUNT_MON} MON, skipping")
            continue

        print(f"  Sending {SEND_AMOUNT_MON} MON...")
        ok, result = gate.send_mon(DEPLOY_PK, wallet, amount_wei)
        if ok:
            print(f"  TX: {result}")
            time.sleep(2)
            new_balance = gate.w3.from_wei(gate.get_balance(wallet), 'ether')
            print(f"  New balance: {new_balance} MON")
        else:
            print(f"  FAILED: {result}")

    # --- Step 3: Verify ---
    print(f"\n--- Step 3: Final Verification ---")
    print(f"{'Agent':<15} {'Wallet':<15} {'Balance':>12}")
    print("-" * 45)
    for name, info in AGENTS.items():
        bal = gate.w3.from_wei(gate.get_balance(info["wallet"]), 'ether')
        print(f"{name:<15} {info['wallet'][:12]}... {bal:>10} MON")

    fee = gate.w3.from_wei(gate.get_entry_fee(), 'ether')
    print(f"\nEntry fee: {fee} MON")
    print(f"\nSetup complete! Run test_enter.py next to enter the world.")


if __name__ == "__main__":
    main()
