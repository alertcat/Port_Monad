#!/usr/bin/env python3
"""
Reset all agents' credits to 1000.

Usage:
    python reset_credits.py
"""
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'world-api'))

from engine.state import get_world_engine

def reset_all_credits(amount: int = 1000):
    """Reset all agents' credits to specified amount"""
    world = get_world_engine()
    
    print(f"\n{'='*60}")
    print(f"🔄 Resetting all agents' credits to {amount}")
    print(f"{'='*60}\n")
    
    # Get all agents
    agents = list(world.agents.values())
    
    if not agents:
        print("❌ No agents found in the world!")
        return
    
    print(f"Found {len(agents)} agents:\n")
    
    for agent in agents:
        old_credits = agent.credits
        agent.credits = amount
        print(f"  • {agent.name} ({agent.wallet[:10]}...): {old_credits} → {amount} credits")
    
    print(f"\n{'='*60}")
    print(f"✅ Reset complete! All {len(agents)} agents now have {amount} credits.")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    # Get amount from command line if provided
    amount = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    reset_all_credits(amount)
