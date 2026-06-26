#!/usr/bin/env python3
"""Top up GuardianSentinel agent RitualWallet with 1 RITUAL - method 2."""

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

RPC_URL = os.environ.get("RPC_URL", "https://rpc.ritualfoundation.org")
PRIVATE_KEY = os.environ["PRIVATE_KEY"]

RITUAL_WALLET = Web3.to_checksum_address("0x532F0dF0896F353d8C3DD8cc134e8129DA2a3948")
HARNESS = Web3.to_checksum_address("0x9E9488aE69f17a248520dC8D542E1ac2452Dc80B")
AMOUNT = Web3.to_wei(1, "ether")  # 1 RITUAL

w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)
sender = account.address

# Check current balance first
bal_abi = [{"name": "balanceOf", "type": "function", "stateMutability": "view",
            "inputs": [{"name": "user", "type": "address"}], "outputs": [{"type": "uint256"}]}]
wc = w3.eth.contract(address=RITUAL_WALLET, abi=bal_abi)
before = w3.from_wei(wc.functions.balanceOf(HARNESS).call(), "ether")
print(f"Agent balance BEFORE: {before} RITUAL")

# Method: depositTo(address) - try multiple function signatures
# deposit(address) = 0xf340fa01
# depositTo(address) = 0xb760faf9
for sig_name, sig_hex in [("deposit(address)", "0xf340fa01"), ("depositTo(address)", "0xb760faf9")]:
    # Encode: function selector + address padded to 32 bytes
    addr_padded = HARNESS[2:].lower().zfill(64)
    data = sig_hex + addr_padded

    tx = {
        "from": sender,
        "to": RITUAL_WALLET,
        "value": AMOUNT,
        "data": data,
        "nonce": w3.eth.get_transaction_count(sender),
        "maxFeePerGas": w3.to_wei(20, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
        "chainId": 1979,
        "type": 2,
        "gas": 200_000,
    }

    try:
        # Estimate gas first to check if it will succeed
        w3.eth.estimate_gas(tx)
        print(f"Using method: {sig_name}")

        signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"tx_hash: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        print(f"status: {receipt.status} (1=success)")

        if receipt.status == 1:
            after = w3.from_wei(wc.functions.balanceOf(HARNESS).call(), "ether")
            print(f"Agent balance AFTER: {after} RITUAL")
            print("Top-up successful!")
            break
        else:
            print(f"{sig_name} reverted, trying next...")
    except Exception as e:
        print(f"{sig_name} failed estimation: {e}")
        continue
else:
    # Last resort: just send ETH directly to the RitualWallet with the harness as recipient
    print("Trying direct ETH transfer to RitualWallet...")
    tx = {
        "from": sender,
        "to": RITUAL_WALLET,
        "value": AMOUNT,
        "nonce": w3.eth.get_transaction_count(sender),
        "maxFeePerGas": w3.to_wei(20, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
        "chainId": 1979,
        "type": 2,
        "gas": 100_000,
    }
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"tx_hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    print(f"status: {receipt.status} (1=success)")
