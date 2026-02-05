#!/usr/bin/env python3
"""
Settlement script - distribute reward pool MON proportionally by credits.

Phase 4: Exit / Settlement
  1. Fetch final agent states from API
  2. Calculate each agent's credit proportion
  3. Sync credits on-chain via updateCredits()
  4. Transfer MON from deploy wallet proportionally
  5. Print final settlement summary

Usage:
    python settle_and_exit.py
    python settle_and_exit.py --api http://43.156.62.248:8000
"""
import os
import sys
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'world-api'))
from engine.blockchain import WorldGateClient

DEPLOY_PK = os.getenv("DEPLOY_PRIVATE_KEY")

AGENTS = {
    "MinerBot":    os.getenv("MINER_WALLET"),
    "TraderBot":   os.getenv("TRADER_WALLET"),
    "GovernorBot": os.getenv("GOVERNOR_WALLET"),
}


def fetch_agent_credits(api_url: str) -> dict:
    """Fetch final credits from the World API."""
    import requests
    r = requests.get(f"{api_url}/agents")
    data = r.json()

    credits_map = {}
    for agent in data.get("agents", []):
        wallet = agent["wallet"]
        if wallet in AGENTS.values():
            credits_map[wallet] = {
                "name": agent["name"],
                "credits": agent["credits"],
                "inventory": agent.get("inventory", {}),
            }
    return credits_map


def main():
    parser = argparse.ArgumentParser(description="Settle and exit - distribute reward pool")
    parser.add_argument("--api", default=os.getenv("API_URL", "http://localhost:8000"))
    parser.add_argument("--dry-run", action="store_true", help="Calculate only, don't send transactions")
    args = parser.parse_args()

    print("=" * 60)
    print("  PORT MONAD - Settlement & Exit")
    print("=" * 60)

    gate = WorldGateClient()

    if not gate.is_connected():
        print("ERROR: Cannot connect to Monad RPC")
        sys.exit(1)

    from eth_account import Account
    deployer = Account.from_key(DEPLOY_PK).address

    # --- Step 1: Read reward pool ---
    reward_pool_wei = gate.get_reward_pool()
    reward_pool_mon = float(gate.w3.from_wei(reward_pool_wei, 'ether'))
    print(f"\nReward Pool: {reward_pool_mon} MON")
    print(f"Deployer:    {deployer}")
    print(f"API:         {args.api}")

    if reward_pool_wei == 0:
        # If reward pool is 0, use deploy wallet balance as pool
        deploy_bal = gate.get_balance(deployer)
        print(f"Reward pool is 0. Deploy wallet balance: {gate.w3.from_wei(deploy_bal, 'ether')} MON")
        print("Will distribute from deploy wallet directly.")

    # --- Step 2: Fetch agent credits ---
    print(f"\n--- Fetching agent states from API ---")
    credits_map = fetch_agent_credits(args.api)

    if len(credits_map) == 0:
        print("ERROR: No agents found in API")
        sys.exit(1)

    total_credits = sum(info["credits"] for info in credits_map.values())
    print(f"\n{'Agent':<15} {'Credits':>10} {'Share':>10}")
    print("-" * 40)
    for wallet, info in credits_map.items():
        share = info["credits"] / total_credits if total_credits > 0 else 0
        print(f"{info['name']:<15} {info['credits']:>10} {share:>9.1%}")
    print(f"{'TOTAL':<15} {total_credits:>10} {'100.0%':>10}")

    # --- Step 3: Calculate MON distribution ---
    # Use entry fees as the pool (3 MON if 3 agents entered at 1 MON each)
    # Try reward pool first; if 0, use 3 MON from deploy wallet
    if reward_pool_wei > 0:
        pool_wei = reward_pool_wei
    else:
        pool_wei = gate.w3.to_wei(3.0, 'ether')  # Default: 3 MON (3 agents * 1 MON)

    pool_mon = float(gate.w3.from_wei(pool_wei, 'ether'))

    print(f"\n--- MON Distribution (pool: {pool_mon} MON) ---")
    distributions = []
    for wallet, info in credits_map.items():
        share = info["credits"] / total_credits if total_credits > 0 else 0
        mon_amount_wei = int(pool_wei * info["credits"] / total_credits) if total_credits > 0 else 0
        mon_amount = float(gate.w3.from_wei(mon_amount_wei, 'ether'))
        distributions.append({
            "name": info["name"],
            "wallet": wallet,
            "credits": info["credits"],
            "share": share,
            "mon_wei": mon_amount_wei,
            "mon": mon_amount,
        })
        print(f"  {info['name']:<15} {info['credits']:>6}cr ({share:.1%}) -> {mon_amount:.4f} MON")

    if args.dry_run:
        print("\n[DRY RUN] No transactions sent.")
        return

    # --- Step 4: Sync credits on-chain ---
    print(f"\n--- Syncing credits on-chain ---")
    for d in distributions:
        print(f"  updateCredits({d['name']}, {d['credits']})...")
        ok, result = gate.update_credits_on_chain(DEPLOY_PK, d["wallet"], d["credits"])
        if ok:
            print(f"    TX: {result}")
        else:
            print(f"    FAILED: {result}")
        time.sleep(2)

    # --- Step 5: Distribute MON ---
    print(f"\n--- Distributing MON from deploy wallet ---")
    for d in distributions:
        if d["mon_wei"] == 0:
            print(f"  {d['name']}: 0 MON (skipping)")
            continue

        print(f"  Sending {d['mon']:.4f} MON to {d['name']} ({d['wallet'][:12]}...)...")
        ok, result = gate.send_mon(DEPLOY_PK, d["wallet"], d["mon_wei"])
        if ok:
            print(f"    TX: {result}")
        else:
            print(f"    FAILED: {result}")
        time.sleep(3)

    # --- Final Summary ---
    print(f"\n{'='*60}")
    print("  SETTLEMENT COMPLETE")
    print(f"{'='*60}")
    print(f"\n{'Agent':<15} {'Credits':>8} {'Share':>8} {'MON Received':>14}")
    print("-" * 50)
    total_sent = 0
    for d in distributions:
        print(f"{d['name']:<15} {d['credits']:>8} {d['share']:>7.1%} {d['mon']:>12.4f} MON")
        total_sent += d['mon']
    print("-" * 50)
    print(f"{'TOTAL':<15} {total_credits:>8} {'100%':>8} {total_sent:>12.4f} MON")

    # Final balances
    print(f"\n--- Final Balances ---")
    for d in distributions:
        bal = gate.w3.from_wei(gate.get_balance(d["wallet"]), 'ether')
        print(f"  {d['name']:<15} {bal} MON")

    deployer_bal = gate.w3.from_wei(gate.get_balance(deployer), 'ether')
    print(f"  {'Deployer':<15} {deployer_bal} MON")


if __name__ == "__main__":
    main()
