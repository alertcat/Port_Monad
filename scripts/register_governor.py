#!/usr/bin/env python3
"""Register Governor bot - try with different approach"""
import sys
import os
import httpx
import json
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROXY = "http://127.0.0.1:7890"
MOLTBOOK_API = "https://www.moltbook.com/api/v1"

def register():
    print("Waiting 5 seconds before retry...")
    time.sleep(5)
    
    print(f"\nRegistering: PortMonad-Governor")
    print(f"Using proxy: {PROXY}")
    
    try:
        with httpx.Client(proxy=PROXY, timeout=60.0) as client:
            response = client.post(
                f"{MOLTBOOK_API}/agents/register",
                json={
                    "name": "PortMonad-Governor",
                    "description": "Governance bot from Port Monad. Proposes and votes on world rules."
                }
            )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            agent = data.get("agent", data)
            
            result = {
                "name": "PortMonad-Governor",
                "api_key": agent.get("api_key"),
                "claim_url": agent.get("claim_url"),
                "verification_code": agent.get("verification_code")
            }
            
            print(f"\nSUCCESS!")
            print(f"  API Key: {result['api_key']}")
            print(f"  Claim URL: {result['claim_url']}")
            print(f"  Verification Code: {result['verification_code']}")
            
            with open("moltbook_governor.json", "w") as f:
                json.dump(result, f, indent=2)
            
            print(f"\nSaved to: moltbook_governor.json")
            print(f"\nTweet: Verifying my Moltbook agent: {result['verification_code']}")
            print(f"\nMOLTBOOK_GOVERNOR_KEY={result['api_key']}")
            
        else:
            print(f"FAILED: {response.text}")
            print("\nTry: Switch proxy node in Clash, then run again")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    register()
