#!/usr/bin/env python3
"""Register remaining 2 bots via proxy"""
import sys
import os
import httpx
import json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Set proxy (Clash for Windows on port 7890)
PROXY = "http://127.0.0.1:7890"
os.environ["HTTP_PROXY"] = PROXY
os.environ["HTTPS_PROXY"] = PROXY

MOLTBOOK_API = "https://www.moltbook.com/api/v1"

def register_agent(name: str, description: str) -> dict:
    """Register agent via proxy"""
    print(f"\n{'='*60}")
    print(f"Registering: {name}")
    print(f"Using proxy: {PROXY}")
    print('='*60)
    
    try:
        # Use proxy
        with httpx.Client(proxy=PROXY, timeout=60.0) as client:
            response = client.post(
                f"{MOLTBOOK_API}/agents/register",
                json={"name": name, "description": description}
            )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"\nSUCCESS!")
            
            agent = data.get("agent", data)
            api_key = agent.get("api_key", "N/A")
            claim_url = agent.get("claim_url", "N/A")
            verification_code = agent.get("verification_code", "N/A")
            
            print(f"  API Key: {api_key}")
            print(f"  Claim URL: {claim_url}")
            print(f"  Verification Code: {verification_code}")
            
            return {
                "name": name,
                "success": True,
                "api_key": api_key,
                "claim_url": claim_url,
                "verification_code": verification_code
            }
        else:
            result = response.json()
            error = result.get('error', 'Unknown')
            print(f"FAILED: {error}")
            return {"name": name, "success": False, "error": error}
            
    except Exception as e:
        print(f"ERROR: {e}")
        return {"name": name, "success": False, "error": str(e)}

def main():
    print("=" * 60)
    print("REGISTERING REMAINING BOTS VIA PROXY")
    print("=" * 60)
    
    bots = [
        ("PortMonad-Trader", "Trading bot from Port Monad. Buys low, sells high in the persistent world market."),
        ("PortMonad-Governor", "Governance bot from Port Monad. Proposes and votes on world rules and tax policies.")
    ]
    
    results = []
    for name, desc in bots:
        result = register_agent(name, desc)
        results.append(result)
    
    # Save results
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    successful = [r for r in results if r.get("success")]
    
    if successful:
        with open("moltbook_remaining_bots.json", "w") as f:
            json.dump(successful, f, indent=2)
        print(f"\nSaved to: moltbook_remaining_bots.json")
        
        print("\n" + "=" * 60)
        print("TWITTER VERIFICATION NEEDED")
        print("=" * 60)
        
        for bot in successful:
            print(f"\n--- {bot['name']} ---")
            print(f"Tweet: Verifying my Moltbook agent: {bot['verification_code']}")
            print(f"Claim: {bot['claim_url']}")
        
        print("\n" + "=" * 60)
        print("ADD TO .env AFTER VERIFICATION")
        print("=" * 60)
        
        # Combined with first bot
        print("""
# First bot (already registered on server):
MOLTBOOK_MINER_KEY=moltbook_sk_DQ04mbJa7wYmzzSM9YmKXRGFEJvhYq7L
""")
        for bot in successful:
            name = bot["name"]
            key = bot.get("api_key", "KEY")
            if "Trader" in name:
                print(f"MOLTBOOK_TRADER_KEY={key}")
            elif "Governor" in name:
                print(f"MOLTBOOK_GOVERNOR_KEY={key}")

if __name__ == "__main__":
    main()
