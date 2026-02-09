# PowerShell test script for remote API via Nginx

$API_URL = "http://43.156.62.248"

Write-Host "========================================"
Write-Host "Port Monad Remote API Test"
Write-Host "========================================"
Write-Host ""

# 1. Health check
Write-Host "[1/6] Health check..."
try {
    $response = Invoke-RestMethod -Uri "$API_URL/health" -Method Get
    $response | ConvertTo-Json
} catch {
    Write-Host "Failed: $_"
}
Write-Host ""

# 2. View world state
Write-Host "[2/6] World state..."
try {
    $response = Invoke-RestMethod -Uri "$API_URL/world/state" -Method Get
    Write-Host "Tick: $($response.tick)"
    Write-Host "Agent Count: $($response.agent_count)"
    Write-Host "Market Prices:"
    $response.market_prices | ConvertTo-Json
} catch {
    Write-Host "Failed: $_"
}
Write-Host ""

# 3. Register test agent
Write-Host "[3/6] Registering test agent..."
$TEST_WALLET = "0xJudgeTest$(Get-Date -Format 'yyyyMMddHHmmss')"
$body = @{
    wallet = $TEST_WALLET
    name = "JudgeBot"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$API_URL/register" -Method Post -Body $body -ContentType "application/json"
    $response | ConvertTo-Json
} catch {
    Write-Host "Failed: $_"
}
Write-Host ""

# 4. Check agent state
Write-Host "[4/6] Agent state..."
try {
    $response = Invoke-RestMethod -Uri "$API_URL/agent/$TEST_WALLET/state" -Method Get
    $response | ConvertTo-Json
} catch {
    Write-Host "Failed: $_"
}
Write-Host ""

# 5. Submit action (move)
Write-Host "[5/6] Submitting action (move)..."
$actionBody = @{
    actor = $TEST_WALLET
    action = "move"
    params = @{ target = "market" }
} | ConvertTo-Json

$headers = @{
    "X-Wallet" = $TEST_WALLET
    "Content-Type" = "application/json"
}

try {
    $response = Invoke-RestMethod -Uri "$API_URL/action" -Method Post -Body $actionBody -Headers $headers
    $response | ConvertTo-Json
} catch {
    Write-Host "Failed: $_"
}
Write-Host ""

# 6. Check agent state again
Write-Host "[6/6] Agent state after action..."
try {
    $response = Invoke-RestMethod -Uri "$API_URL/agent/$TEST_WALLET/state" -Method Get
    Write-Host "Region: $($response.region)"
    Write-Host "Energy: $($response.energy)"
} catch {
    Write-Host "Failed: $_"
}
Write-Host ""

Write-Host "========================================"
Write-Host "Test Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "API Docs: $API_URL/docs"
Write-Host "Contract: https://testnet.monadvision.com/address/0xA725EEE1aA9D5874A2Bba70279773856dea10b7c"
