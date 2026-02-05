// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/WorldGate.sol";

contract WorldGateTest is Test {
    WorldGate public gate;
    address public alice = address(0x1);
    address public bob = address(0x2);
    
    function setUp() public {
        gate = new WorldGate();
        vm.deal(alice, 1 ether);
        vm.deal(bob, 1 ether);
    }
    
    function test_Enter() public {
        vm.prank(alice);
        gate.enter{value: 0.05 ether}();
        
        assertTrue(gate.isActiveEntry(alice));
        
        (uint256 enteredAt, uint256 expiresAt, bool isActive) = gate.getEntry(alice);
        assertGt(enteredAt, 0);
        assertEq(expiresAt, block.timestamp + 7 days);
        assertTrue(isActive);
    }
    
    function test_EnterInsufficientFee() public {
        vm.prank(alice);
        vm.expectRevert("Insufficient fee");
        gate.enter{value: 0.01 ether}();
    }
    
    function test_EnterAlreadyActive() public {
        vm.startPrank(alice);
        gate.enter{value: 0.05 ether}();
        
        vm.expectRevert("Already in world");
        gate.enter{value: 0.05 ether}();
        vm.stopPrank();
    }
    
    function test_Expiry() public {
        vm.prank(alice);
        gate.enter{value: 0.05 ether}();
        
        assertTrue(gate.isActiveEntry(alice));
        
        // 时间流逝超过7天
        vm.warp(block.timestamp + 8 days);
        
        assertFalse(gate.isActiveEntry(alice));
    }
    
    function test_Extend() public {
        vm.startPrank(alice);
        gate.enter{value: 0.05 ether}();
        
        uint256 originalExpiry = block.timestamp + 7 days;
        
        // 续期
        gate.extend{value: 0.05 ether}();
        
        (, uint256 newExpiry,) = gate.getEntry(alice);
        assertEq(newExpiry, originalExpiry + 7 days);
        vm.stopPrank();
    }
    
    function test_ExtendAfterExpiry() public {
        vm.prank(alice);
        gate.enter{value: 0.05 ether}();
        
        // 时间流逝超过7天
        vm.warp(block.timestamp + 8 days);
        
        // 续期应该从当前时间开始
        vm.prank(alice);
        gate.extend{value: 0.05 ether}();
        
        (, uint256 newExpiry,) = gate.getEntry(alice);
        assertEq(newExpiry, block.timestamp + 7 days);
    }
}
