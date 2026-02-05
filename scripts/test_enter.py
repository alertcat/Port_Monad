#!/usr/bin/env python3
"""
Enter all 3 agents into the world on-chain, then fund the reward pool.

Phase 2:
  1. Each agent calls enter() paying the entry fee (1 MON)
  2. Owner withdraws entry fees and funds the reward pool
     so the 3 MON are available for cashout at settlement

Usage:
    python test_enter.py
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'world-api'))
from engine.blockchain import WorldGateClient

DEPLOY_PK = os.getenv("DEPLOY_PRIVATE_KEY")

AGENTS = [
    ("MinerBot",    os.getenv("MINER_WALLET"),    os.getenv("MINER_PRIVATE_KEY")),
    ("TraderBot",   os.getenv("TRADER_WALLET"),    os.getenv("TRADER_PRIVATE_KEY")),
    ("GovernorBot", os.getenv("GOVERNOR_WALLET"),  os.getenv("GOVERNOR_PRIVATE_KEY")),
]


def main():
    print("=" * 60)
    print("  PORT MONAD - Enter World (On-Chain)")
    print("=" * 60)

    gate = WorldGateClient()

    if not gate.is_connected():
        print("ERROR: Cannot connect to Monad RPC")
        sys.exit(1)

    print(f"RPC:      {gate.rpc_url}")
    print(f"Contract: {gate.contract_address}")
    print(f"Chain ID: {gate.w3.eth.chain_id}")

    fee = gate.get_entry_fee()
    fee_mon = float(gate.w3.from_wei(fee, 'ether'))
    print(f"Entry fee: {fee_mon} MON")

    # --- Enter each agent ---
    results = []
    for name, wallet, pk in AGENTS:
        print(f"\n{'='*50}")
        print(f"  {name}")
        print(f"{'='*50}")
        print(f"Wallet:  {wallet}")

        balance = gate.get_balance(wallet)
        balance_mon = float(gate.w3.from_wei(balance, 'ether'))
        print(f"Balance: {balance_mon} MON")

        # Check if already entered
        # Temporarily disable DEBUG_MODE for real on-chain check
        old_debug = os.environ.get("DEBUG_MODE")
        os.environ["DEBUG_MODE"] = "false"

        is_active = gate.contract.functions.isActiveEntry(
            gate.w3.to_checksum_address(wallet)
        ).call()
        print(f"Active:  {is_active}")

        if old_debug:
            os.environ["DEBUG_MODE"] = old_debug

        if is_active:
            print("Already entered, skipping")
            results.append((name, True, "already entered"))
            continue

        if balance < fee:
            print(f"ERROR: Insufficient balance ({balance_mon} < {fee_mon})")
            results.append((name, False, "insufficient balance"))
            continue

        print(f"Calling enter() with {fee_mon} MON...")
        ok, result = gate.enter_world(pk)
        if ok:
            print(f"  SUCCESS! TX: {result}")
            results.append((name, True, result))
        else:
            print(f"  FAILED: {result}")
            results.append((name, False, result))

        time.sleep(3)  # wait between transactions

    # --- Fund reward pool ---
    print(f"\n{'='*60}")
    print("  Funding Reward Pool")
    print(f"{'='*60}")

    # The entry fees (3 MON) are now in the contract but NOT in rewardPool.
    # We need to: withdrawFees() -> then fundRewardPool() with that amount.
    # Or simpler: just fund from deploy wallet directly.

    contract_balance = gate.get_contract_balance()
    reward_pool = gate.get_reward_pool()
    fees_available = contract_balance - reward_pool

    print(f"Contract balance: {gate.w3.from_wei(contract_balance, 'ether')} MON")
    print(f"Reward pool:      {gate.w3.from_wei(reward_pool, 'ether')} MON")
    print(f"Fees available:   {gate.w3.from_wei(fees_available, 'ether')} MON")

    entered_count = sum(1 for _, ok, _ in results if ok)
    pool_amount = entered_count * fee  # fund pool with exactly the entry fees collected

    if pool_amount > 0 and fees_available > 0:
        # First withdraw fees to deploy wallet
        print(f"\nWithdrawing {gate.w3.from_wei(fees_available, 'ether')} MON fees to deploy wallet...")
        ok, result = gate.withdraw_fees(DEPLOY_PK)
        if ok:
            print(f"  TX: {result}")
            time.sleep(3)
        else:
            print(f"  Withdraw failed (may already be empty): {result}")

        # Then fund reward pool with the same amount
        print(f"Funding reward pool with {gate.w3.from_wei(pool_amount, 'ether')} MON...")
        ok, result = gate.fund_reward_pool(DEPLOY_PK, pool_amount)
        if ok:
            print(f"  TX: {result}")
            time.sleep(2)
            new_pool = gate.get_reward_pool()
            print(f"  New reward pool: {gate.w3.from_wei(new_pool, 'ether')} MON")
        else:
            print(f"  FAILED: {result}")
    else:
        print("No new fees to move to reward pool")

    # --- Summary ---
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    for name, ok, detail in results:
        status = "ENTERED" if ok else "FAILED"
        print(f"  {name:<15} {status:<10} {detail[:40]}")

    pool = gate.get_reward_pool()
    print(f"\nReward pool: {gate.w3.from_wei(pool, 'ether')} MON")
    print(f"Entry fee:   {gate.w3.from_wei(gate.get_entry_fee(), 'ether')} MON")
    print(f"\nAll agents entered! Run the game simulation next.")


if __name__ == "__main__":
    main()
