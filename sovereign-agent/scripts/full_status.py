#!/usr/bin/env python3
"""Full status check for all deployed contracts."""

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
w3 = Web3(Web3.HTTPProvider(RPC_URL))

HARNESS = "0x9E9488aE69f17a248520dC8D542E1ac2452Dc80B"
WALLET = "0xDCEF810d9dd334fEBD74DF0A546cd6A57313dBb0"
AIJUDGE = "0x77331384Bb1808151C7111234464E403B4382251"
CHRONICLE = "0xC01df623EAFC95B77028ceE5c1DA69c8ED79e45E"

print(f"Current block: {w3.eth.block_number}")
print()

for name, addr in [("Wallet", WALLET), ("Harness (Agent)", HARNESS), ("AIJudge", AIJUDGE), ("RitualChronicle", CHRONICLE)]:
    cs = Web3.to_checksum_address(addr)
    bal = w3.from_wei(w3.eth.get_balance(cs), "ether")
    code_size = len(w3.eth.get_code(cs))
    tx_count = w3.eth.get_transaction_count(cs)
    is_contract = code_size > 0
    status = "CONTRACT" if is_contract else "EOA (wallet)"
    print(f"--- {name} ---")
    print(f"  Address:  {addr}")
    print(f"  Type:     {status} ({code_size} bytes)")
    print(f"  Balance:  {bal} RITUAL")
    print(f"  Tx Count: {tx_count}")
    print()

print("All checks complete.")
