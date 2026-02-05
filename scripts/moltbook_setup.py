#!/usr/bin/env python3
"""
Moltbook Agent Setup Script

This script helps you:
1. Register agents on Moltbook
2. Get API keys
3. Test posting/commenting
"""
import os
import json
import httpx
from pathlib import Path

# IMPORTANT: Always use www.moltbook.com to avoid 307 redirect issues
MOLTBOOK_API = "https://www.moltbook.com/api/v1"

def register_agent(name: str, description: str) -> dict:
    """
    Register a new agent on Moltbook
    Returns: {"api_key": "...", "claim_url": "...", "verification_code": "..."}
    """
    print(f"\n{'='*50}")
    print(f"Registering agent: {name}")
    print('='*50)
    
    response = httpx.post(
        f"{MOLTBOOK_API}/agents/register",
        json={
            "name": name,
            "description": description
        },
        timeout=30.0
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ SUCCESS!")
        print(f"   API Key: {data.get('api_key', 'N/A')[:20]}...")
        print(f"   Claim URL: {data.get('claim_url', 'N/A')}")
        print(f"   Verification Code: {data.get('verification_code', 'N/A')}")
        return data
    else:
        print(f"❌ FAILED: {response.text}")
        return {}

def test_post(api_key: str, title: str, content: str) -> dict:
    """Test posting to Moltbook"""
    print(f"\n{'='*50}")
    print(f"Testing post...")
    print('='*50)
    
    response = httpx.post(
        f"{MOLTBOOK_API}/posts",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "submolt": "general",
            "title": title,
            "content": content
        },
        timeout=30.0
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code in [200, 201]:
        data = response.json()
        print(f"✅ Post created!")
        print(f"   Post ID: {data.get('id', 'N/A')}")
        return data
    else:
        print(f"❌ FAILED: {response.text}")
        return {}

def test_comment(api_key: str, post_id: str, content: str) -> dict:
    """Test commenting on a post"""
    print(f"\n{'='*50}")
    print(f"Testing comment on post {post_id}...")
    print('='*50)
    
    response = httpx.post(
        f"{MOLTBOOK_API}/posts/{post_id}/comments",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "content": content
        },
        timeout=30.0
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code in [200, 201]:
        data = response.json()
        print(f"✅ Comment created!")
        return data
    else:
        print(f"❌ FAILED: {response.text}")
        return {}

def save_credentials(agents: dict, path: str = None):
    """Save agent credentials to file"""
    if path is None:
        path = Path.home() / ".config" / "moltbook" / "credentials.json"
    
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w') as f:
        json.dump(agents, f, indent=2)
    
    print(f"\n✅ Credentials saved to: {path}")

def main():
    print("=" * 60)
    print("MOLTBOOK AGENT SETUP")
    print("=" * 60)
    
    # Define agents to register
    agents_to_register = [
        {
            "name": "PortMonadWorldHost",
            "description": "Port Monad world host. Posts tick summaries, market updates, and world events."
        },
        {
            "name": "PortMonadMiner",
            "description": "Mining bot in Port Monad. Harvests resources and trades at market."
        },
        {
            "name": "PortMonadTrader",
            "description": "Trading bot in Port Monad. Buys low, sells high."
        },
        {
            "name": "PortMonadGovernor",
            "description": "Governance bot in Port Monad. Proposes and votes on world rules."
        }
    ]
    
    registered = {}
    
    for agent in agents_to_register:
        result = register_agent(agent["name"], agent["description"])
        if result:
            registered[agent["name"]] = result
    
    if registered:
        # Save credentials
        save_credentials(registered)
        
        # Print summary
        print("\n" + "=" * 60)
        print("REGISTRATION SUMMARY")
        print("=" * 60)
        
        for name, data in registered.items():
            print(f"\n{name}:")
            print(f"  API Key: {data.get('api_key', 'N/A')[:30]}...")
            print(f"  Claim URL: {data.get('claim_url', 'Use Twitter to verify')}")
            print(f"  Verification Code: {data.get('verification_code', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("NEXT STEPS")
        print("=" * 60)
        print("""
1. For EACH agent, post a tweet containing the verification_code
   Example tweet: "Verifying my Moltbook agent: [verification_code]"

2. After tweeting, visit the claim_url to complete verification

3. Once verified, you can use the API keys to post/comment

4. Update your .env file with the API keys:
   MOLTBOOK_HOST_KEY=xxx
   MOLTBOOK_MINER_KEY=xxx
   MOLTBOOK_TRADER_KEY=xxx
   MOLTBOOK_GOVERNOR_KEY=xxx
""")

if __name__ == "__main__":
    main()
