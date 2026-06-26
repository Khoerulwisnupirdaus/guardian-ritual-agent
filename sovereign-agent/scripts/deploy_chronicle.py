#!/usr/bin/env python3
"""
Deploy RitualChronicle contract to Ritual Chain + write genesis entry.
"""

import json
import os
import sys
from pathlib import Path

from web3 import Web3

# Load env from sovereign-agent/.env
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

# Load compiled artifact
ARTIFACT_PATH = Path(__file__).parent.parent.parent / "hardhat" / "artifacts" / "contracts" / "RitualChronicle.sol" / "RitualChronicle.json"


def main():
    print()
    print("=" * 56)
    print("  RitualChronicle -- Contract Deployer")
    print("=" * 56)
    print()

    # Init
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print("[FAIL] Cannot connect to Ritual Chain RPC!")
        sys.exit(1)

    account = w3.eth.account.from_key(PRIVATE_KEY)
    sender = account.address
    balance = w3.from_wei(w3.eth.get_balance(sender), "ether")

    print(f"  Wallet:  {sender}")
    print(f"  Chain:   {w3.eth.chain_id}")
    print(f"  Balance: {balance:.4f} RITUAL")

    # Load ABI + bytecode
    if not ARTIFACT_PATH.exists():
        print(f"[FAIL] Artifact not found: {ARTIFACT_PATH}")
        print("  Run 'npx hardhat compile' in hardhat/ first.")
        sys.exit(1)

    with open(ARTIFACT_PATH) as f:
        artifact = json.load(f)

    abi = artifact["abi"]
    bytecode = artifact["bytecode"]
    print(f"  ABI: {len(abi)} entries")
    print(f"  Bytecode: {len(bytecode)} chars")

    # Deploy
    print(f"\n-- Step 1/2: Deploy Contract --")
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = contract.constructor().build_transaction({
        "from": sender,
        "nonce": w3.eth.get_transaction_count(sender),
        "maxFeePerGas": w3.to_wei(20, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
        "chainId": 1979,
        "type": 2,
        "gas": 2_000_000,
    })

    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"  tx: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    status = "[OK]" if receipt.status == 1 else "[FAIL]"
    print(f"  status: {status} (gas used: {receipt.gasUsed:,})")

    if receipt.status != 1:
        print("[FAIL] Contract deployment failed!")
        sys.exit(1)

    contract_addr = receipt.contractAddress
    print(f"  [OK] RitualChronicle deployed: {contract_addr}")

    # Write genesis entry
    print(f"\n-- Step 2/2: Write Genesis Entry --")
    chronicle = w3.eth.contract(address=contract_addr, abi=abi)

    topic = "Genesis"
    analysis = (
        "GuardianSentinel Chronicle initialized on Ritual Chain. "
        "This is the genesis entry of an autonomous on-chain AI chronicle. "
        f"Deployed by {sender} at block {receipt.blockNumber}. "
        "Companion agent: 0x857043f674806fa7144251BAbA625746683de0E7. "
        "Mission: permanent, immutable record of AI-generated chain intelligence."
    )

    store_tx = chronicle.functions.storeEntry(topic, analysis).build_transaction({
        "from": sender,
        "nonce": w3.eth.get_transaction_count(sender),
        "maxFeePerGas": w3.to_wei(20, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
        "chainId": 1979,
        "type": 2,
        "gas": 500_000,
    })

    signed2 = w3.eth.account.sign_transaction(store_tx, PRIVATE_KEY)
    tx_hash2 = w3.eth.send_raw_transaction(signed2.raw_transaction)
    print(f"  tx: {tx_hash2.hex()}")

    receipt2 = w3.eth.wait_for_transaction_receipt(tx_hash2, timeout=180)
    status2 = "[OK]" if receipt2.status == 1 else "[FAIL]"
    print(f"  status: {status2} (gas used: {receipt2.gasUsed:,})")

    # Verify
    if receipt2.status == 1:
        entry = chronicle.functions.getEntry(0).call()
        print(f"\n  Genesis entry verified:")
        print(f"    ID: {entry[0]}")
        print(f"    Topic: {entry[3]}")
        print(f"    Block: {entry[2]}")

    # Summary
    print()
    print("=" * 56)
    print("  RITUAL CHRONICLE DEPLOYED SUCCESSFULLY!")
    print("=" * 56)
    print(f"  Contract: {contract_addr}")
    print(f"  Entries:  1 (genesis)")
    print(f"  Explorer: https://explorer.ritualfoundation.org/address/{contract_addr}")
    print("=" * 56)

    # Save address
    addr_file = Path(__file__).parent.parent / ".chronicle_address"
    addr_file.write_text(contract_addr)
    print(f"\n  Address saved to .chronicle_address")


if __name__ == "__main__":
    main()
