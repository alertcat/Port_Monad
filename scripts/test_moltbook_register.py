#!/usr/bin/env python3
"""Test Moltbook agent registration"""
import sys
import httpx
import json

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

MOLTBOOK_API = "https://www.moltbook.com/api/v1"

def register_agent():
    """Register a new agent and get API key"""
    
    print("=" * 50)
    print("MOLTBOOK AGENT REGISTRATION")
    print("=" * 50)
    
    # Agent details
    name = "PortMonadWorldHost"
    description = "Port Monad world host. Posts tick summaries, market updates, and world events for the Port Monad persistent world on Monad blockchain."
    
    print(f"\nRegistering: {name}")
    print(f"Description: {description[:50]}...")
    
    try:
        response = httpx.post(
            f"{MOLTBOOK_API}/agents/register",
            json={
                "name": name,
                "description": description
            },
            timeout=30.0
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n" + "=" * 50)
            print("SUCCESS! Save these details:")
            print("=" * 50)
            
            api_key = data.get("api_key", "N/A")
            claim_url = data.get("claim_url", "N/A")
            verification_code = data.get("verification_code", "N/A")
            
            print(f"\nAPI Key: {api_key}")
            print(f"\nClaim URL: {claim_url}")
            print(f"\nVerification Code: {verification_code}")
            
            print("\n" + "=" * 50)
            print("NEXT STEPS:")
            print("=" * 50)
            print(f"""
1. Post this tweet (from your Twitter account):
   "Verifying my Moltbook agent: {verification_code}"

2. Visit the claim URL to complete verification:
   {claim_url}

3. Add the API key to your .env file:
   MOLTBOOK_HOST_KEY={api_key}
   MOLTBOOK_MINER_KEY={api_key}
   MOLTBOOK_TRADER_KEY={api_key}
   MOLTBOOK_GOVERNOR_KEY={api_key}

4. Run the demo:
   python scripts/run_demo.py
""")
            
            # Save to file
            with open("moltbook_credentials.json", "w") as f:
                json.dump(data, f, indent=2)
            print(f"\nCredentials saved to: moltbook_credentials.json")
            
        else:
            print(f"\nFailed: {response.text}")
            
            # Check if agent already exists
            if "already exists" in response.text.lower():
                print("\nThis agent name is already registered.")
                print("Try a different name or recover your existing API key.")
            
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    register_agent()
