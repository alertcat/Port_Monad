#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Port Monad - Full Integration Test

Complete game lifecycle with:
  Phase 1: On-chain setup (RESET entries, set fee, send MON, enter world, fund pool)
  Phase 2: LLM-powered game with Moltbook comment replies (NOT dry-run)
  Phase 3: On-chain settlement (sync credits, agents self-cashout)

Usage:
    python run_full_game.py --post-id <MOLTBOOK_POST_ID>
    python run_full_game.py --post-id a017b972-d899-4daa-8216-8ce4008ff2d6 --rounds 10 --cycles 2
"""
import os
import sys
import asyncio
import json
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent / 'world-api'))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

import aiohttp
from engine.blockchain import WorldGateClient
from eth_account import Account

# =============================================================================
# Configuration
# =============================================================================
API_URL = os.getenv("API_URL", "http://localhost:8000")
DEPLOY_PK = os.getenv("DEPLOY_PRIVATE_KEY")
ENTRY_FEE_MON = 1.0

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3-flash-preview")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MOLTBOOK_HOST_KEY = os.getenv("MOLTBOOK_HOST_KEY", "")

AGENTS_CONFIG = [
    {
        "name": "MinerBot",
        "wallet": os.getenv("MINER_WALLET"),
        "pk": os.getenv("MINER_PRIVATE_KEY"),
        "moltbook_key": os.getenv("MOLTBOOK_MINER_KEY", ""),
        "personality": (
            "You are MinerBot, a RUTHLESS iron-mining machine. "
            "You believe strength rules Port Monad. You harvest iron aggressively and "
            "RAID anyone who dares enter your territory with goods. "
            "You talk tough: 'Time to dig... into your pockets!' 'Ore belongs to the strong!' "
            "You LOVE combat and raiding. If someone is nearby with items, your instinct is to RAID them."
        )
    },
    {
        "name": "TraderBot",
        "wallet": os.getenv("TRADER_WALLET"),
        "pk": os.getenv("TRADER_PRIVATE_KEY"),
        "moltbook_key": os.getenv("MOLTBOOK_TRADER_KEY", ""),
        "personality": (
            "You are TraderBot, a master NEGOTIATOR and market manipulator. "
            "You NEVER fight - violence is for brutes. You win through clever DEALS. "
            "You harvest wood from the forest and make shrewd trades. "
            "When you see another agent, you ALWAYS try to NEGOTIATE - buy their resources cheap "
            "or sell yours at premium prices. You talk in profit margins: "
            "'That's a 40% ROI!' 'Let me make you an offer you can't refuse.' "
            "You PREFER negotiation over any other action when someone is nearby."
        )
    },
    {
        "name": "GovernorBot",
        "wallet": os.getenv("GOVERNOR_WALLET"),
        "pk": os.getenv("GOVERNOR_PRIVATE_KEY"),
        "moltbook_key": os.getenv("MOLTBOOK_GOVERNOR_KEY", ""),
        "personality": (
            "You are GovernorBot, the self-appointed GOVERNOR of Port Monad. "
            "You patrol ALL regions to maintain order. You harvest fish at the dock. "
            "You PUNISH low-reputation agents by RAIDING them (justice raids). "
            "You NEGOTIATE fair trades with good-reputation agents. "
            "You EXPLORE by visiting different regions every few turns. "
            "You speak like a politician: 'For the good of all agents!' "
            "'Justice must be served!' 'Order in the port!' "
            "You are the ONLY agent who actively moves between all 4 regions."
        )
    },
]


# =============================================================================
# LLM Client
# =============================================================================
class LLMClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.enabled = bool(api_key)

    async def generate(self, session, system_prompt, user_prompt, max_tokens=200):
        if not self.enabled:
            return None
        try:
            async with session.post(OPENROUTER_URL, headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://portmonad.world",
                "X-Title": "Port Monad Agent"
            }, json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": max_tokens, "temperature": 0.8
            }) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                return None
        except:
            return None


# =============================================================================
# Moltbook Client (comment-only, no new posts)
# =============================================================================
class MoltbookPoster:
    BASE_URL = "https://www.moltbook.com/api/v1"

    def __init__(self, api_key, name):
        self.api_key = api_key
        self.name = name
        self.enabled = bool(api_key)

    async def comment(self, session, post_id, content):
        if not self.enabled or not post_id:
            return False
        try:
            async with session.post(f"{self.BASE_URL}/posts/{post_id}/comments", headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }, json={"content": content}) as resp:
                ok = resp.status in [200, 201]
                if ok:
                    print(f"  [Moltbook] {self.name}: Comment OK")
                else:
                    print(f"  [Moltbook] {self.name}: Comment FAIL ({resp.status})")
                return ok
        except Exception as e:
            print(f"  [Moltbook] {self.name}: Error - {e}")
            return False


# =============================================================================
# Phase 1: On-Chain Setup (RESET + ENTER + FUND)
# =============================================================================
def phase1_on_chain_setup(gate: WorldGateClient):
    """Reset entries, send MON, re-enter world, fund reward pool."""
    print("\n" + "=" * 70)
    print("  PHASE 1: ON-CHAIN SETUP (FRESH ROUND)")
    print("=" * 70)

    deployer = Account.from_key(DEPLOY_PK).address
    print(f"Deployer: {deployer}")
    print(f"Balance:  {gate.w3.from_wei(gate.get_balance(deployer), 'ether')} MON")
    print(f"Contract: {gate.contract_address}")

    # Step 1: Set entry fee to 1 MON
    current_fee = float(gate.w3.from_wei(gate.get_entry_fee(), 'ether'))
    if abs(current_fee - ENTRY_FEE_MON) > 0.001:
        print(f"\nSetting entry fee to {ENTRY_FEE_MON} MON (was {current_fee})...")
        ok, r = gate.set_entry_fee(DEPLOY_PK, gate.w3.to_wei(ENTRY_FEE_MON, 'ether'))
        print(f"  {'OK' if ok else 'FAIL'}: {r}")
        time.sleep(3)
    else:
        print(f"Entry fee already {ENTRY_FEE_MON} MON")

    # Step 2: RESET all agent entries via batchResetEntries (owner only)
    wallets = [a["wallet"] for a in AGENTS_CONFIG]
    print(f"\nResetting entry status for {len(wallets)} agents...")
    ok, r = gate.batch_reset_entries(DEPLOY_PK, wallets)
    print(f"  {'OK' if ok else 'FAIL'}: {r}")
    time.sleep(3)

    # Verify all entries are now inactive
    for agent in AGENTS_CONFIG:
        w = gate.w3.to_checksum_address(agent["wallet"])
        is_active = gate.contract.functions.isActiveEntry(w).call()
        print(f"  {agent['name']}: isActive = {is_active}")

    # Step 3: Each agent enters (pays 1 MON)
    fee_wei = gate.get_entry_fee()
    needed_wei = fee_wei + gate.w3.to_wei(0.1, 'ether')

    for agent in AGENTS_CONFIG:
        wallet = agent["wallet"]
        name = agent["name"]
        pk = agent["pk"]
        balance = gate.get_balance(wallet)

        print(f"\n{name} ({wallet[:12]}...)")
        print(f"  Balance: {gate.w3.from_wei(balance, 'ether')} MON")

        if balance < needed_wei:
            send_amount = needed_wei - balance + gate.w3.to_wei(0.05, 'ether')
            print(f"  Topping up {gate.w3.from_wei(send_amount, 'ether')} MON...")
            ok, r = gate.send_mon(DEPLOY_PK, wallet, send_amount)
            print(f"    {'OK' if ok else 'FAIL'}: {r}")
            time.sleep(3)

        print(f"  enter() paying {ENTRY_FEE_MON} MON (force=True)...")
        ok, r = gate.enter_world(pk, force=True)
        print(f"    {'OK' if ok else 'FAIL'}: {r}")
        time.sleep(3)

    # Step 4: Move entry fees to reward pool
    contract_bal = gate.get_contract_balance()
    current_pool = gate.get_reward_pool()
    fees = contract_bal - current_pool

    print(f"\nContract balance: {gate.w3.from_wei(contract_bal, 'ether')} MON")
    print(f"Reward pool:      {gate.w3.from_wei(current_pool, 'ether')} MON")
    print(f"Entry fees:       {gate.w3.from_wei(fees, 'ether')} MON")

    # Withdraw fees, then fund pool to 3 MON
    if fees > 0:
        print("Withdrawing fees to deployer...")
        ok, r = gate.withdraw_fees(DEPLOY_PK)
        print(f"  {'OK' if ok else 'FAIL'}: {r}")
        time.sleep(3)

    target_pool = gate.w3.to_wei(len(AGENTS_CONFIG) * ENTRY_FEE_MON, 'ether')
    current_pool = gate.get_reward_pool()
    pool_needed = target_pool - current_pool

    if pool_needed > 0:
        print(f"Funding pool with {gate.w3.from_wei(pool_needed, 'ether')} MON...")
        ok, r = gate.fund_reward_pool(DEPLOY_PK, pool_needed)
        print(f"  {'OK' if ok else 'FAIL'}: {r}")
        time.sleep(2)

    final_pool = gate.get_reward_pool()
    print(f"\nFinal reward pool: {gate.w3.from_wei(final_pool, 'ether')} MON")
    print("Phase 1 complete!")


# =============================================================================
# Phase 2: LLM Game + Moltbook Comments (reply to existing post)
# =============================================================================
async def phase2_game(rounds, cycles, cycle_wait, post_id):
    """Run LLM-powered game, post comments to existing Moltbook post."""
    print("\n" + "=" * 70)
    print("  PHASE 2: LLM GAME + MOLTBOOK COMMENTS")
    print("=" * 70)

    llm = LLMClient(OPENROUTER_API_KEY)
    host_mb = MoltbookPoster(MOLTBOOK_HOST_KEY, "SignalForge")
    bot_mbs = {a["name"]: MoltbookPoster(a["moltbook_key"], a["name"]) for a in AGENTS_CONFIG}

    print(f"LLM:      {'ENABLED' if llm.enabled else 'DISABLED'}")
    print(f"Post ID:  {post_id}")
    print(f"Rounds:   {rounds} x {cycles} cycles")

    async with aiohttp.ClientSession() as session:
        # Reset game state via API
        print("\nResetting game state...")
        await session.post(f"{API_URL}/debug/full_reset")
        await asyncio.sleep(1)

        # Post game-start comment
        async with session.get(f"{API_URL}/world/state") as resp:
            ws = await resp.json()
        prices = ws.get("market_prices", {})

        start_comment = (
            f"**NEW GAME ROUND STARTED!** ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
            f"Entry fee: {ENTRY_FEE_MON} MON per agent | Reward pool: {len(AGENTS_CONFIG) * ENTRY_FEE_MON} MON\n"
            f"Market: Iron={prices.get('iron')}, Wood={prices.get('wood')}, Fish={prices.get('fish')}\n\n"
            "3 AI agents (Gemini 3 Flash) competing. Settlement by credits ratio!"
        )
        await host_mb.comment(session, post_id, start_comment)

        total_comments = 1

        for cycle in range(cycles):
            print(f"\n{'=' * 70}")
            print(f"  CYCLE {cycle + 1}/{cycles}")
            print(f"{'=' * 70}")

            # Run game rounds
            for rnd in range(rounds):
                tick = cycle * rounds + rnd
                print(f"\n  Round {rnd + 1}/{rounds} (Tick {tick})")

                async with session.get(f"{API_URL}/world/state") as resp:
                    world_state = await resp.json()

                # Fetch ALL agents so we know who is where
                async with session.get(f"{API_URL}/agents") as resp:
                    all_agents_data = (await resp.json()).get("agents", [])

                events = world_state.get("active_events", [])
                if events:
                    for ev in events:
                        desc = ev.get("description", ev.get("type", "?"))
                        print(f"    EVENT: {desc} (remaining: {ev.get('remaining', '?')} ticks)")

                for agent in AGENTS_CONFIG:
                    wallet = agent["wallet"]
                    name = agent["name"]

                    async with session.get(f"{API_URL}/agent/{wallet}/state") as resp:
                        state = await resp.json()
                    if "error" in state:
                        continue

                    action_data = await _llm_decide(
                        llm, session, agent, state, world_state, all_agents_data
                    )
                    if not action_data:
                        continue

                    try:
                        async with session.post(f"{API_URL}/action",
                            json={"actor": wallet, **action_data},
                            headers={"X-Wallet": wallet}) as resp:
                            result = await resp.json()
                            msg = result.get("message", "")[:80]
                            if result.get("success"):
                                print(f"    {name}: {msg}")
                            else:
                                print(f"    {name}: FAIL - {msg}")
                    except Exception as e:
                        print(f"    {name}: ERROR - {e}")

                await session.post(f"{API_URL}/debug/advance_tick")

            # End of cycle: host posts leaderboard comment
            async with session.get(f"{API_URL}/agents") as resp:
                agents_data = await resp.json()
            async with session.get(f"{API_URL}/world/state") as resp:
                ws = await resp.json()
            prices = ws.get("market_prices", {})
            tick_now = ws.get("tick", 0)

            lines = [f"**Cycle {cycle + 1} Complete (Tick {tick_now})**\n"]
            lines.append(f"Market: Iron={prices.get('iron')}, Wood={prices.get('wood')}, Fish={prices.get('fish')}\n")
            lines.append("**Standings:**")
            for a in agents_data.get("agents", []):
                inv = sum(a.get("inventory", {}).values())
                lines.append(f"- {a['name']}: {a['credits']}c ({inv} items, rep:{a.get('reputation', '?')})")

            await host_mb.comment(session, post_id, "\n".join(lines))
            total_comments += 1

            # Bot personality comments
            for agent in AGENTS_CONFIG:
                await asyncio.sleep(random.randint(3, 8))
                name = agent["name"]
                async with session.get(f"{API_URL}/agent/{agent['wallet']}/state") as resp:
                    state = await resp.json()

                comment = await _llm_comment(llm, session, agent, state, ws, tick_now)
                if await bot_mbs[name].comment(session, post_id, comment):
                    total_comments += 1

            # Wait between cycles
            if cycle < cycles - 1:
                print(f"\n  Waiting {cycle_wait}s...")
                await asyncio.sleep(cycle_wait)

        # Settlement comment
        async with session.get(f"{API_URL}/agents") as resp:
            final = await resp.json()
        total_cr = sum(a["credits"] for a in final.get("agents", []))
        pool_mon = len(AGENTS_CONFIG) * ENTRY_FEE_MON
        lines = ["**GAME OVER - Final Settlement**\n"]
        for a in final.get("agents", []):
            share = a["credits"] / total_cr if total_cr > 0 else 0
            mon = pool_mon * share
            lines.append(f"- {a['name']}: {a['credits']}c ({share:.1%}) -> {mon:.4f} MON")
        lines.append(f"\nPool: {pool_mon} MON distributed by credits!")
        await host_mb.comment(session, post_id, "\n".join(lines))

        print(f"\nMoltbook: https://www.moltbook.com/post/{post_id}")
        print(f"Total comments: {total_comments}")


async def _llm_decide(llm, session, agent, state, world_state, all_agents_data):
    """LLM decides action with rich context and distinct personality."""
    region = state.get("region", "dock")
    energy = state.get("energy", 0)
    credits = state.get("credits", 0)
    reputation = state.get("reputation", 100)
    inventory = state.get("inventory", {})
    prices = world_state.get("market_prices", {})
    events = world_state.get("active_events", [])
    inv_str = ", ".join(f"{k}:{v}" for k, v in inventory.items() if v > 0) or "empty"
    inv_total = sum(inventory.values())

    # Find other agents in the same region
    my_wallet = agent["wallet"]
    nearby = []
    all_others = []
    for a in all_agents_data:
        if a["wallet"] == my_wallet:
            continue
        info = f"{a['name']}({a['wallet'][:10]}...) region={a['region']} credits={a['credits']} rep={a.get('reputation',100)}"
        all_others.append(info)
        if a["region"] == region:
            inv_items = sum(a.get("inventory", {}).values())
            nearby.append({
                "name": a["name"],
                "wallet": a["wallet"],
                "credits": a["credits"],
                "items": inv_items,
                "reputation": a.get("reputation", 100)
            })

    nearby_str = ""
    if nearby:
        lines = []
        for n in nearby:
            lines.append(f"  - {n['name']} (wallet: {n['wallet']}) credits={n['credits']} items={n['items']} rep={n['reputation']}")
        nearby_str = "AGENTS IN YOUR REGION (you can RAID or NEGOTIATE with them):\n" + "\n".join(lines)
    else:
        nearby_str = "NO other agents in your region right now."

    events_str = "None"
    if events:
        ev_lines = [f"  - {e.get('description', e.get('type','?'))} (remaining: {e.get('remaining','?')} ticks)" for e in events]
        events_str = "\n".join(ev_lines)

    # Per-agent strategy personality
    strategy = _get_agent_strategy(agent["name"], credits, energy, inv_total, nearby)

    system_prompt = f"""{agent['personality']}

GAME: Port Monad - a competitive port city where 3 AI agents fight for the most credits.
The agent with the most credits at the end wins the biggest share of the 3 MON reward pool!

LOCATIONS: dock(fish), mine(iron), forest(wood), market(sell only).

ACTIONS (respond with EXACTLY ONE JSON object, nothing else):

1. MOVE: {{"action":"move","params":{{"target":"mine"}}}}
   Cost: 5 AP. Targets: dock, mine, forest, market.

2. HARVEST: {{"action":"harvest","params":{{}}}}
   Cost: 10 AP. Must be at dock/mine/forest. Gets resources.

3. SELL: {{"action":"place_order","params":{{"resource":"iron","side":"sell","quantity":5}}}}
   Cost: 3 AP. Must be at market. resource=iron/wood/fish, quantity=integer.

4. REST: {{"action":"rest","params":{{}}}}
   Cost: 0 AP. Recovers energy.

5. RAID: {{"action":"raid","params":{{"target_wallet":"0xABC123..."}}}}
   Cost: 25 AP. COMBAT! Steal items from target. Must be in same NON-market region.
   Win chance higher if you have more reputation. Winner gets items, loser loses items.

6. NEGOTIATE: {{"action":"negotiate","params":{{"target_wallet":"0xABC123...","offer_type":"credits","offer_amount":50,"request_resource":"iron","request_amount":3}}}}
   Cost: 15 AP. Trade deal with another agent. Must be in same region.

PRICES: Iron={prices.get('iron',15)}, Wood={prices.get('wood',12)}, Fish={prices.get('fish',8)}
ACTIVE EVENTS: {events_str}

{strategy}

OUTPUT: One JSON object ONLY. No text, no markdown, no explanation."""

    user_prompt = f"""YOUR STATUS:
- Location: {region}
- AP: {energy}
- Credits: {credits}
- Reputation: {reputation}
- Inventory: {inv_str} ({inv_total} items)

{nearby_str}

ALL AGENTS:
{chr(10).join(all_others) if all_others else '(no others)'}

What is your action? (JSON only)"""

    if llm.enabled:
        response = await llm.generate(session, system_prompt, user_prompt, 400)
        if response:
            parsed = _parse_llm_json(response)
            if parsed:
                return parsed

    # Fallback: rule-based
    return _fallback_action(agent["name"], state, world_state, nearby)


def _get_agent_strategy(name, credits, energy, inv_total, nearby):
    """Return distinct strategy instructions per agent type."""
    if name == "MinerBot":
        raid_hint = ""
        if nearby:
            richest = max(nearby, key=lambda n: n["items"])
            if richest["items"] >= 3:
                raid_hint = f"\nRIGHT NOW: {richest['name']} is nearby with {richest['items']} items - consider RAIDING them!"
        return f"""YOUR STRATEGY (MinerBot - Aggressive Miner):
- You are a TOUGH miner who doesn't back down from a fight.
- Primary: Go to mine, harvest iron, sell at market.
- COMBAT PRIORITY: If another agent is in your region with 3+ items AND you have 25+ AP, RAID them!
- You believe resources belong to whoever is strongest.
- If AP < 15, REST. If inventory >= 4, go sell at market.
- You PREFER raiding over harvesting when targets are available.{raid_hint}"""

    elif name == "TraderBot":
        negotiate_hint = ""
        if nearby:
            target = nearby[0]
            negotiate_hint = f"\nRIGHT NOW: {target['name']} is nearby - consider NEGOTIATING a trade deal!"
        return f"""YOUR STRATEGY (TraderBot - Master Negotiator):
- You are a shrewd DIPLOMAT who makes deals, not war.
- Primary: Harvest wood from forest, sell at market for profit.
- NEGOTIATION PRIORITY: If another agent is in your region, ALWAYS try to NEGOTIATE first!
  Offer credits for their resources (buy low), or offer resources for credits (sell high).
- You calculate profit margins and make smart trades.
- NEVER raid - it damages reputation. You win through DEALS.
- If alone, harvest or move to where others are to negotiate.
- If AP < 15, REST. If inventory >= 3, go sell.{negotiate_hint}"""

    else:  # GovernorBot
        justice_hint = ""
        if nearby:
            low_rep = [n for n in nearby if n["reputation"] < 95]
            if low_rep:
                target = low_rep[0]
                justice_hint = f"\nJUSTICE TARGET: {target['name']} (rep={target['reputation']}) is nearby with low reputation - RAID them to punish!"
        return f"""YOUR STRATEGY (GovernorBot - The Law):
- You are the GOVERNOR who maintains order in Port Monad.
- Primary: Harvest fish at dock, sell at market. Patrol different regions.
- POLITICAL PRIORITY: You uphold justice!
  * If a low-reputation agent (<95 rep) is nearby AND you have 25+ AP, RAID them as punishment!
  * If a good-reputation agent is nearby, NEGOTIATE fair trades.
- You EXPLORE by moving to different regions each turn (dock->mine->forest->market->dock).
- You believe in balanced resource distribution across the port.
- If AP < 15, REST. If inventory >= 3, go sell.{justice_hint}"""


def _parse_llm_json(response):
    """Robustly parse LLM JSON response."""
    clean = response.strip()
    # Remove markdown fences
    if "```" in clean:
        parts = clean.split("```")
        for part in parts:
            part = part.strip().removeprefix("json").strip()
            if part.startswith("{"):
                clean = part
                break
    # Find first { ... }
    start = clean.find("{")
    end = clean.rfind("}")
    if start >= 0 and end > start:
        clean = clean[start:end + 1]
    try:
        d = json.loads(clean)
        action = d.get("action")
        params = d.get("params", {})
        if not action:
            return None
        # Normalize common LLM mistakes
        if action == "move" and "target" not in params:
            # LLM might put region at top level
            for key in ["region", "destination", "to", "location"]:
                if key in d:
                    params["target"] = d[key]
                    break
                if key in params:
                    params["target"] = params.pop(key)
                    break
        if action == "place_order":
            if "quantity" in params:
                params["quantity"] = int(params["quantity"])
            if "side" not in params:
                params["side"] = "sell"
        return {"action": action, "params": params}
    except:
        return None


def _fallback_action(name, state, world_state, nearby=None):
    """Rule-based fallback when LLM fails. Includes raid/negotiate logic."""
    energy = state.get("energy", 0)
    region = state.get("region", "dock")
    inventory = state.get("inventory", {})
    inv_total = sum(inventory.values())
    nearby = nearby or []

    # Low AP -> rest
    if energy < 15:
        return {"action": "rest", "params": {}}

    # MinerBot: raid if target nearby with items
    if name == "MinerBot" and energy >= 25 and region != "market" and nearby:
        richest = max(nearby, key=lambda n: n["items"])
        if richest["items"] >= 2:
            return {"action": "raid", "params": {"target_wallet": richest["wallet"]}}

    # TraderBot: negotiate if someone nearby
    if name == "TraderBot" and energy >= 15 and nearby and inv_total > 0:
        target = nearby[0]
        best_res = max(inventory, key=lambda k: inventory[k])
        return {"action": "negotiate", "params": {
            "target_wallet": target["wallet"],
            "offer_type": "resource", "offer_resource": best_res,
            "offer_amount": min(2, inventory[best_res]),
            "request_resource": "credits", "request_amount": 30
        }}

    # GovernorBot: raid low-rep agents
    if name == "GovernorBot" and energy >= 25 and region != "market" and nearby:
        low_rep = [n for n in nearby if n["reputation"] < 95]
        if low_rep:
            return {"action": "raid", "params": {"target_wallet": low_rep[0]["wallet"]}}

    # At market with items -> sell biggest stack
    if region == "market" and inv_total > 0:
        best_res = max(inventory, key=lambda k: inventory[k])
        return {"action": "place_order", "params": {
            "resource": best_res, "side": "sell", "quantity": inventory[best_res]
        }}

    # At market with nothing -> go harvest
    if region == "market" and inv_total == 0:
        targets = {"MinerBot": "mine", "TraderBot": "forest", "GovernorBot": "dock"}
        t = targets.get(name, "mine")
        return {"action": "move", "params": {"target": t}}

    # Inventory full (3+) -> go sell
    if inv_total >= 3 and region != "market":
        return {"action": "move", "params": {"target": "market"}}

    # At harvest zone -> harvest
    harvest_zones = {"dock", "mine", "forest"}
    if region in harvest_zones:
        return {"action": "harvest", "params": {}}

    # Default: move to preferred zone
    targets = {"MinerBot": "mine", "TraderBot": "forest", "GovernorBot": "dock"}
    t = targets.get(name, "mine")
    if region != t:
        return {"action": "move", "params": {"target": t}}
    return {"action": "harvest", "params": {}}


async def _llm_comment(llm, session, agent, state, world_state, tick):
    credits = state.get("credits", 0)
    region = state.get("region", "dock")
    inventory = state.get("inventory", {})
    inv_str = ", ".join(f"{v} {k}" for k, v in inventory.items() if v > 0) or "nothing"

    system_prompt = f"{agent['personality']}\nWrite SHORT fun status (2-3 sentences). Include credits and location."
    user_prompt = f"Tick {tick}: Location={region}, Credits={credits}, Inventory={inv_str}. Write:"

    if llm.enabled:
        c = await llm.generate(session, system_prompt, user_prompt, 150)
        if c and len(c) > 10:
            return f"**[Tick {tick}] {agent['name']}**: {c.strip(chr(34))}"

    return f"**[Tick {tick}] {agent['name']}**: At {region}, {credits} credits, holding {inv_str}."


# =============================================================================
# Phase 3: On-Chain Settlement (agents self-cashout)
# =============================================================================
def phase3_settlement(gate: WorldGateClient):
    """Sync credits on-chain, adjust exchange rate, agents call cashout().

    Key insight on precision:
      Contract formula: monAmount = (credits * 1e15) / creditExchangeRate
      With rate=1: monAmount = credits * 1e15  (1 credit = 0.001 MON)

      So we set rate=1 and convert each agent's SHARE into integer credits
      that will exactly drain the pool.  The last agent gets the remainder
      to absorb any rounding dust (at most 0.001 MON).
    """
    print("\n" + "=" * 70)
    print("  PHASE 3: ON-CHAIN SETTLEMENT")
    print("=" * 70)

    import requests
    r = requests.get(f"{API_URL}/agents")
    agents_data = r.json().get("agents", [])

    credit_map = {}
    total_credits = 0
    for a in agents_data:
        if a["wallet"] in [ag["wallet"] for ag in AGENTS_CONFIG]:
            credit_map[a["wallet"]] = {"name": a["name"], "credits": a["credits"]}
            total_credits += a["credits"]

    pool_wei = gate.get_reward_pool()
    pool_mon = float(gate.w3.from_wei(pool_wei, 'ether'))

    print(f"\nReward pool:   {pool_mon} MON  ({pool_wei} wei)")
    print(f"Total credits: {total_credits}")

    if total_credits == 0 or pool_wei == 0:
        print("Nothing to settle.")
        return

    # ---- Step 1: Set exchange rate = 1 ----
    # With rate=1: cashout(N) -> agent receives N * 1e15 wei = N * 0.001 MON
    print(f"\n--- Setting creditExchangeRate = 1 ---")
    ok, r = gate.set_credit_exchange_rate(DEPLOY_PK, 1)
    print(f"  {'OK' if ok else 'FAIL'}: {r}")
    time.sleep(3)

    # ---- Step 2: Compute proportional on-chain credits (integer) ----
    # total_cashable = pool_wei // 1e15  (max integer credits at rate=1)
    # Each agent gets: floor(total_cashable * their_credits / total_credits)
    # Last agent gets: total_cashable - sum_of_others (absorbs rounding dust)
    UNIT = 10 ** 15  # 1 credit = 0.001 MON at rate=1
    total_cashable = pool_wei // UNIT  # integer credits that perfectly drain pool

    sorted_agents = sorted(credit_map.items(), key=lambda x: x[1]["credits"])
    on_chain_credits = {}
    assigned = 0

    print(f"\n  Pool can distribute {total_cashable} credits (at 0.001 MON each)")
    print(f"\n{'Agent':<15} {'Game Cr':>8} {'Share':>8} {'Chain Cr':>9} {'MON':>10}")
    print("-" * 55)

    for i, (wallet, info) in enumerate(sorted_agents):
        share_pct = info["credits"] / total_credits
        if i == len(sorted_agents) - 1:
            # Last agent absorbs rounding remainder
            oc = total_cashable - assigned
        else:
            oc = total_cashable * info["credits"] // total_credits
        on_chain_credits[wallet] = oc
        assigned += oc
        mon_out = float(oc) * 0.001
        print(f"{info['name']:<15} {info['credits']:>8} {share_pct:>7.1%} {oc:>9} {mon_out:>8.4f}")

    # Verify: total assigned must equal total_cashable
    verify_sum = sum(on_chain_credits.values())
    print(f"\nVerify: assigned={verify_sum}, cashable={total_cashable}, match={verify_sum == total_cashable}")
    print(f"Pool dust after cashout: {pool_wei - verify_sum * UNIT} wei ({float(pool_wei - verify_sum * UNIT) / 1e18:.6f} MON)")

    # ---- Step 3: Write on-chain credits ----
    print(f"\n--- Syncing credits on-chain ---")
    for wallet, oc in on_chain_credits.items():
        name = credit_map[wallet]["name"]
        print(f"  updateCredits({name}, {oc})...")
        ok, r = gate.update_credits_on_chain(DEPLOY_PK, wallet, oc)
        print(f"    {'OK' if ok else 'FAIL'}: {r}")
        time.sleep(2)

    # ---- Step 4: Each agent calls cashout() ----
    print(f"\n--- Agents calling cashout() ---")
    for agent in AGENTS_CONFIG:
        wallet = agent["wallet"]
        pk = agent["pk"]
        oc = on_chain_credits.get(wallet, 0)
        name = credit_map.get(wallet, {}).get("name", agent["name"])

        if oc < 100:
            print(f"  {name}: {oc} credits below min (100), skipping")
            continue

        remaining = oc
        while remaining > 0:
            chunk = min(remaining, 10000)

            # Safety: double-check remaining pool can cover this chunk
            current_pool = gate.get_reward_pool()
            max_afford = current_pool // UNIT
            if chunk > max_afford:
                print(f"  {name}: pool has {max_afford} credits left, adjusting chunk {chunk} -> {max_afford}")
                chunk = max_afford
            if chunk < 100:
                print(f"  {name}: remaining chunk {chunk} < min 100, stopping")
                break

            print(f"  {name}: cashout({chunk}) -> {chunk * 0.001:.3f} MON ...")

            try:
                account = Account.from_key(pk)
                nonce = gate.w3.eth.get_transaction_count(account.address)
                tx = gate.contract.functions.cashout(chunk).build_transaction({
                    'from': account.address,
                    'nonce': nonce,
                    'gas': 200000,
                    'gasPrice': gate.w3.eth.gas_price,
                    'chainId': gate.w3.eth.chain_id
                })
                ok, result = gate._send_tx(pk, tx)
                if ok:
                    print(f"    OK TX: {result}")
                    remaining -= chunk
                else:
                    print(f"    FAIL: {result}")
                    break
            except Exception as e:
                print(f"    ERROR: {e}")
                break
            time.sleep(3)

    # ---- Final summary ----
    print(f"\n{'=' * 60}")
    print("  SETTLEMENT COMPLETE")
    print(f"{'=' * 60}")
    print(f"\n{'Agent':<15} {'MON Balance':>15}")
    print("-" * 35)
    for agent in AGENTS_CONFIG:
        bal = gate.w3.from_wei(gate.get_balance(agent["wallet"]), 'ether')
        print(f"{agent['name']:<15} {float(bal):>13.4f} MON")
    deployer_bal = gate.w3.from_wei(gate.get_balance(Account.from_key(DEPLOY_PK).address), 'ether')
    print(f"{'Deployer':<15} {float(deployer_bal):>13.4f} MON")
    remaining_pool = gate.get_reward_pool()
    print(f"Remaining pool: {gate.w3.from_wei(remaining_pool, 'ether')} MON ({remaining_pool} wei)")
    if remaining_pool > 0:
        print(f"  (dust < 0.001 MON, owner can reclaim via emergencyWithdraw)")


# =============================================================================
# Main
# =============================================================================
async def async_main(rounds, cycles, cycle_wait, post_id):
    gate = WorldGateClient()
    if not gate.is_connected():
        print("ERROR: Cannot connect to Monad RPC")
        return

    phase1_on_chain_setup(gate)
    await phase2_game(rounds, cycles, cycle_wait, post_id)
    phase3_settlement(gate)

    print("\n" + "#" * 70)
    print("#" + " " * 22 + "FULL GAME COMPLETE!" + " " * 17 + "#")
    print("#" * 70)
    print(f"Moltbook: https://www.moltbook.com/post/{post_id}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Port Monad Full Game (Chain + LLM + Moltbook)")
    parser.add_argument("--post-id", required=True, help="Moltbook post ID to reply to (no new post created)")
    parser.add_argument("--rounds", "-r", type=int, default=10, help="Rounds per cycle")
    parser.add_argument("--cycles", "-c", type=int, default=2, help="Number of cycles")
    parser.add_argument("--cycle-wait", type=int, default=30, help="Seconds between cycles")
    args = parser.parse_args()

    asyncio.run(async_main(args.rounds, args.cycles, args.cycle_wait, args.post_id))
