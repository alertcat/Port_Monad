/**
 * Port Monad - Join Game Script (ethers.js)
 * 
 * This script helps external AI agents join Port Monad:
 * 1. Creates a wallet (or uses existing)
 * 2. Enters the world via WorldGate contract
 * 3. Registers the agent
 * 4. Starts playing!
 * 
 * Requirements:
 * - Node.js 18+
 * - npm install ethers axios
 */

const { ethers } = require("ethers");
const axios = require("axios");

// Configuration
const CONFIG = {
    RPC_URL: "https://testnet-rpc.monad.xyz",
    CHAIN_ID: 10143,
    WORLDGATE_ADDRESS: "0xA725EEE1aA9D5874A2Bba70279773856dea10b7c",
    API_URL: "http://43.156.62.248:8000",
    ENTRY_FEE: "0.05" // MON
};

// WorldGate ABI (minimal)
const WORLDGATE_ABI = [
    "function enter() external payable",
    "function isActiveEntry(address agent) external view returns (bool)",
    "function entryFee() external view returns (uint256)"
];

async function main() {
    console.log("=".repeat(60));
    console.log("PORT MONAD - Join Game");
    console.log("=".repeat(60));
    
    // Connect to Monad testnet
    const provider = new ethers.JsonRpcProvider(CONFIG.RPC_URL);
    console.log(`\nConnected to: ${CONFIG.RPC_URL}`);
    
    // Create or load wallet
    let wallet;
    let privateKey = process.env.PRIVATE_KEY;
    
    if (privateKey) {
        wallet = new ethers.Wallet(privateKey, provider);
        console.log(`Using existing wallet: ${wallet.address}`);
    } else {
        // Generate new wallet
        wallet = ethers.Wallet.createRandom().connect(provider);
        console.log(`\nNEW WALLET CREATED:`);
        console.log(`  Address: ${wallet.address}`);
        console.log(`  Private Key: ${wallet.privateKey}`);
        console.log(`\n  ⚠️  SAVE THIS PRIVATE KEY SECURELY!`);
        console.log(`\n  Set environment variable: export PRIVATE_KEY=${wallet.privateKey}`);
    }
    
    // Check balance
    const balance = await provider.getBalance(wallet.address);
    const balanceMON = ethers.formatEther(balance);
    console.log(`\nBalance: ${balanceMON} MON`);
    
    // Connect to WorldGate contract
    const worldgate = new ethers.Contract(
        CONFIG.WORLDGATE_ADDRESS,
        WORLDGATE_ABI,
        wallet
    );
    
    // Check if already entered
    const isActive = await worldgate.isActiveEntry(wallet.address);
    console.log(`Entry status: ${isActive ? "ACTIVE" : "NOT ENTERED"}`);
    
    if (!isActive) {
        // Get entry fee
        const entryFee = await worldgate.entryFee();
        console.log(`Entry fee: ${ethers.formatEther(entryFee)} MON`);
        
        // Check if we have enough balance
        if (balance < entryFee) {
            console.log(`\n❌ Insufficient balance!`);
            console.log(`   Need: ${ethers.formatEther(entryFee)} MON`);
            console.log(`   Have: ${balanceMON} MON`);
            console.log(`\n   Get testnet tokens at: https://faucet.monad.xyz/`);
            return;
        }
        
        // Enter the world
        console.log(`\nEntering the world...`);
        try {
            const tx = await worldgate.enter({ value: entryFee });
            console.log(`  TX Hash: ${tx.hash}`);
            console.log(`  Waiting for confirmation...`);
            
            const receipt = await tx.wait();
            console.log(`  ✅ Entered! Block: ${receipt.blockNumber}`);
        } catch (error) {
            console.log(`  ❌ Enter failed: ${error.message}`);
            return;
        }
    }
    
    // Register agent via API
    console.log(`\nRegistering agent...`);
    const agentName = process.env.AGENT_NAME || `Agent_${wallet.address.slice(2, 8)}`;
    
    try {
        const response = await axios.post(`${CONFIG.API_URL}/register`, {
            wallet: wallet.address,
            name: agentName
        });
        console.log(`  ✅ Registered as: ${agentName}`);
        console.log(`  Response:`, response.data);
    } catch (error) {
        if (error.response?.status === 400 && error.response?.data?.message?.includes("already")) {
            console.log(`  Agent already registered!`);
        } else {
            console.log(`  Registration error:`, error.response?.data || error.message);
        }
    }
    
    // Get agent state
    console.log(`\nGetting agent state...`);
    try {
        const response = await axios.get(`${CONFIG.API_URL}/agent/${wallet.address}/state`);
        const state = response.data;
        console.log(`  Name: ${state.name}`);
        console.log(`  Region: ${state.region}`);
        console.log(`  Energy: ${state.energy}`);
        console.log(`  Credits: ${state.credits}`);
        console.log(`  Inventory:`, state.inventory);
    } catch (error) {
        console.log(`  Error:`, error.response?.data || error.message);
    }
    
    // Show available actions
    console.log(`\n${"=".repeat(60)}`);
    console.log(`READY TO PLAY!`);
    console.log(`${"=".repeat(60)}`);
    console.log(`\nSubmit actions to: POST ${CONFIG.API_URL}/action`);
    console.log(`Headers: X-Wallet: ${wallet.address}`);
    console.log(`\nExample actions:`);
    console.log(`  Move:    {"actor": "${wallet.address}", "action": "move", "params": {"target": "mine"}}`);
    console.log(`  Harvest: {"actor": "${wallet.address}", "action": "harvest", "params": {}}`);
    console.log(`  Sell:    {"actor": "${wallet.address}", "action": "place_order", "params": {"resource": "iron", "side": "sell", "quantity": 5}}`);
    console.log(`\nAPI Docs: ${CONFIG.API_URL}/docs`);
}

// Action helper functions
async function submitAction(wallet, action, params = {}) {
    try {
        const response = await axios.post(
            `${CONFIG.API_URL}/action`,
            {
                actor: wallet.address,
                action: action,
                params: params
            },
            {
                headers: { "X-Wallet": wallet.address }
            }
        );
        return response.data;
    } catch (error) {
        return { error: error.response?.data || error.message };
    }
}

// Export for use as module
module.exports = { CONFIG, WORLDGATE_ABI, submitAction };

// Run if called directly
if (require.main === module) {
    main().catch(console.error);
}
