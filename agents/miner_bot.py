"""MinerBot - Mining robot with on-chain entry"""
import asyncio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from sdk.client import PortMonadClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s [MinerBot] %(message)s')
log = logging.getLogger(__name__)

class MinerBot:
    """Miner robot: harvest -> sell"""
    
    SELL_THRESHOLD = 10
    
    def __init__(self, client: PortMonadClient):
        self.client = client
    
    async def decide(self, my_state: dict, world_state: dict) -> dict:
        """Decide: return action to execute"""
        energy = my_state.get("energy", 0)
        inventory = my_state.get("inventory", {})
        region = my_state.get("region", "dock")
        
        iron = inventory.get("iron", 0)
        wood = inventory.get("wood", 0)
        total_resources = iron + wood
        
        # Priority 1: Low AP, rest
        if energy < 20:
            log.info(f"Low AP ({energy}), resting")
            return {"action": "rest"}
        
        # Priority 2: Inventory full, go to market
        if total_resources >= self.SELL_THRESHOLD:
            if region != "market":
                log.info(f"Inventory full ({total_resources}), going to market")
                return {"action": "move", "params": {"target": "market"}}
            else:
                if iron > 0:
                    log.info(f"Selling {iron} iron")
                    return {"action": "place_order", "params": {
                        "resource": "iron", "side": "sell", "quantity": iron
                    }}
                if wood > 0:
                    log.info(f"Selling {wood} wood")
                    return {"action": "place_order", "params": {
                        "resource": "wood", "side": "sell", "quantity": wood
                    }}
        
        # Priority 3: Go to mine
        if region != "mine":
            log.info("Going to mine")
            return {"action": "move", "params": {"target": "mine"}}
        
        log.info("Mining")
        return {"action": "harvest"}
    
    async def run_cycle(self):
        """Run one decision cycle"""
        try:
            my_state = await self.client.get_my_state()
            if "error" in my_state:
                log.error(f"Failed to get state: {my_state}")
                return None
            
            world_state = await self.client.get_world_state()
            action = await self.decide(my_state, world_state)
            
            if action:
                result = await self.client.submit_action(
                    action["action"],
                    action.get("params", {})
                )
                log.info(f"Result: {result.get('message', result)}")
                return result
        except Exception as e:
            log.error(f"Cycle failed: {e}")
        return None

async def main():
    api_url = os.getenv("API_URL", "http://localhost:8000")
    wallet = os.getenv("MINER_WALLET")
    private_key = os.getenv("MINER_PRIVATE_KEY")
    
    if not wallet or not private_key:
        log.error("MINER_WALLET and MINER_PRIVATE_KEY must be set in .env")
        return
    
    log.info(f"Wallet: {wallet}")
    log.info(f"Balance: {PortMonadClient(api_url, wallet, private_key).get_balance()} MON")
    
    client = PortMonadClient(api_url, wallet, private_key)
    
    # 1. Ensure entered on-chain
    log.info("Checking on-chain entry status...")
    if not await client.ensure_entered():
        log.error("Failed to enter world on-chain")
        return
    
    # 2. Register with API
    log.info(f"Registering with API...")
    result = await client.register("MinerBot")
    log.info(f"Registration: {result.get('message', result)}")
    
    if not result.get('success'):
        log.error(f"Registration failed: {result}")
        return
    
    # 3. Run bot loop
    log.info("Starting bot loop...")
    bot = MinerBot(client)
    while True:
        await bot.run_cycle()
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
