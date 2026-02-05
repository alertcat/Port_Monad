#!/usr/bin/env python3
"""Test Moltbook integration"""
import os
import asyncio
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

API_URL = os.getenv("API_URL", "http://localhost:8000")
MOLTBOOK_APP_KEY = os.getenv("MOLTBOOK_APP_KEY", "")

async def test_moltbook_auth_endpoint():
    """Test the Moltbook auth info endpoint"""
    print("Testing Moltbook auth info endpoint...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/moltbook/auth-info")
        data = response.json()
        
        print(f"  Auth URL: {data.get('auth_url')}")
        print(f"  Header: {data.get('header')}")
        print(f"  Enabled: {data.get('enabled')}")
        print(f"  Audience: {data.get('audience')}")
        
        return data

async def test_moltbook_verification():
    """Test Moltbook identity verification (requires valid token)"""
    print("\nTesting Moltbook verification...")
    
    if not MOLTBOOK_APP_KEY:
        print("  MOLTBOOK_APP_KEY not set, skipping verification test")
        return None
    
    # This would require a real Moltbook identity token
    # For now, just test the endpoint exists
    print("  Moltbook app key configured: Yes")
    print("  To test verification, use a real Moltbook identity token")
    
    return True

async def test_api_with_wallet():
    """Test API with direct wallet authentication"""
    print("\nTesting API with wallet auth...")
    
    wallet = os.getenv("MINER_WALLET")
    if not wallet:
        print("  MINER_WALLET not set, skipping")
        return None
    
    async with httpx.AsyncClient() as client:
        # Test gate status
        response = await client.get(f"{API_URL}/gate/status/{wallet}")
        data = response.json()
        
        print(f"  Wallet: {wallet}")
        print(f"  Is Active Entry: {data.get('is_active_entry')}")
        print(f"  Balance: {data.get('balance')}")
        
        return data

async def main():
    print("=" * 50)
    print("MOLTBOOK INTEGRATION TEST")
    print("=" * 50)
    print(f"API URL: {API_URL}")
    print(f"Moltbook Key Configured: {bool(MOLTBOOK_APP_KEY)}")
    print()
    
    # Test auth endpoint
    await test_moltbook_auth_endpoint()
    
    # Test verification
    await test_moltbook_verification()
    
    # Test wallet auth
    await test_api_with_wallet()
    
    print("\n" + "=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
