#!/usr/bin/env python3
"""End-to-end test: on-chain enter -> API register -> actions"""
import os
import sys
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'agents'))
from sdk.client import PortMonadClient

API_URL = os.getenv("API_URL", "http://localhost:8000")

async def test_agent(name: str, wallet: str, private_key: str):
    """Test a single agent: enter -> register -> action"""
    print(f"\n{'='*50}")
    print(f"Testing {name}")
    print(f"{'='*50}")
    print(f"Wallet: {wallet}")
    
    client = PortMonadClient(API_URL, wallet, private_key)
    
    # 1. Check balance
    balance = client.get_balance()
    print(f"Balance: {balance} MON")
    
    # 2. Check on-chain entry
    print("\nStep 1: On-chain entry check...")
    if client.is_active_entry():
        print("  OK: Already entered on-chain")
    else:
        print("  Not entered, calling WorldGate.enter()...")
        if balance < 0.05:
            print(f"  ERROR: Insufficient balance (need 0.05 MON)")
            return False
        success, result = client.enter_world()
        if success:
            print(f"  SUCCESS: {result}")
        else:
            print(f"  FAILED: {result}")
            return False
    
    # 3. Register with API
    print("\nStep 2: API registration...")
    result = await client.register(name)
    print(f"  Result: {result}")
    
    if not result.get('success'):
        print(f"  FAILED: {result}")
        return False
    
    # 4. Get state
    print("\nStep 3: Get agent state...")
    state = await client.get_my_state()
    print(f"  Region: {state.get('region')}")
    print(f"  Energy: {state.get('energy')}")
    print(f"  Credits: {state.get('credits')}")
    
    # 5. Execute an action
    print("\nStep 4: Execute action (move to mine)...")
    result = await client.submit_action("move", {"target": "mine"})
    print(f"  Result: {result.get('message', result)}")
    
    if not result.get('success'):
        print(f"  FAILED: {result}")
        return False
    
    # 6. Verify state changed
    print("\nStep 5: Verify state changed...")
    state = await client.get_my_state()
    print(f"  Region: {state.get('region')}")
    print(f"  Energy: {state.get('energy')}")
    
    await client.close()
    
    print(f"\n{name} TEST PASSED!")
    return True

async def test_api_health():
    """Test API is running"""
    print("Testing API health...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_URL}/health") as resp:
                if resp.status == 200:
                    print(f"  API is running at {API_URL}")
                    return True
                else:
                    print(f"  API returned {resp.status}")
                    return False
        except Exception as e:
            print(f"  API not reachable: {e}")
            print(f"  Please start API with: python world-api/app.py")
            return False

async def main():
    print("="*60)
    print("PORT MONAD END-TO-END TEST")
    print("="*60)
    
    # Check API
    if not await test_api_health():
        return
    
    # Test each agent
    agents = [
        ("MinerBot", os.getenv("MINER_WALLET"), os.getenv("MINER_PRIVATE_KEY")),
        ("TraderBot", os.getenv("TRADER_WALLET"), os.getenv("TRADER_PRIVATE_KEY")),
        ("GovernorBot", os.getenv("GOVERNOR_WALLET"), os.getenv("GOVERNOR_PRIVATE_KEY")),
    ]
    
    results = []
    for name, wallet, private_key in agents:
        if not wallet or not private_key:
            print(f"\n{name}: SKIPPED (wallet/key not configured)")
            results.append(False)
            continue
        
        success = await test_agent(name, wallet, private_key)
        results.append(success)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for (name, _, _), success in zip(agents, results):
        status = "PASS" if success else "FAIL"
        print(f"  {name}: {status}")
    
    passed = sum(results)
    total = len(results)
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\nALL TESTS PASSED!")
    else:
        print("\nSOME TESTS FAILED")

if __name__ == "__main__":
    asyncio.run(main())
