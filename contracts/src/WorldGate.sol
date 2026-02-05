// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title WorldGate
 * @notice Port Monad 入场门禁合约
 * @dev 收取 MON 作为入场费，记录有效期
 */
contract WorldGate {
    uint256 public entryFee = 0.05 ether;  // 0.05 MON
    uint256 public entryDuration = 7 days;
    address public owner;
    
    struct Entry {
        uint256 enteredAt;
        uint256 expiresAt;
        bool isActive;
    }
    
    mapping(address => Entry) public entries;
    
    event Entered(address indexed agent, uint256 expiresAt, uint256 feePaid);
    event Extended(address indexed agent, uint256 newExpiresAt);
    event FeeUpdated(uint256 oldFee, uint256 newFee);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    constructor() {
        owner = msg.sender;
    }
    
    /**
     * @notice 入场：支付费用进入世界
     */
    function enter() external payable {
        require(msg.value >= entryFee, "Insufficient fee");
        require(!isActiveEntry(msg.sender), "Already in world");
        
        entries[msg.sender] = Entry({
            enteredAt: block.timestamp,
            expiresAt: block.timestamp + entryDuration,
            isActive: true
        });
        
        emit Entered(msg.sender, entries[msg.sender].expiresAt, msg.value);
    }
    
    /**
     * @notice 续期：延长有效期
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
     * @notice 检查是否为有效入场者
     */
    function isActiveEntry(address agent) public view returns (bool) {
        Entry memory e = entries[agent];
        return e.isActive && e.expiresAt > block.timestamp;
    }
    
    /**
     * @notice 获取入场信息
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
     * @notice 更新入场费（仅owner）
     */
    function setEntryFee(uint256 newFee) external onlyOwner {
        emit FeeUpdated(entryFee, newFee);
        entryFee = newFee;
    }
    
    /**
     * @notice 提取合约余额（仅owner）
     */
    function withdraw() external onlyOwner {
        payable(owner).transfer(address(this).balance);
    }
}
