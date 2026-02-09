#!/bin/bash
# Test script for remote API via Nginx

API_URL="http://43.156.62.248"

echo "========================================"
echo "Port Monad Remote API Test"
echo "========================================"
echo ""

# 1. Health check
echo "[1/6] Health check..."
curl -s "$API_URL/health" | jq '.' || echo "Failed"
echo ""

# 2. View world state
echo "[2/6] World state..."
curl -s "$API_URL/world/state" | jq '.tick, .agent_count, .market_prices' || echo "Failed"
echo ""

# 3. Register test agent
echo "[3/6] Registering test agent..."
TEST_WALLET="0xJudgeTest$(date +%s)"
curl -s -X POST "$API_URL/register" \
  -H "Content-Type: application/json" \
  -d "{\"wallet\": \"$TEST_WALLET\", \"name\": \"JudgeBot\"}" | jq '.'
echo ""

# 4. Check agent state
echo "[4/6] Agent state..."
curl -s "$API_URL/agent/$TEST_WALLET/state" | jq '.' || echo "Failed"
echo ""

# 5. Submit action (move)
echo "[5/6] Submitting action (move)..."
curl -s -X POST "$API_URL/action" \
  -H "Content-Type: application/json" \
  -H "X-Wallet: $TEST_WALLET" \
  -d "{
    \"actor\": \"$TEST_WALLET\",
    \"action\": \"move\",
    \"params\": {\"target\": \"market\"}
  }" | jq '.'
echo ""

# 6. Check agent state again
echo "[6/6] Agent state after action..."
curl -s "$API_URL/agent/$TEST_WALLET/state" | jq '.region, .energy' || echo "Failed"
echo ""

echo "========================================"
echo "Test Complete!"
echo "========================================"
echo ""
echo "API Docs: $API_URL/docs"
echo "Contract: https://testnet.monadvision.com/address/0xA725EEE1aA9D5874A2Bba70279773856dea10b7c"
