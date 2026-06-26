#!/usr/bin/env python3
"""GuardianSentinel -- Check Agent Status"""

import argparse, os, sys
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
RITUAL_WALLET = "0x532F0dF0896F353d8C3DD8cc134e8129DA2a3948"

def call_fn(w3, addr, sig, from_addr=None):
    try:
        params = {"to": Web3.to_checksum_address(addr), "data": sig}
        if from_addr:
            params["from"] = from_addr
        return w3.eth.call(params)
    except:
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--harness", help="Harness address")
    args = parser.parse_args()

    harness_input = args.harness
    if not harness_input:
        addr_file = Path(__file__).parent.parent / ".harness_address"
        if addr_file.exists():
            harness_input = addr_file.read_text().strip()
        else:
            print("[FAIL] No harness address.")
            sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    harness = Web3.to_checksum_address(harness_input)

    print()
    print("=" * 56)
    print("  GUARDIAN SENTINEL STATUS")
    print("=" * 56)
    print(f"  Harness: {harness}")
    print(f"  Explorer: https://explorer.ritualfoundation.org/address/{harness}")
    print()

    code = w3.eth.get_code(harness)
    if not code or code == b"" or code == b"\x00":
        print("  [FAIL] No contract at this address!")
        sys.exit(1)
    print(f"  [OK] Contract deployed ({len(code)} bytes)")

    # Owner
    result = call_fn(w3, harness, "0x8da5cb5b")
    if result and len(result) >= 20:
        owner = "0x" + result[-20:].hex()
        print(f"  Owner: {owner}")

    # RitualWallet balance
    abi = [{"name": "balanceOf", "type": "function", "stateMutability": "view",
            "inputs": [{"name": "user", "type": "address"}], "outputs": [{"type": "uint256"}]}]
    wc = w3.eth.contract(address=RITUAL_WALLET, abi=abi)
    bal = wc.functions.balanceOf(harness).call()
    eth_bal = w3.from_wei(bal, "ether")
    print(f"  RitualWallet Balance: {eth_bal} RITUAL")

    # Estimate heartbeats
    if bal > 0:
        heartbeats = int(bal / w3.to_wei(0.003, "ether"))
        print(f"  Estimated heartbeats: ~{heartbeats}")

    # Lock
    lock_abi = [{"name": "lockUntil", "type": "function", "stateMutability": "view",
                 "inputs": [{"name": "user", "type": "address"}], "outputs": [{"type": "uint256"}]}]
    lc = w3.eth.contract(address=RITUAL_WALLET, abi=lock_abi)
    try:
        lock_until = lc.functions.lockUntil(harness).call()
        current = w3.eth.block_number
        remaining = max(0, lock_until - current)
        days = remaining * 0.35 / 86400
        print(f"  Lock: {remaining:,} blocks (~{days:.0f} days)")
    except:
        pass

    print()
    print("=" * 56)

if __name__ == "__main__":
    main()
