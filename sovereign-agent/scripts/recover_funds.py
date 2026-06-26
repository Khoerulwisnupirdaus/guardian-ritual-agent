#!/usr/bin/env python3
"""Check if we can withdraw funds from old harness RitualWallet."""

import os
from pathlib import Path
from web3 import Web3

def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

w3 = Web3(Web3.HTTPProvider("https://rpc.ritualfoundation.org"))
PRIVATE_KEY = os.environ["PRIVATE_KEY"]
account = w3.eth.account.from_key(PRIVATE_KEY)
sender = account.address

RITUAL_WALLET = Web3.to_checksum_address("0x532F0dF0896F353d8C3DD8cc134e8129DA2a3948")
OLD_HARNESS = Web3.to_checksum_address("0x857043f674806fa7144251BAbA625746683de0E7")

# Check balance
bal_abi = [{"name": "balanceOf", "type": "function", "stateMutability": "view",
            "inputs": [{"name": "user", "type": "address"}], "outputs": [{"type": "uint256"}]}]
wc = w3.eth.contract(address=RITUAL_WALLET, abi=bal_abi)
bal = wc.functions.balanceOf(OLD_HARNESS).call()
eth_bal = w3.from_wei(bal, "ether")
print(f"Old harness RitualWallet balance: {eth_bal} RITUAL")

if bal == 0:
    print("Nothing to withdraw.")
else:
    # Try to call withdraw through the harness
    # The harness owner should be able to call withdrawFromWallet or similar
    # Let's try calling the harness directly to withdraw
    
    # Common withdraw selectors
    withdraw_sigs = {
        "withdraw(uint256)": "0x2e1a7d4d",
        "withdrawFromWallet(uint256)": "0x7fcbc096",
        "withdrawFunds(uint256)": "0x155dd5ee",
        "emergencyWithdraw()": "0xdb2e21bc",
        "claimFunds()": "0xd63a8e11",
    }
    
    amount_hex = hex(bal)[2:].zfill(64)
    
    for name, sig in withdraw_sigs.items():
        data = sig + amount_hex if "uint256" in name else sig
        try:
            # Estimate gas to see if it would work
            w3.eth.estimate_gas({
                "from": sender,
                "to": OLD_HARNESS,
                "data": data,
            })
            print(f"  {name}: CAN CALL - attempting...")
            
            tx = {
                "from": sender,
                "to": OLD_HARNESS,
                "data": data,
                "nonce": w3.eth.get_transaction_count(sender),
                "maxFeePerGas": w3.to_wei(20, "gwei"),
                "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
                "chainId": 1979,
                "type": 2,
                "gas": 300_000,
            }
            signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            print(f"  status: {receipt.status} (1=success)")
            if receipt.status == 1:
                new_bal = wc.functions.balanceOf(OLD_HARNESS).call()
                print(f"  New balance: {w3.from_wei(new_bal, 'ether')} RITUAL")
                break
        except Exception as e:
            print(f"  {name}: reverted ({e})")
    else:
        print("\nNo withdraw function found on harness.")
        print("Funds may be locked until lock period expires (~29 days).")
