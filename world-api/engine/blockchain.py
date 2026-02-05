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
            return self.w3.to_wei(1, 'ether')  # Default: 1 MON
        
        try:
            return self.contract.functions.entryFee().call()
        except Exception as e:
            print(f"Error getting entryFee: {e}")
            return self.w3.to_wei(1, 'ether')
    
    def get_balance(self, wallet: str) -> int:
        """Get wallet balance in wei"""
        try:
            wallet = self.w3.to_checksum_address(wallet)
            return self.w3.eth.get_balance(wallet)
        except Exception as e:
            print(f"Error getting balance: {e}")
            return 0
    
    def _send_tx(self, private_key: str, tx: dict) -> Tuple[bool, str]:
        """Sign, send, and wait for a transaction. Returns (success, tx_hash_or_error)."""
        try:
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status == 1:
                return True, tx_hash.hex()
            else:
                return False, f"Transaction reverted: {tx_hash.hex()}"
        except Exception as e:
            return False, str(e)

    def enter_world(self, private_key: str, force: bool = False) -> Tuple[bool, str]:
        """Call enter() on WorldGate contract.
        
        Args:
            force: If True, skip the is_active_entry check and always send
                   the enter() transaction. Use after batchResetEntries().
        """
        if not self.contract:
            return False, "No contract address configured"
        
        try:
            account = Account.from_key(private_key)
            wallet = account.address
            
            if not force and self.is_active_entry(wallet):
                return True, "Already has active entry"
            
            # Double-check on-chain directly (bypass DEBUG_MODE)
            if force:
                try:
                    on_chain_active = self.contract.functions.isActiveEntry(
                        self.w3.to_checksum_address(wallet)
                    ).call()
                    if on_chain_active:
                        return True, "Already has active entry (on-chain confirmed)"
                except:
                    pass
            
            entry_fee = self.get_entry_fee()
            balance = self.get_balance(wallet)
            if balance < entry_fee:
                return False, f"Insufficient balance: {self.w3.from_wei(balance, 'ether')} MON, need {self.w3.from_wei(entry_fee, 'ether')} MON"
            
            nonce = self.w3.eth.get_transaction_count(wallet)
            tx = self.contract.functions.enter().build_transaction({
                'from': wallet,
                'value': entry_fee,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            return self._send_tx(private_key, tx)
        except Exception as e:
            return False, str(e)

    def set_entry_fee(self, private_key: str, new_fee_wei: int) -> Tuple[bool, str]:
        """Call setEntryFee() - owner only."""
        if not self.contract:
            return False, "No contract configured"
        try:
            account = Account.from_key(private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)
            tx = self.contract.functions.setEntryFee(new_fee_wei).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            return self._send_tx(private_key, tx)
        except Exception as e:
            return False, str(e)

    def fund_reward_pool(self, private_key: str, amount_wei: int) -> Tuple[bool, str]:
        """Call fundRewardPool() with value."""
        if not self.contract:
            return False, "No contract configured"
        try:
            account = Account.from_key(private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)
            tx = self.contract.functions.fundRewardPool().build_transaction({
                'from': account.address,
                'value': amount_wei,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            return self._send_tx(private_key, tx)
        except Exception as e:
            return False, str(e)

    def update_credits_on_chain(self, private_key: str, agent_wallet: str, credits: int) -> Tuple[bool, str]:
        """Call updateCredits() - owner/authorized server only."""
        if not self.contract:
            return False, "No contract configured"
        try:
            account = Account.from_key(private_key)
            agent_addr = self.w3.to_checksum_address(agent_wallet)
            nonce = self.w3.eth.get_transaction_count(account.address)
            tx = self.contract.functions.updateCredits(agent_addr, credits).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            return self._send_tx(private_key, tx)
        except Exception as e:
            return False, str(e)

    def get_reward_pool(self) -> int:
        """Read rewardPool balance in wei."""
        if not self.contract:
            return 0
        try:
            return self.contract.functions.rewardPool().call()
        except Exception as e:
            print(f"Error reading rewardPool: {e}")
            return 0

    def get_contract_balance(self) -> int:
        """Read total contract balance in wei."""
        if not self.contract_address:
            return 0
        try:
            return self.w3.eth.get_balance(self.w3.to_checksum_address(self.contract_address))
        except:
            return 0

    def send_mon(self, private_key: str, to_address: str, amount_wei: int) -> Tuple[bool, str]:
        """Send MON directly from one wallet to another."""
        try:
            account = Account.from_key(private_key)
            to_addr = self.w3.to_checksum_address(to_address)
            nonce = self.w3.eth.get_transaction_count(account.address)
            tx = {
                'nonce': nonce,
                'to': to_addr,
                'value': amount_wei,
                'gas': 21000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            }
            return self._send_tx(private_key, tx)
        except Exception as e:
            return False, str(e)

    def reset_entry(self, private_key: str, agent_wallet: str) -> Tuple[bool, str]:
        """Call resetEntry(agent) - owner only. Sets entry to inactive."""
        if not self.contract:
            return False, "No contract configured"
        try:
            account = Account.from_key(private_key)
            agent_addr = self.w3.to_checksum_address(agent_wallet)
            nonce = self.w3.eth.get_transaction_count(account.address)
            tx = self.contract.functions.resetEntry(agent_addr).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            return self._send_tx(private_key, tx)
        except Exception as e:
            return False, str(e)

    def batch_reset_entries(self, private_key: str, wallets: list) -> Tuple[bool, str]:
        """Call batchResetEntries() - owner only."""
        if not self.contract:
            return False, "No contract configured"
        try:
            account = Account.from_key(private_key)
            addrs = [self.w3.to_checksum_address(w) for w in wallets]
            nonce = self.w3.eth.get_transaction_count(account.address)
            tx = self.contract.functions.batchResetEntries(addrs).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            return self._send_tx(private_key, tx)
        except Exception as e:
            return False, str(e)

    def set_credit_exchange_rate(self, private_key: str, new_rate: int) -> Tuple[bool, str]:
        """Call setCreditExchangeRate() - owner only."""
        if not self.contract:
            return False, "No contract configured"
        try:
            account = Account.from_key(private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)
            tx = self.contract.functions.setCreditExchangeRate(new_rate).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            return self._send_tx(private_key, tx)
        except Exception as e:
            return False, str(e)

    def withdraw_fees(self, private_key: str) -> Tuple[bool, str]:
        """Call withdrawFees() - owner only. Withdraws entry fees (not reward pool)."""
        if not self.contract:
            return False, "No contract configured"
        try:
            account = Account.from_key(private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)
            tx = self.contract.functions.withdrawFees().build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            return self._send_tx(private_key, tx)
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
