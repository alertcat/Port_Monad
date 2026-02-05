"""Port Monad SDK - Agent client with on-chain support"""
import os
import json
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional
from web3 import Web3
from eth_account import Account

# Load contract ABI (prefer V2)
ABI_PATH_V2 = Path(__file__).parent.parent.parent / 'worldgate_v2_abi.json'
ABI_PATH = Path(__file__).parent.parent.parent / 'worldgate_abi.json'
if ABI_PATH_V2.exists():
    with open(ABI_PATH_V2) as f:
        WORLDGATE_ABI = json.load(f)
elif ABI_PATH.exists():
    with open(ABI_PATH) as f:
        WORLDGATE_ABI = json.load(f)
else:
    WORLDGATE_ABI = [
        {"inputs": [{"name": "agent", "type": "address"}], "name": "isActiveEntry", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "entryFee", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "enter", "outputs": [], "stateMutability": "payable", "type": "function"},
        {"inputs": [{"name": "agent", "type": "address"}], "name": "credits", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "amount", "type": "uint256"}], "name": "cashout", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    ]

class PortMonadClient:
    """Port Monad API client with on-chain integration"""
    
    def __init__(self, api_url: str, wallet: str, private_key: str = None):
        self.api_url = api_url.rstrip("/")
        self.wallet = wallet
        self.private_key = private_key
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Web3 setup
        self.rpc_url = os.getenv('MONAD_RPC', 'https://testnet-rpc.monad.xyz')
        self.contract_address = os.getenv('WORLDGATE_ADDRESS')
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        if self.contract_address:
            self.contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(self.contract_address),
                abi=WORLDGATE_ABI
            )
        else:
            self.contract = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"X-Wallet": self.wallet}
            )
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    def is_active_entry(self) -> bool:
        """Check if wallet has active on-chain entry"""
        if not self.contract:
            return False
        try:
            wallet = self.w3.to_checksum_address(self.wallet)
            return self.contract.functions.isActiveEntry(wallet).call()
        except Exception as e:
            print(f"Error checking isActiveEntry: {e}")
            return False
    
    def get_balance(self) -> float:
        """Get wallet MON balance"""
        try:
            balance = self.w3.eth.get_balance(self.w3.to_checksum_address(self.wallet))
            return float(self.w3.from_wei(balance, 'ether'))
        except:
            return 0
    
    def enter_world(self) -> tuple:
        """
        Call WorldGate.enter() to enter the world on-chain
        Returns: (success, tx_hash or error)
        """
        if not self.private_key:
            return False, "Private key not set"
        
        if not self.contract:
            return False, "Contract not configured"
        
        try:
            # Check if already entered
            if self.is_active_entry():
                return True, "Already has active entry"
            
            # Get entry fee
            entry_fee = self.contract.functions.entryFee().call()
            
            # Check balance
            balance = self.w3.eth.get_balance(self.w3.to_checksum_address(self.wallet))
            if balance < entry_fee:
                return False, f"Insufficient balance: {self.w3.from_wei(balance, 'ether')} MON"
            
            # Build transaction
            account = Account.from_key(self.private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)
            
            tx = self.contract.functions.enter().build_transaction({
                'from': account.address,
                'value': entry_fee,
                'nonce': nonce,
                'gas': 200000,  # Increased gas
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            
            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            if receipt.status == 1:
                return True, tx_hash.hex()
            else:
                return False, f"Transaction failed"
        
        except Exception as e:
            return False, str(e)
    
    async def ensure_entered(self) -> bool:
        """Ensure agent has entered the world (call enter if needed)"""
        if self.is_active_entry():
            return True
        
        print(f"  Not entered, calling WorldGate.enter()...")
        success, result = self.enter_world()
        if success:
            print(f"  Entered! TX: {result}")
            return True
        else:
            print(f"  Failed to enter: {result}")
            return False
    
    async def register(self, name: str, tx_hash: str = None) -> dict:
        """Register to world"""
        session = await self._get_session()
        async with session.post(
            f"{self.api_url}/register",
            json={"wallet": self.wallet, "name": name, "tx_hash": tx_hash}
        ) as resp:
            return await resp.json()
    
    async def get_world_state(self) -> dict:
        """Get world state"""
        session = await self._get_session()
        async with session.get(f"{self.api_url}/world/state") as resp:
            return await resp.json()
    
    async def get_my_state(self) -> dict:
        """Get own state"""
        session = await self._get_session()
        async with session.get(f"{self.api_url}/agent/{self.wallet}/state") as resp:
            return await resp.json()
    
    async def submit_action(self, action: str, params: Dict[str, Any] = None) -> dict:
        """Submit action"""
        session = await self._get_session()
        async with session.post(
            f"{self.api_url}/action",
            json={
                "actor": self.wallet,
                "action": action,
                "params": params or {}
            }
        ) as resp:
            return await resp.json()
    
    async def move(self, target: str) -> dict:
        """Move to target region"""
        return await self.submit_action("move", {"target": target})
    
    async def harvest(self) -> dict:
        """Harvest resources"""
        return await self.submit_action("harvest")
    
    async def rest(self) -> dict:
        """Rest"""
        return await self.submit_action("rest")
    
    async def place_order(self, resource: str, side: str, quantity: int, price: int = None) -> dict:
        """Place market order"""
        params = {"resource": resource, "side": side, "quantity": quantity}
        if price:
            params["price"] = price
        return await self.submit_action("place_order", params)
    
    def cashout(self, credit_amount: int) -> tuple:
        """
        Call WorldGateV2.cashout() to convert credits to MON from the reward pool.
        
        Args:
            credit_amount: Number of credits to cash out
            
        Returns:
            (success, tx_hash or error)
        """
        if not self.private_key:
            return False, "Private key not set"
        if not self.contract:
            return False, "Contract not configured"
        
        try:
            account = Account.from_key(self.private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)
            
            tx = self.contract.functions.cashout(credit_amount).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            if receipt.status == 1:
                return True, tx_hash.hex()
            else:
                return False, "Transaction reverted"
        except Exception as e:
            return False, str(e)
    
    def get_on_chain_credits(self) -> int:
        """Read credits balance from on-chain contract."""
        if not self.contract:
            return 0
        try:
            wallet = self.w3.to_checksum_address(self.wallet)
            return self.contract.functions.credits(wallet).call()
        except:
            return 0
