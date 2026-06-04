// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// SWC-101: Integer Overflow and Underflow Example
contract VulnerableToken {
    mapping(address => uint256) public balances;
    uint256 public totalSupply;

    constructor(uint256 _initialSupply) {
        totalSupply = _initialSupply;
        balances[msg.sender] = _initialSupply;
    }

    // Vulnerable: no SafeMath or overflow check
    function transfer(address _to, uint256 _value) public returns (bool) {
        require(balances[msg.sender] - _value >= 0, "Insufficient balance"); // SWC-101
        balances[msg.sender] -= _value;
        balances[_to] += _value;
        return true;
    }

    // Vulnerable: unchecked external call
    function withdraw(uint256 _amount) public {
        require(balances[msg.sender] >= _amount, "Insufficient balance");
        (bool success, ) = msg.sender.call{value: _amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= _amount; // SWC-107: Reentrancy
    }

    function getBalance(address _addr) public view returns (uint256) {
        return balances[_addr];
    }
}
