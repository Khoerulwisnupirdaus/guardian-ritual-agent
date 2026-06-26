# 🛡️ GuardianSentinel — Sovereign Agent on Ritual Chain

An autonomous AI agent deployed on Ritual Chain (Chain ID: 1979) using the Factory Harness pattern.

## What is this?

GuardianSentinel is a **sovereign on-chain AI agent** that autonomously monitors and analyzes the Ritual Chain ecosystem. Every ~29 minutes, it:

1. Wakes up via the Scheduler
2. Runs AI inference (Claude/GPT/Gemini) inside a TEE (Trusted Execution Environment)
3. Generates an ecosystem health report
4. Stores results on HuggingFace and delivers callback on-chain

## Architecture

```
Your Wallet ──deployHarness──▶ SovereignAgentFactory (0x9dC4...304)
    │                                    │
    │                              CREATE3 deploy
    │                                    ▼
    │                         GuardianSentinel Harness
    │  configureFundAndStart         │
    └───────────────────────────────▶│
                                     │  wakeUp() every 5000 blocks
                                     ▼
                              Precompile 0x080C ──TEE──▶ AI Model
                                     │
                                     │  Phase 2 callback
                                     ▼
                              Harness ◀── onSovereignAgentResult
```

## Deploy

```bash
# 1. Install dependencies
pip install web3 eciespy eth-abi

# 2. Configure .env (fill in your private key)
# See .env file

# 3. Deploy
python scripts/deploy.py

# 4. Check status
python scripts/check-status.py
```

## Cost

| Step | Cost |
|------|------|
| Deploy Harness | ~0.005 RITUAL |
| Configure + Fund | ~0.12 RITUAL |
| Per heartbeat | ~0.002 RITUAL |
| **Total setup** | **~0.13 RITUAL** |

## Custom Prompt

GuardianSentinel uses a unique prompt (see `templates/guardian-sentinel.txt`) that focuses on:
- Network health monitoring
- Threat assessment
- Builder intelligence
- Ecosystem scanning

This is NOT a generic template — it's purpose-built for chain security monitoring.

## Files

```
sovereign-agent/
├── .env                              # Configuration (DO NOT commit)
├── .gitignore
├── README.md                         # This file
├── scripts/
│   ├── deploy.py                     # Full deployment script
│   └── check-status.py              # Check harness status
└── templates/
    └── guardian-sentinel.txt          # Custom agent prompt
```

## Built on Ritual Chain

- Chain ID: 1979
- Block time: ~350ms
- Precompile: 0x080C (Sovereign Agent)
- Factory: 0x9dC4C054e53bCc4Ce0A0Ff09E890A7a8e817f304
