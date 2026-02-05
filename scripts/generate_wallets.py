#!/usr/bin/env python3
"""Generate 3 secure random wallets for agents"""
import secrets
import hashlib

def generate_wallet():
    """Generate a wallet using cryptographically secure random"""
    # Use secrets module for cryptographic randomness
    private_key_bytes = secrets.token_bytes(32)
    private_key = '0x' + private_key_bytes.hex()
    
    # Derive address using keccak256 (simplified, need eth_account for real)
    # For proper derivation, we use eth_account
    try:
        from eth_account import Account
        acct = Account.from_key(private_key)
        return private_key, acct.address
    except ImportError:
        # Fallback: just return private key, address will be derived later
        print("Warning: eth_account not installed, returning private key only")
        return private_key, None

def main():
    print("=" * 60)
    print("Generating 3 Secure Agent Wallets")
    print("=" * 60)
    print("\nUsing secrets.token_bytes(32) for cryptographic randomness\n")
    
    agents = ['MINER', 'TRADER', 'GOVERNOR']
    
    wallets = []
    for name in agents:
        private_key, address = generate_wallet()
        wallets.append({
            'name': name,
            'private_key': private_key,
            'address': address
        })
        print(f"{name}_PRIVATE_KEY={private_key}")
        print(f"{name}_WALLET={address}")
        print()
    
    # Generate .env content
    print("=" * 60)
    print("Copy this to your .env file:")
    print("=" * 60)
    print()
    print("# Monad RPC")
    print("MONAD_RPC=https://testnet-rpc.monad.xyz")
    print()
    print("# Deploy wallet (has test MON)")
    print("DEPLOY_PRIVATE_KEY=0x568e7874e35e1a8419052976268f3038e99ab555997098cf3bd222b4ac64f04e")
    print("DEPLOY_WALLET=0x5134b47c614c7884Ad6cdebB99C7846Daf06b30C")
    print()
    print("# API")
    print("API_URL=http://localhost:8000")
    print()
    print("# Agent wallets (need testnet MON)")
    for w in wallets:
        print(f"{w['name']}_PRIVATE_KEY={w['private_key']}")
        print(f"{w['name']}_WALLET={w['address']}")
    print()
    
    return wallets

if __name__ == "__main__":
    main()
