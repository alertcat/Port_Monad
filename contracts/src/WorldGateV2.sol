// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title WorldGateV2
 * @notice Port Monad - Token-gated World with Credit Cashout
 * @dev Entry fee in MON, credits can be cashed out for MON rewards
 */
contract WorldGateV2 {
    uint256 public entryFee = 1 ether;  // 1 MON (adjustable via setEntryFee)
    uint256 public entryDuration = 7 days;
    address public owner;
    
    // Credit exchange rate: 1000 credits = 0.001 MON
    uint256 public creditExchangeRate = 1000;  // credits per 0.001 MON
    uint256 public minCashout = 100;           // minimum credits to cashout
    uint256 public maxCashoutPerTx = 10000;    // max credits per cashout
    
    // Reward pool for cashouts (separate from entry fees)
    uint256 public rewardPool;
    
    struct Entry {
        uint256 enteredAt;
        uint256 expiresAt;
        bool isActive;
    }
    
    // On-chain credit balances (synced from off-chain game)
    mapping(address => uint256) public credits;
    mapping(address => Entry) public entries;
    
    // Authorized game servers that can update credits
    mapping(address => bool) public authorizedServers;
    
    event Entered(address indexed agent, uint256 expiresAt, uint256 feePaid);
    event Extended(address indexed agent, uint256 newExpiresAt);
    event FeeUpdated(uint256 oldFee, uint256 newFee);
    event CreditsUpdated(address indexed agent, uint256 oldBalance, uint256 newBalance);
    event Cashout(address indexed agent, uint256 credits, uint256 monAmount);
    event RewardPoolFunded(address indexed funder, uint256 amount);
    event ServerAuthorized(address indexed server, bool authorized);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    modifier onlyAuthorized() {
        require(msg.sender == owner || authorizedServers[msg.sender], "Not authorized");
        _;
    }
    
    constructor() {
        owner = msg.sender;
        authorizedServers[msg.sender] = true;
    }
    
    /**
     * @notice Enter the world by paying entry fee
     */
    function enter() external payable {
        require(msg.value >= entryFee, "Insufficient fee");
        require(!isActiveEntry(msg.sender), "Already in world");
        
        entries[msg.sender] = Entry({
            enteredAt: block.timestamp,
            expiresAt: block.timestamp + entryDuration,
            isActive: true
        });
        
        // Initialize credits for new players
        if (credits[msg.sender] == 0) {
            credits[msg.sender] = 1000;  // Starting credits
        }
        
        emit Entered(msg.sender, entries[msg.sender].expiresAt, msg.value);
    }
    
    /**
     * @notice Extend entry duration
     */
    function extend() external payable {
        require(msg.value >= entryFee, "Insufficient fee");
        require(entries[msg.sender].isActive, "Not in world");
        
        uint256 baseTime = entries[msg.sender].expiresAt > block.timestamp 
            ? entries[msg.sender].expiresAt 
            : block.timestamp;
        entries[msg.sender].expiresAt = baseTime + entryDuration;
        
        emit Extended(msg.sender, entries[msg.sender].expiresAt);
    }
    
    /**
     * @notice Check if address has active entry
     */
    function isActiveEntry(address agent) public view returns (bool) {
        Entry memory e = entries[agent];
        return e.isActive && e.expiresAt > block.timestamp;
    }
    
    /**
     * @notice Get entry information
     */
    function getEntry(address agent) external view returns (
        uint256 enteredAt,
        uint256 expiresAt,
        bool isActive
    ) {
        Entry memory e = entries[agent];
        return (e.enteredAt, e.expiresAt, e.isActive && e.expiresAt > block.timestamp);
    }
    
    /**
     * @notice Reset an agent's entry (owner only, for testing/new rounds)
     * @dev Sets isActive to false so the agent can re-enter and pay again
     */
    function resetEntry(address agent) external onlyOwner {
        entries[agent].isActive = false;
        entries[agent].expiresAt = 0;
    }

    /**
     * @notice Batch reset multiple agents' entries
     */
    function batchResetEntries(address[] calldata agents) external onlyOwner {
        for (uint i = 0; i < agents.length; i++) {
            entries[agents[i]].isActive = false;
            entries[agents[i]].expiresAt = 0;
        }
    }

    /**
     * @notice Update agent credits (only authorized servers)
     * @dev Called by game server to sync off-chain credits to on-chain
     */
    function updateCredits(address agent, uint256 newBalance) external onlyAuthorized {
        uint256 oldBalance = credits[agent];
        credits[agent] = newBalance;
        emit CreditsUpdated(agent, oldBalance, newBalance);
    }
    
    /**
     * @notice Batch update multiple agents' credits
     */
    function batchUpdateCredits(address[] calldata agents, uint256[] calldata balances) external onlyAuthorized {
        require(agents.length == balances.length, "Length mismatch");
        for (uint i = 0; i < agents.length; i++) {
            uint256 oldBalance = credits[agents[i]];
            credits[agents[i]] = balances[i];
            emit CreditsUpdated(agents[i], oldBalance, balances[i]);
        }
    }
    
    /**
     * @notice Cashout credits for MON from reward pool
     * @param amount Number of credits to cashout
     */
    function cashout(uint256 amount) external {
        require(isActiveEntry(msg.sender), "Not active entry");
        require(amount >= minCashout, "Below minimum cashout");
        require(amount <= maxCashoutPerTx, "Exceeds max cashout");
        require(credits[msg.sender] >= amount, "Insufficient credits");
        
        // Calculate MON amount: amount / creditExchangeRate * 0.001 ether
        uint256 monAmount = (amount * 0.001 ether) / creditExchangeRate;
        require(rewardPool >= monAmount, "Insufficient reward pool");
        
        // Deduct credits and reward pool
        credits[msg.sender] -= amount;
        rewardPool -= monAmount;
        
        // Transfer MON
        payable(msg.sender).transfer(monAmount);
        
        emit Cashout(msg.sender, amount, monAmount);
    }
    
    /**
     * @notice Fund the reward pool
     */
    function fundRewardPool() external payable {
        rewardPool += msg.value;
        emit RewardPoolFunded(msg.sender, msg.value);
    }
    
    /**
     * @notice Get cashout estimate
     */
    function getCashoutEstimate(uint256 creditAmount) external view returns (uint256 monAmount) {
        return (creditAmount * 0.001 ether) / creditExchangeRate;
    }
    
    /**
     * @notice Authorize/deauthorize a game server
     */
    function setAuthorizedServer(address server, bool authorized) external onlyOwner {
        authorizedServers[server] = authorized;
        emit ServerAuthorized(server, authorized);
    }
    
    /**
     * @notice Update entry fee (owner only)
     */
    function setEntryFee(uint256 newFee) external onlyOwner {
        emit FeeUpdated(entryFee, newFee);
        entryFee = newFee;
    }
    
    /**
     * @notice Update credit exchange rate (owner only)
     */
    function setCreditExchangeRate(uint256 newRate) external onlyOwner {
        creditExchangeRate = newRate;
    }
    
    /**
     * @notice Withdraw entry fees (not reward pool) - owner only
     */
    function withdrawFees() external onlyOwner {
        uint256 fees = address(this).balance - rewardPool;
        require(fees > 0, "No fees to withdraw");
        payable(owner).transfer(fees);
    }
    
    /**
     * @notice Emergency withdraw all (owner only)
     */
    function emergencyWithdraw() external onlyOwner {
        payable(owner).transfer(address(this).balance);
        rewardPool = 0;
    }
    
    /**
     * @notice Get contract stats
     */
    function getStats() external view returns (
        uint256 _entryFee,
        uint256 _rewardPool,
        uint256 _creditExchangeRate,
        uint256 _contractBalance
    ) {
        return (entryFee, rewardPool, creditExchangeRate, address(this).balance);
    }
}
