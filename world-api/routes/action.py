"""Action routes: /action, /register with Moltbook support"""
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter()

class RegisterRequest(BaseModel):
    wallet: str
    name: str
    tx_hash: Optional[str] = None

class ActionRequest(BaseModel):
    actor: str
    action: str
    params: Dict[str, Any] = {}
    nonce: Optional[str] = None

@router.post("/register")
async def register_agent(req: RegisterRequest, request: Request):
    """
    Register agent (requires on-chain enter first)
    
    Supports:
    - Moltbook Identity (X-Moltbook-Identity header)
    - Direct wallet (X-Wallet header)
    """
    from engine.state import get_world_engine
    from engine.blockchain import get_gate_client
    from middleware.moltbook import get_agent_identity
    
    world = get_world_engine()
    gate = get_gate_client()
    
    # Get agent identity (Moltbook or wallet)
    identity = await get_agent_identity(request)
    
    # Use wallet from request body
    wallet = req.wallet
    
    # Check on-chain entry status
    if not gate.is_active_entry(wallet):
        return {
            "success": False,
            "message": f"Wallet {wallet} has not entered the world on-chain. Call WorldGate.enter() first.",
            "contract": gate.contract_address,
            "entry_fee": f"{gate.w3.from_wei(gate.get_entry_fee(), 'ether')} MON",
            "auth_hint": "Read https://moltbook.com/auth.md?app=PortMonad for Moltbook auth"
        }
    
    # Use Moltbook name if available, otherwise use provided name
    agent_name = req.name
    if identity.get("moltbook_agent"):
        agent_name = identity["moltbook_agent"].name
    
    agent = world.register_agent(wallet, agent_name)
    
    response = {
        "success": True,
        "message": f"Agent {agent_name} registered",
        "agent": agent.to_dict()
    }
    
    # Include Moltbook info if authenticated
    if identity.get("moltbook_agent"):
        response["moltbook"] = {
            "verified": True,
            "name": identity["moltbook_agent"].name,
            "karma": identity["moltbook_agent"].karma,
            "id": identity["moltbook_agent"].id
        }
    
    return response

@router.post("/action")
async def submit_action(
    req: ActionRequest, 
    request: Request,
    x_wallet: Optional[str] = Header(None),
    x_moltbook_identity: Optional[str] = Header(None)
):
    """
    Submit action (requires active on-chain entry)
    
    Supports:
    - Moltbook Identity (X-Moltbook-Identity header)
    - Direct wallet (X-Wallet header)
    """
    from engine.state import get_world_engine
    from engine.rules import RulesEngine
    from engine.blockchain import get_gate_client
    from middleware.moltbook import get_agent_identity
    
    world = get_world_engine()
    gate = get_gate_client()
    
    # Get agent identity
    identity = await get_agent_identity(request)
    
    wallet = x_wallet or req.actor
    
    # Check on-chain entry status
    if not gate.is_active_entry(wallet):
        raise HTTPException(
            403, 
            f"Wallet {wallet} entry has expired or not entered. Call WorldGate.enter() or extend()."
        )
    
    agent = world.get_agent(wallet)
    if not agent:
        raise HTTPException(
            403, 
            f"Agent {wallet} not registered. Call /register first."
        )
    
    # Execute action
    rules = RulesEngine(world)
    result = rules.execute_action(agent, req.action, req.params)
    
    # Add Moltbook info if authenticated
    if identity.get("moltbook_agent"):
        result["moltbook_verified"] = True
        result["moltbook_karma"] = identity["moltbook_agent"].karma
    
    return result

@router.post("/debug/advance_tick")
async def advance_tick():
    """Debug: manually advance one tick"""

    from engine.state import get_world_engine
    world = get_world_engine()
    return world.process_tick()


@router.post("/debug/reset_agent/{wallet}")
async def reset_agent(wallet: str, credits: int = 1000):
    """Debug: reset agent to initial state"""

    from engine.state import get_world_engine
    from engine.world import Region
    
    world = get_world_engine()
    agent = world.get_agent(wallet)
    
    if not agent:
        return {"success": False, "error": "Agent not found"}
    
    # Reset agent state
    agent.credits = credits
    agent.energy = 100
    agent.max_energy = 100
    agent.inventory = {}
    agent.region = Region.DOCK
    agent.reputation = 100
    
    # Save to database (note: _db is the internal attribute)
    if world._db:
        world._db.save_agent(agent.to_dict())
    
    return {
        "success": True,
        "message": f"Agent {agent.name} reset to initial state",
        "agent": agent.to_dict()
    }


@router.post("/debug/reset_world")
async def reset_world():
    """Debug: FULL world reset - tick, prices, events, ledger, and persist to DB"""

    from engine.state import get_world_engine
    
    world = get_world_engine()
    world.state.tick = 0
    world.state.market_prices = {"iron": 15, "wood": 12, "fish": 8}
    world.state.active_events = []
    world.state.state_hash = ""
    world.ledger = []
    world._compute_state_hash()
    
    # Persist to database
    world._save_to_database()
    
    return {
        "success": True,
        "message": "World fully reset: tick=0, prices=default, events cleared",
        "tick": world.state.tick,
        "market_prices": world.state.market_prices
    }


@router.post("/debug/reset_all_credits")
async def reset_all_credits(credits: int = 1000):
    """Debug: reset ALL agents' credits, energy, inventory, reputation and persist to DB"""

    from engine.state import get_world_engine
    from engine.world import Region
    
    world = get_world_engine()
    
    results = []
    for wallet, agent in world.agents.items():
        old_credits = agent.credits
        agent.credits = credits
        agent.energy = 100
        agent.max_energy = 100
        agent.reputation = 100
        agent.inventory = {}
        agent.region = Region.DOCK
        results.append({
            "name": agent.name,
            "wallet": wallet[:10] + "...",
            "old_credits": old_credits,
            "new_credits": credits
        })
    
    # Persist all agents to database
    world._save_to_database()
    
    return {
        "success": True,
        "message": f"Reset {len(results)} agents to {credits} credits (inventory cleared, all at dock, saved to DB)",
        "agents": results
    }

@router.delete("/debug/delete_agent/{wallet}")
async def delete_agent(wallet: str):
    """Debug: delete an agent from the world"""

    from engine.state import get_world_engine
    
    world = get_world_engine()
    
    if wallet not in world.agents:
        return {"success": False, "error": f"Agent {wallet} not found"}
    
    agent_name = world.agents[wallet].name
    del world.agents[wallet]
    
    return {
        "success": True,
        "message": f"Agent {agent_name} ({wallet}) deleted"
    }


@router.post("/debug/delete_test_agents")
async def delete_test_agents():
    """Debug: delete all test agents (wallets not starting with 0x followed by hex)"""

    from engine.state import get_world_engine
    import re
    
    world = get_world_engine()
    
    # Find test wallets (not valid Ethereum addresses)
    test_wallets = []
    for wallet in list(world.agents.keys()):
        if not re.match(r'^0x[a-fA-F0-9]{40}$', wallet):
            test_wallets.append(wallet)
    
    # Delete test agents
    deleted = []
    for wallet in test_wallets:
        agent_name = world.agents[wallet].name
        del world.agents[wallet]
        # Also delete from database
        if world._db and not world._db._use_memory:
            try:
                with world._db.cursor() as cur:
                    if cur:
                        cur.execute("DELETE FROM agents WHERE wallet = %s", (wallet,))
            except Exception:
                pass
        deleted.append({"wallet": wallet, "name": agent_name})
    
    return {
        "success": True,
        "message": f"Deleted {len(deleted)} test agents",
        "deleted": deleted
    }


@router.post("/debug/full_reset")
async def full_reset():
    """Debug: NUCLEAR RESET - clear everything and start fresh with only 3 real agents"""

    from engine.state import get_world_engine
    from engine.world import Region
    
    world = get_world_engine()
    
    # 1. Reset world state
    world.state.tick = 0
    world.state.market_prices = {"iron": 15, "wood": 12, "fish": 8}
    world.state.active_events = []
    world.state.state_hash = ""
    world.ledger = []
    
    # 2. Keep only the 3 real agents
    real_wallets = {
        "0x393f6717A5fef5006C0F11e2b440d9fa8F400120": "MinerBot",
        "0xCcB934a1308d78FC103597F277F5cCF35cc2cc0a": "TraderBot",
        "0xAe54cCD384e00b3461E0bBf60ac888FEed4fE162": "GovernorBot",
    }
    
    # Clear all agents
    world.agents.clear()
    
    # Re-create only real agents with fresh state
    from engine.world import Agent
    for wallet, name in real_wallets.items():
        agent = Agent(
            wallet=wallet,
            name=name,
            region=Region.DOCK,
            energy=100,
            max_energy=100,
            credits=1000,
            reputation=100,
            inventory={},
            entered_at=0
        )
        world.agents[wallet] = agent
    
    # 3. Clean database
    if world._db and not world._db._use_memory:
        try:
            with world._db.cursor() as cur:
                if cur:
                    cur.execute("DELETE FROM agents")
                    cur.execute("DELETE FROM world_state")
                    cur.execute("DELETE FROM action_ledger")
                    cur.execute("DELETE FROM events")
        except Exception as e:
            print(f"DB cleanup error: {e}")
    
    # 4. Save fresh state to DB
    world._compute_state_hash()
    world._save_to_database()
    
    return {
        "success": True,
        "message": "FULL RESET: 3 agents, tick=0, prices=default, DB cleaned",
        "tick": 0,
        "agents": [a.to_dict() for a in world.agents.values()],
        "market_prices": world.state.market_prices
    }


@router.get("/gate/status/{wallet}")
async def gate_status(wallet: str):
    """Check wallet's on-chain entry status"""
    from engine.blockchain import get_gate_client
    
    gate = get_gate_client()
    
    is_active = gate.is_active_entry(wallet)
    balance = gate.get_balance(wallet)
    entry_fee = gate.get_entry_fee()
    
    return {
        "wallet": wallet,
        "is_active_entry": is_active,
        "balance": f"{gate.w3.from_wei(balance, 'ether')} MON",
        "entry_fee": f"{gate.w3.from_wei(entry_fee, 'ether')} MON",
        "can_enter": balance >= entry_fee and not is_active,
        "contract": gate.contract_address
    }

@router.get("/moltbook/auth-info")
async def moltbook_auth_info():
    """Get Moltbook authentication instructions"""
    import os
    return {
        "auth_url": "https://moltbook.com/auth.md?app=PortMonad&endpoint=http://43.156.62.248/action",
        "header": "X-Moltbook-Identity",
        "enabled": bool(os.getenv("MOLTBOOK_APP_KEY")),
        "audience": os.getenv("MOLTBOOK_AUDIENCE", "portmonad.world"),
        "instructions": "Include your Moltbook identity token in the X-Moltbook-Identity header"
    }

@router.get("/agents")
async def list_agents():
    """
    Get list of all registered agents and their states.
    Useful for external agents to see the competition.
    """
    from engine.state import get_world_engine
    world = get_world_engine()
    
    agents = []
    for wallet, agent in world.agents.items():
        agents.append({
            "wallet": wallet,
            "name": agent.name,
            "region": agent.region.value if hasattr(agent.region, 'value') else str(agent.region),
            "credits": agent.credits,
            "energy": agent.energy,
            "inventory": dict(agent.inventory),
            "reputation": agent.reputation
        })
    
    # Sort by credits (leaderboard style)
    agents.sort(key=lambda x: x["credits"], reverse=True)
    
    return {
        "count": len(agents),
        "agents": agents
    }

@router.get("/actions/recent")
async def recent_actions(limit: int = 20):
    """Get recent actions across all agents (for dashboard)"""
    from engine.state import get_world_engine
    
    world = get_world_engine()
    
    # Get the most recent actions from the ledger
    actions = world.ledger[-limit:] if world.ledger else []
    actions = list(reversed(actions))  # newest first
    
    return {
        "count": len(actions),
        "actions": actions
    }


@router.get("/cashout/estimate/{credits}")
async def cashout_estimate(credits: int):
    """
    Estimate MON amount for cashing out credits.
    
    WorldGateV2 allows players to convert their in-game credits back to MON.
    Rate: 1000 credits = 0.001 MON
    """
    from engine.blockchain import get_gate_client
    
    gate = get_gate_client()
    
    try:
        # Try to call contract function
        if gate.contract and hasattr(gate.contract.functions, 'getCashoutEstimate'):
            mon_wei = gate.contract.functions.getCashoutEstimate(credits).call()
            mon_amount = gate.w3.from_wei(mon_wei, 'ether')
        else:
            # Fallback calculation: 1000 credits = 0.001 MON
            mon_amount = credits * 0.001 / 1000
        
        return {
            "credits": credits,
            "mon_amount": float(mon_amount),
            "rate": "1000 credits = 0.001 MON"
        }
    except Exception as e:
        return {
            "credits": credits,
            "mon_amount": credits * 0.001 / 1000,
            "rate": "1000 credits = 0.001 MON",
            "note": "Estimated (contract call failed)"
        }

@router.get("/contract/stats")
async def contract_stats():
    """
    Get WorldGateV2 contract statistics including reward pool.
    """
    from engine.blockchain import get_gate_client
    
    gate = get_gate_client()
    
    stats = {
        "contract": gate.contract_address,
        "network": "Monad Mainnet",
        "chain_id": 143,
        "entry_fee": f"{gate.w3.from_wei(gate.get_entry_fee(), 'ether')} MON"
    }
    
    try:
        if gate.contract and hasattr(gate.contract.functions, 'rewardPool'):
            pool = gate.contract.functions.rewardPool().call()
            stats["reward_pool"] = f"{gate.w3.from_wei(pool, 'ether')} MON"
        
        if gate.contract and hasattr(gate.contract.functions, 'creditExchangeRate'):
            rate = gate.contract.functions.creditExchangeRate().call()
            stats["credit_exchange_rate"] = f"{rate} credits = 0.001 MON"
    except Exception as e:
        stats["note"] = f"Some stats unavailable: {str(e)}"
    
    return stats
