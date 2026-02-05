"""TraderBot - Trading robot with on-chain entry"""
import asyncio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from sdk.client import PortMonadClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s [TraderBot] %(message)s')
log = logging.getLogger(__name__)

class TraderBot:
    """Trading robot: observe market, buy low sell high"""
    
    def __init__(self, client: PortMonadClient):
        self.client = client
        self.price_history = {}
    
    async def decide(self, my_state: dict, world_state: dict) -> dict:
        """Decide"""
        energy = my_state.get("energy", 0)
        credits = my_state.get("credits", 0)
        inventory = my_state.get("inventory", {})
        region = my_state.get("region", "dock")
        
        # Update price history
        prices = world_state.get("market_prices", {})
        for resource, price in prices.items():
            if resource not in self.price_history:
                self.price_history[resource] = []
            self.price_history[resource].append(price)
            self.price_history[resource] = self.price_history[resource][-20:]
        
        if energy < 10:
            log.info(f"Low AP ({energy}), resting")
            return {"action": "rest"}
        
        if region != "market":
            log.info("Going to market")
            return {"action": "move", "params": {"target": "market"}}
        
        # Find trading opportunity
        for resource, history in self.price_history.items():
            if len(history) < 3:
                continue
            
            current = history[-1]
            avg = sum(history) / len(history)
            my_stock = inventory.get(resource, 0)
            
            if current < avg * 0.9 and credits > current * 5:
                qty = min(5, credits // current)
                log.info(f"Buy low: {resource}@{current} (avg:{avg:.1f}), qty:{qty}")
                return {"action": "place_order", "params": {
                    "resource": resource, "side": "buy", "quantity": qty
                }}
            
            if current > avg * 1.1 and my_stock > 0:
                log.info(f"Sell high: {resource}@{current} (avg:{avg:.1f}), qty:{my_stock}")
                return {"action": "place_order", "params": {
                    "resource": resource, "side": "sell", "quantity": my_stock
                }}
        
        log.info("Watching...")
        return None
    
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
    wallet = os.getenv("TRADER_WALLET")
    private_key = os.getenv("TRADER_PRIVATE_KEY")
    
    if not wallet or not private_key:
        log.error("TRADER_WALLET and TRADER_PRIVATE_KEY must be set in .env")
        return
    
    log.info(f"Wallet: {wallet}")
    
    client = PortMonadClient(api_url, wallet, private_key)
    log.info(f"Balance: {client.get_balance()} MON")
    
    # 1. Ensure entered on-chain
    log.info("Checking on-chain entry status...")
    if not await client.ensure_entered():
        log.error("Failed to enter world on-chain")
        return
    
    # 2. Register with API
    log.info(f"Registering with API...")
    result = await client.register("TraderBot")
    log.info(f"Registration: {result.get('message', result)}")
    
    if not result.get('success'):
        log.error(f"Registration failed: {result}")
        return
    
    # 3. Run bot loop
    log.info("Starting bot loop...")
    bot = TraderBot(client)
    while True:
        await bot.run_cycle()
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
