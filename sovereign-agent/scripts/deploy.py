#!/usr/bin/env python3
"""
GuardianSentinel — Sovereign Agent Deployment
Deploy a custom sovereign agent on Ritual Chain using the factory harness pattern.

Usage:
    python scripts/deploy.py
"""

import json
import os
import sys
from pathlib import Path

from eth_abi.abi import encode
from web3 import Web3

# Custom ECIES (no coincurve dependency)
from ecies_helper import encrypt as ecies_encrypt

# ── Load .env ──
def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print("[FAIL] .env file not found!")
        print("   Copy .env.example to .env and fill in your values.")
        sys.exit(1)
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

load_env()

# ── Config ──
RPC_URL = os.environ.get("RPC_URL", "https://rpc.ritualfoundation.org")
PRIVATE_KEY = os.environ["PRIVATE_KEY"]
HF_TOKEN = os.environ["HF_TOKEN"]
HF_REPO_ID = os.environ["HF_REPO_ID"]
CLI_TYPE = int(os.environ.get("CLI_TYPE", "5"))
SALT = os.environ.get("SALT", "guardian-ritual-sentinel")
FREQUENCY = int(os.environ.get("FREQUENCY", "5000"))
WINDOW_NUM_CALLS = int(os.environ.get("WINDOW_NUM_CALLS", "5"))
ROLLOVER_THRESHOLD_BPS = int(os.environ.get("ROLLOVER_THRESHOLD_BPS", "5000"))
FUND_AMOUNT = float(os.environ.get("FUND_AMOUNT", "0.1"))

# ── System Contracts ──
SOVEREIGN_FACTORY = "0x9dC4C054e53bCc4Ce0A0Ff09E890A7a8e817f304"
REGISTRY = "0x9644e8562cE0Fe12b4deeC4163c064A8862Bf47F"
TRACKER = "0xC069FFCa0389f44eCA2C626e55491b0ab045AEF5"

# ── Load prompt ──
def get_prompt():
    custom = os.environ.get("AGENT_PROMPT", "").strip()
    if custom:
        return custom
    prompt_path = Path(__file__).parent.parent / "templates" / "guardian-sentinel.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()
    return "You are GuardianSentinel, an autonomous AI agent on Ritual Chain."

# ── Get LLM credentials ──
def get_llm_creds():
    provider = os.environ.get("LLM_PROVIDER", "").lower()
    model = os.environ.get("MODEL", "")
    
    if provider == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if not key:
            print("[FAIL] OPENROUTER_API_KEY not set")
            sys.exit(1)
        return {"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": key, "HF_TOKEN": HF_TOKEN}, model or "google/gemini-2.5-flash"
    
    elif provider == "openai":
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            print("[FAIL] OPENAI_API_KEY not set")
            sys.exit(1)
        creds = {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": key, "HF_TOKEN": HF_TOKEN}
        # Support custom base URL (e.g., zyloo.io, other OpenAI-compatible providers)
        base_url = os.environ.get("OPENAI_BASE_URL", "")
        if base_url:
            creds["OPENAI_BASE_URL"] = base_url
        return creds, model or "gpt-4o-mini"
    
    elif provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            print("[FAIL] ANTHROPIC_API_KEY not set")
            sys.exit(1)
        return {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": key, "HF_TOKEN": HF_TOKEN}, model or "claude-sonnet-4-5-20250929"
    
    elif provider == "gemini":
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key:
            print("[FAIL] GEMINI_API_KEY not set")
            sys.exit(1)
        return {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": key, "HF_TOKEN": HF_TOKEN}, model or "gemini-2.5-flash"
    
    else:
        print(f"[FAIL] Unknown LLM_PROVIDER '{provider}'")
        print("   Options: openrouter, openai, anthropic, gemini")
        sys.exit(1)


# ── ABI fragments ──
FACTORY_ABI = [
    {
        "name": "predictHarness",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "userSalt", "type": "bytes32"},
        ],
        "outputs": [
            {"name": "harness", "type": "address"},
            {"name": "childSalt", "type": "bytes32"},
        ],
    },
    {
        "name": "deployHarness",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "userSalt", "type": "bytes32"}],
        "outputs": [{"name": "harness", "type": "address"}],
    },
]

REGISTRY_ABI = [
    {
        "name": "getServicesByCapability",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "capability", "type": "uint8"},
            {"name": "checkValidity", "type": "bool"},
        ],
        "outputs": [
            {
                "name": "",
                "type": "tuple[]",
                "components": [
                    {
                        "name": "node",
                        "type": "tuple",
                        "components": [
                            {"name": "paymentAddress", "type": "address"},
                            {"name": "teeAddress", "type": "address"},
                            {"name": "teeType", "type": "uint8"},
                            {"name": "publicKey", "type": "bytes"},
                            {"name": "endpoint", "type": "string"},
                            {"name": "certPubKeyHash", "type": "bytes32"},
                            {"name": "capability", "type": "uint8"},
                        ],
                    },
                    {"name": "isValid", "type": "bool"},
                    {"name": "workloadId", "type": "bytes32"},
                ],
            }
        ],
    }
]

TRACKER_ABI = [
    {
        "name": "hasPendingJobForSender",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "sender", "type": "address"}],
        "outputs": [{"name": "", "type": "bool"}],
    }
]

SOVEREIGN_REQUEST_TYPES = [
    "address", "uint256", "bytes", "uint64", "uint64", "string",
    "address", "bytes4", "uint256", "uint256", "uint256", "uint16",
    "string", "bytes",
    "(string,string,string)", "(string,string,string)",
    "(string,string,string)[]", "(string,string,string)",
    "string", "string[]", "uint16", "uint32", "string",
]


def send_tx(w3, tx_data, to, value=0, gas_limit=5_000_000, private_key=""):
    """Build, sign, send tx. Return receipt."""
    if isinstance(tx_data, str):
        tx_data = bytes.fromhex(tx_data[2:]) if tx_data.startswith("0x") else bytes.fromhex(tx_data)
    
    account = w3.eth.account.from_key(private_key)
    tx = {
        "from": account.address,
        "to": Web3.to_checksum_address(to),
        "value": value,
        "data": tx_data,
        "nonce": w3.eth.get_transaction_count(account.address),
        "maxFeePerGas": w3.to_wei(20, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
        "chainId": 1979,
        "type": 2,
        "gas": gas_limit,
    }
    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"  tx: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    status = "[OK]" if receipt.status == 1 else "[FAIL]"
    print(f"  status: {status} (gas used: {receipt.gasUsed:,})")
    return receipt


def main():
    print()
    print("=" * 56)
    print("  GuardianSentinel -- Sovereign Agent Deployer")
    print("=" * 56)
    print()

    # ── Init ──
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print("[FAIL] Cannot connect to Ritual Chain RPC!")
        sys.exit(1)
    
    account = w3.eth.account.from_key(PRIVATE_KEY)
    SENDER = account.address
    balance = w3.from_wei(w3.eth.get_balance(SENDER), 'ether')
    
    print(f"  Wallet:  {SENDER}")
    print(f"  Chain:   {w3.eth.chain_id}")
    print(f"  Balance: {balance:.4f} RITUAL")
    print(f"  Salt:    {SALT}")
    
    if balance < 0.15:
        print(f"\n[WARN] Balance ({balance:.4f}) might be too low. Need ~0.15 RITUAL.")

    # ── 0. Check pending jobs ──
    print(f"\n-- Pre-check: Pending Jobs --")
    tracker = w3.eth.contract(address=TRACKER, abi=TRACKER_ABI)
    pending = tracker.functions.hasPendingJobForSender(SENDER).call()
    if pending:
        print("[FAIL] Has pending async job. Wait for it to finish or use different key.")
        sys.exit(1)
    print("  [OK] No pending jobs")

    # ── 1. Predict + Deploy Harness ──
    print(f"\n-- Step 1/3: Deploy Harness --")
    factory = w3.eth.contract(address=SOVEREIGN_FACTORY, abi=FACTORY_ABI)
    user_salt_bytes = Web3.keccak(text=SALT)
    
    predicted, child_salt = factory.functions.predictHarness(SENDER, user_salt_bytes).call()
    print(f"  Predicted address: {predicted}")

    code = w3.eth.get_code(predicted)
    if code and code != b"" and code != b"\x00":
        print(f"  [OK] Harness already deployed at {predicted}")
        harness_addr = predicted
    else:
        deploy_data = factory.encode_abi("deployHarness", [user_salt_bytes])
        receipt = send_tx(w3, deploy_data, SOVEREIGN_FACTORY, gas_limit=3_000_000, private_key=PRIVATE_KEY)
        if receipt.status != 1:
            print("  [FAIL] deployHarness FAILED! (check gas limit >= 3M)")
            sys.exit(1)
        harness_addr = predicted
        print(f"  [OK] Harness deployed: {harness_addr}")

    # ── 2. Get executor + encrypt secrets ──
    print(f"\n-- Step 2/3: Build Calldata --")
    registry = w3.eth.contract(address=REGISTRY, abi=REGISTRY_ABI)
    services = registry.functions.getServicesByCapability(0, True).call()
    if not services:
        print("  [FAIL] No valid executors found in registry")
        sys.exit(1)

    node = services[0][0]
    executor = Web3.to_checksum_address(node[1])
    pub_key_bytes = bytes(node[3])
    print(f"  Executor: {executor}")

    # Encrypt secrets
    creds, model = get_llm_creds()
    secrets_json = json.dumps(creds)
    encrypted = ecies_encrypt(pub_key_bytes.hex(), secrets_json.encode())
    print(f"  Secrets encrypted ({len(encrypted)} bytes)")
    print(f"  Model: {model}")
    print(f"  Provider: {creds['LLM_PROVIDER']}")

    # Delivery selector
    delivery_selector = Web3.keccak(text="onSovereignAgentResult(bytes32,bytes)")[:4]

    # Build 23-field params
    prompt = get_prompt()
    print(f"  Prompt: {prompt[:60]}...")

    params = [
        executor,                                                    # 1. executor
        500,                                                         # 2. ttl
        b"",                                                         # 3. userPublicKey
        5,                                                           # 4. pollIntervalBlocks
        6000,                                                        # 5. maxPollBlock
        "SOVEREIGN_AGENT_TASK",                                      # 6. taskIdMarker
        Web3.to_checksum_address(harness_addr),                      # 7. deliveryTarget
        delivery_selector,                                           # 8. deliverySelector
        3_000_000,                                                   # 9. deliveryGasLimit
        1_000_000_000,                                               # 10. deliveryMaxFeePerGas
        100_000_000,                                                 # 11. deliveryMaxPriorityFeePerGas
        CLI_TYPE,                                                    # 12. cliType
        prompt,                                                      # 13. prompt
        encrypted,                                                   # 14. encryptedSecrets
        ("hf", f"{HF_REPO_ID}/sessions/session-001.jsonl", "HF_TOKEN"),  # 15. convoHistory
        ("hf", f"{HF_REPO_ID}/artifacts/", "HF_TOKEN"),                  # 16. output
        [],                                                          # 17. skills
        ("hf", f"{HF_REPO_ID}/prompts/default-system.md", ""),           # 18. systemPrompt
        model,                                                       # 19. model
        [],                                                          # 20. tools
        50,                                                          # 21. maxTurns
        8192,                                                        # 22. maxTokens
        "",                                                          # 23. rpcUrls
    ]

    # ── 3. configureFundAndStart ──
    print(f"\n-- Step 3/3: Configure, Fund & Start --")

    schedule = (
        500000,                # schedulerGas
        FREQUENCY,             # frequency
        500,                   # schedulerTtl
        w3.to_wei(20, "gwei"), # maxFeePerGas
        w3.to_wei(1, "gwei"),  # maxPriorityFeePerGas
        0,                     # value
    )

    rolling = (
        WINDOW_NUM_CALLS,      # windowNumCalls
        ROLLOVER_THRESHOLD_BPS,# rolloverThresholdBps
        1,                     # rolloverRetryEveryCalls
    )

    lock_duration = 7_400_000  # ~30 days in blocks
    scheduler_funding = w3.to_wei(FUND_AMOUNT, "ether")

    selector = bytes.fromhex("b1906702")
    schedule_tuple = "(uint32,uint32,uint32,uint256,uint256,uint256)"
    rolling_tuple = "(uint32,uint16,uint16)"
    encoded_args = encode(
        [f"({','.join(SOVEREIGN_REQUEST_TYPES)})", schedule_tuple, rolling_tuple, "uint256"],
        [params, schedule, rolling, lock_duration]
    )
    calldata = selector + encoded_args

    print(f"  Funding: {FUND_AMOUNT} RITUAL")
    print(f"  Frequency: every {FREQUENCY} blocks (~{FREQUENCY * 0.35 / 60:.1f} min)")
    receipt = send_tx(w3, calldata, harness_addr, value=scheduler_funding, gas_limit=8_000_000, private_key=PRIVATE_KEY)

    if receipt.status == 1:
        print()
        print("=" * 56)
        print("  GUARDIAN SENTINEL DEPLOYED SUCCESSFULLY!")
        print("=" * 56)
        print(f"  Harness:  {harness_addr}")
        print(f"  Schedule: every {FREQUENCY} blocks (~{FREQUENCY * 0.35 / 60:.1f} min)")
        print(f"  Model:    {model}")
        print(f"  Funding:  {FUND_AMOUNT} RITUAL")
        print(f"  Explorer: https://explorer.ritualfoundation.org/address/{harness_addr}")
        print("=" * 56)
        
        # Save harness address for check-status
        addr_file = Path(__file__).parent.parent / ".harness_address"
        addr_file.write_text(harness_addr)
        print(f"\n  Harness address saved to .harness_address")
    else:
        print(f"\n  [FAIL] configureFundAndStart FAILED!")
        print("  Try: increase gas limit or check balance")
        sys.exit(1)


if __name__ == "__main__":
    main()
