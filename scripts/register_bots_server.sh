#!/bin/bash
# Run this on your server (43.156.62.248)
# Usage: bash register_bots_server.sh

echo "=============================================="
echo "MOLTBOOK BOT REGISTRATION (Server)"
echo "=============================================="

DATE=$(date +%m%d)

# Bot 1: Miner
echo ""
echo "--- Registering MinerBot ---"
MINER_RESULT=$(curl -s -X POST https://www.moltbook.com/api/v1/agents/register \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"PortMonadMiner${DATE}\",\"description\":\"Mining bot in Port Monad. Harvests resources, trades at market.\"}")
echo "Miner: $MINER_RESULT"
echo "$MINER_RESULT" > moltbook_miner.json

# Wait to avoid rate limit
sleep 2

# Bot 2: Trader
echo ""
echo "--- Registering TraderBot ---"
TRADER_RESULT=$(curl -s -X POST https://www.moltbook.com/api/v1/agents/register \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"PortMonadTrader${DATE}\",\"description\":\"Trading bot in Port Monad. Buys low, sells high.\"}")
echo "Trader: $TRADER_RESULT"
echo "$TRADER_RESULT" > moltbook_trader.json

sleep 2

# Bot 3: Governor
echo ""
echo "--- Registering GovernorBot ---"
GOVERNOR_RESULT=$(curl -s -X POST https://www.moltbook.com/api/v1/agents/register \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"PortMonadGovernor${DATE}\",\"description\":\"Governance bot in Port Monad. Proposes world rules.\"}")
echo "Governor: $GOVERNOR_RESULT"
echo "$GOVERNOR_RESULT" > moltbook_governor.json

echo ""
echo "=============================================="
echo "DONE! Check the JSON files for credentials"
echo "=============================================="
echo ""
echo "Files created:"
echo "  - moltbook_miner.json"
echo "  - moltbook_trader.json"
echo "  - moltbook_governor.json"
echo ""
echo "Next steps:"
echo "1. For each bot, tweet the verification_code"
echo "2. Visit the claim_url to complete verification"
echo "3. Add API keys to your .env file"
