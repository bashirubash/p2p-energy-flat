// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract YEDCPayment {
    address public owner;

    event EnergyBought(address indexed buyer, uint256 amount);

    constructor() {
        owner = msg.sender;
    }

    // Buy energy (accept ETH)
    function buyEnergy() external payable {
        require(msg.value > 0, "Send ETH to buy energy");
        emit EnergyBought(msg.sender, msg.value);
    }

    // Withdraw contract balance to owner
    function withdraw() external {
        require(msg.sender == owner, "Only owner can withdraw");
        payable(owner).transfer(address(this).balance);
    }
}
