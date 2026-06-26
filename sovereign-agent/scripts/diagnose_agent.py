#!/usr/bin/env python3
"""Deep diagnostic for GuardianSentinel agent."""

import os, json
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
HARNESS = Web3.to_checksum_address("0x9E9488aE69f17a248520dC8D542E1ac2452Dc80B")
SENDER = w3.eth.account.from_key(os.environ["PRIVATE_KEY"]).address
TRACKER = Web3.to_checksum_address("0xC069FFCa0389f44eCA2C626e55491b0ab045AEF5")
SCHEDULER = Web3.to_checksum_address("0x5A16533e62C7F96C8dDc5E5bdBFE2bF73F399F06")

print("=" * 60)
print("  DEEP AGENT DIAGNOSTIC")
print("=" * 60)

# 1. Basic contract check
code = w3.eth.get_code(HARNESS)
print(f"\n[1] Harness contract: {len(code)} bytes {'(OK)' if len(code) > 0 else '(MISSING!)'}")

# 2. Owner check
try:
    result = w3.eth.call({"to": HARNESS, "data": "0x8da5cb5b"})
    owner = "0x" + result[-20:].hex()
    print(f"[2] Owner: {owner}")
    print(f"    Matches wallet: {'YES' if owner.lower() == SENDER.lower() else 'NO'}")
except Exception as e:
    print(f"[2] Owner check failed: {e}")

# 3. Pending job check
tracker_abi = [{"name":"hasPendingJobForSender","type":"function","stateMutability":"view",
                "inputs":[{"name":"sender","type":"address"}],"outputs":[{"name":"","type":"bool"}]}]
tracker = w3.eth.contract(address=TRACKER, abi=tracker_abi)
pending = tracker.functions.hasPendingJobForSender(HARNESS).call()
print(f"[3] Pending job for harness: {pending}")
pending_wallet = tracker.functions.hasPendingJobForSender(SENDER).call()
print(f"    Pending job for wallet: {pending_wallet}")

# 4. Check scheduler contract for our harness
print(f"\n[4] Scheduler contract: {SCHEDULER}")
sched_code = w3.eth.get_code(SCHEDULER)
print(f"    Code size: {len(sched_code)} bytes")

# 5. Check harness internal state - try common view functions
print(f"\n[5] Harness state queries:")
common_selectors = {
    "isActive()": "0x22f3e2d4",
    "getAgent()": "0xb6a0e8de", 
    "getScheduleConfig()": "0x6e947298",
    "initialized()": "0x158ef93e",
    "paused()": "0x5c975abb",
    "getRequest()": "0xc4f6b0ed",
    "schedulerConfig()": "0x4f0dcd5e",
    "lastExecutionBlock()": "0xc8f33c91",
    "getState()": "0x1865c57d",
}
for name, sig in common_selectors.items():
    try:
        result = w3.eth.call({"to": HARNESS, "data": sig})
        if len(result) > 0:
            # Try to decode as various types
            if len(result) == 32:
                as_int = int.from_bytes(result, "big")
                as_bool = as_int == 1
                if as_int <= 1:
                    print(f"    {name}: {as_bool} (bool)")
                elif as_int < 10**18:
                    print(f"    {name}: {as_int}")
                else:
                    print(f"    {name}: {as_int} (raw)")
            else:
                print(f"    {name}: {result.hex()[:80]}...")
    except Exception:
        pass  # function doesn't exist

# 6. Check RitualWallet balance
RITUAL_WALLET = Web3.to_checksum_address("0x532F0dF0896F353d8C3DD8cc134e8129DA2a3948")
bal_abi = [{"name":"balanceOf","type":"function","stateMutability":"view",
            "inputs":[{"name":"user","type":"address"}],"outputs":[{"type":"uint256"}]}]
wc = w3.eth.contract(address=RITUAL_WALLET, abi=bal_abi)
bal = w3.from_wei(wc.functions.balanceOf(HARNESS).call(), "ether")
print(f"\n[6] RitualWallet balance: {bal} RITUAL")

# 7. Transaction history
tx_count_harness = w3.eth.get_transaction_count(HARNESS)
tx_count_wallet = w3.eth.get_transaction_count(SENDER)
print(f"\n[7] Tx counts:")
print(f"    Harness nonce: {tx_count_harness}")
print(f"    Wallet nonce: {tx_count_wallet}")

# 8. Check recent blocks for any activity related to harness
print(f"\n[8] Scanning recent 10000 blocks for harness events...")
latest = w3.eth.block_number
try:
    logs = w3.eth.get_logs({"fromBlock": latest - 10000, "toBlock": "latest", "address": HARNESS})
    print(f"    Events found: {len(logs)}")
    for log in logs[:5]:
        print(f"    - Block {log.blockNumber}: {[t.hex()[:18] for t in log.topics]}")
except Exception as e:
    print(f"    Error scanning: {e}")

# 9. Check scheduler for harness events
print(f"\n[9] Scanning scheduler events for harness...")
try:
    # Topic filter for harness address in events
    logs = w3.eth.get_logs({"fromBlock": latest - 10000, "toBlock": "latest", "address": SCHEDULER})
    harness_lower = HARNESS.lower()
    related = [l for l in logs if any(harness_lower[2:] in t.hex() for t in l.topics)]
    print(f"    Scheduler events total: {len(logs)}")
    print(f"    Related to our harness: {len(related)}")
except Exception as e:
    print(f"    Error: {e}")

print(f"\n[10] Current block: {latest}")
print("=" * 60)
