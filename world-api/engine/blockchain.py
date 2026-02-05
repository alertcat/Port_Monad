"""Blockchain integration - WorldGateV2 contract interaction (Monad Mainnet)"""
import os
import json
from pathlib import Path
from typing import Optional, Tuple, List
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
    # Minimal ABI for WorldGateV2
    WORLDGATE_ABI = [
        {"inputs": [{"name": "agent", "type": "address"}], "name": "isActiveEntry", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "entryFee", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "enter", "outputs": [], "stateMutability": "payable", "type": "function"},
        {"inputs": [], "name": "rewardPool", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "agent", "type": "address"}], "name": "credits", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "agent", "type": "address"}, {"name": "newBalance", "type": "uint256"}], "name": "updateCredits", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"name": "amount", "type": "uint256"}], "name": "cashout", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"name": "creditAmount", "type": "uint256"}], "name": "getCashoutEstimate", "outputs": [{"name": "monAmount", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    ]

class WorldGateClient:
    """Client for interacting with WorldGate contract"""
    
    def __init__(self, rpc_url: str = None, contract_address: str = None):
        self.rpc_url = rpc_url or os.getenv('MONAD_RPC', 'https://testnet-rpc.monad.xyz')
        self.contract_address = contract_address or os.getenv('WORLDGATE_ADDRESS')
        
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        if self.contract_address:
            self.contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(self.contract_address),
                abi=WORLDGATE_ABI
            )
        else:
            self.contract = None
    
    def is_connected(self) -> bool:
        """Check if connected to RPC"""
        return self.w3.is_connected()
    
    def is_active_entry(self, wallet: str) -> bool:
        """Check if wallet has active entry in the world"""
        # In DEBUG_MODE, skip on-chain check (for local testing)
        if os.getenv("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
            return True
        
        if not self.contract:
            print("Warning: No contract address, skipping on-chain check")
            return True  # Allow if no contract configured
        
        try:
            wallet = self.w3.to_checksum_address(wallet)
            return self.contract.functions.isActiveEntry(wallet).call()
        except Exception as e:
            print(f"Error checking isActiveEntry: {e}")
            return False
    
    def get_entry_fee(self) -> int:
        """Get current entry fee in wei"""
        if not self.contract:
            return self.w3.to_wei(0.05, 'ether')  # Default
        
        try:
            return self.contract.functions.entryFee().call()
        except Exception as e:
            print(f"Error getting entryFee: {e}")
            return self.w3.to_wei(0.05, 'ether')
    
    def get_balance(self, wallet: str) -> int:
        """Get wallet balance in wei"""
        try:
            wallet = self.w3.to_checksum_address(wallet)
            return self.w3.eth.get_balance(wallet)
        except Exception as e:
            print(f"Error getting balance: {e}")
            return 0
    
    def enter_world(self, private_key: str) -> Tuple[bool, str]:
        """
        Call enter() on WorldGate contract
        Returns: (success, tx_hash or error message)
        """
        if not self.contract:
            return False, "No contract address configured"
        
        try:
            account = Account.from_key(private_key)
            wallet = account.address
            
            # Check if already entered
            if self.is_active_entry(wallet):
                return True, "Already has active entry"
            
            # Get entry fee
            entry_fee = self.get_entry_fee()
            
            # Check balance
            balance = self.get_balance(wallet)
            if balance < entry_fee:
                return False, f"Insufficient balance: {self.w3.from_wei(balance, 'ether')} MON, need {self.w3.from_wei(entry_fee, 'ether')} MON"
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(wallet)
            
            tx = self.contract.functions.enter().build_transaction({
                'from': wallet,
                'value': entry_fee,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            
            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            if receipt.status == 1:
                return True, tx_hash.hex()
            else:
                return False, f"Transaction failed: {tx_hash.hex()}"
        
        except Exception as e:
            return False, str(e)

# Global instance
_gate_client: Optional[WorldGateClient] = None

def get_gate_client() -> WorldGateClient:
    """Get WorldGate client singleton"""
    global _gate_client
    if _gate_client is None:
        _gate_client = WorldGateClient()
    return _gate_client
