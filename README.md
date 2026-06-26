# GuardianSentinel - Ritual Chain Deployment

> Level 3 submission: Custom Smart Contract + Sovereign Agent on Ritual Chain

## Deployed Contracts

| Component | Address | Type |
|-----------|---------|------|
| **GuardianSentinel** | [`0x857043f674806fa7144251BAbA625746683de0E7`](https://explorer.ritualfoundation.org/address/0x857043f674806fa7144251BAbA625746683de0E7) | Sovereign Agent (Harness) |
| **RitualChronicle** | [`0xC01df623EAFC95B77028ceE5c1DA69c8ED79e45E`](https://explorer.ritualfoundation.org/address/0xC01df623EAFC95B77028ceE5c1DA69c8ED79e45E) | Custom Solidity Contract |

**Wallet:** `0xDCEF810d9dd334fEBD74DF0A546cd6A57313dBb0`
**Chain:** Ritual Chain (ID: 1979)

---

## Architecture

```
                    RITUAL CHAIN (Chain ID: 1979)

  +---------------------------+     +-----------------------------+
  |   RitualChronicle.sol     |     |   GuardianSentinel Agent    |
  |   (Custom Contract)       |     |   (Factory Harness)         |
  |                           |     |                             |
  |   * storeEntry(topic,txt) |     |   * Wakes every 2000 blocks |
  |   * getEntry(id)          |     |   * AI inference via 0x080C |
  |   * getRecentEntries(n)   |     |   * Custom prompt: chain    |
  |   * getEntriesByTopic()   |     |     security & monitoring   |
  |   * storeBatch()          |     |   * Results to HuggingFace  |
  |                           |     |                             |
  |   Permanent on-chain      |     |   Autonomous agent with     |
  |   AI analysis storage     |     |   unique identity           |
  +---------------------------+     +-----------------------------+
         |                                    |
         v                                    v
   Demonstrates:                     Demonstrates:
   Solidity + On-chain storage       Agent infra + TEE + ECIES
   Custom errors + Events            Factory Harness pattern
   Topic indexing + Batch ops        Scheduler + Rolling Window
```

---

## What Makes This Different

Most participants use a copy-paste script to deploy a generic agent. This submission includes:

1. **Custom Smart Contract** - `RitualChronicle.sol` with 6 public functions, custom errors, event emission, topic indexing, and batch writes. Not a template.

2. **Custom Agent Identity** - "GuardianSentinel" with a purpose-built prompt for chain security monitoring, not a default DeFi analytics template.

3. **Custom ECIES Implementation** - Wrote a from-scratch ECIES encryption module (`ecies_helper.py`) compatible with Ritual's TEE executor, because `eciespy` couldn't build on Python 3.14/Windows. Uses `eth_keys` + `pycryptodome` + `cryptography`.

4. **Original Deployment Scripts** - All scripts written from understanding, not copied from a guide repo.

---

## Project Structure

```
ritual-agent/
|-- hardhat/                        # Smart contract project
|   |-- contracts/
|   |   +-- RitualChronicle.sol     # Custom contract (Solidity 0.8.24)
|   +-- hardhat.config.ts           # Ritual Chain network configured
|
+-- sovereign-agent/                # Agent deployment
    |-- scripts/
    |   |-- deploy.py               # Sovereign agent deployer
    |   |-- deploy_chronicle.py     # Contract deployer
    |   |-- check-status.py         # Agent status checker
    |   +-- ecies_helper.py         # Custom ECIES (no coincurve)
    |-- templates/
    |   +-- guardian-sentinel.txt   # Custom agent prompt
    +-- README.md
```

---

## RitualChronicle Contract

A permanent on-chain AI chronicle. Owner writes analysis entries, anyone can read.

### Functions

| Function | Access | Description |
|----------|--------|-------------|
| `storeEntry(topic, analysis)` | Owner | Store one entry |
| `storeBatch(topics[], analyses[])` | Owner | Store multiple entries |
| `getEntry(id)` | Public | Read entry by ID |
| `getLatestEntry()` | Public | Read most recent entry |
| `getRecentEntries(count)` | Public | Read last N entries |
| `getEntriesByTopic(topic)` | Public | Get entry IDs by topic |
| `transferOwnership(newOwner)` | Owner | Transfer ownership |

### Events

```solidity
event EntryStored(uint256 indexed id, string topic, address indexed author, uint256 timestamp, uint256 blockNumber);
event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
```

---

## GuardianSentinel Agent

An autonomous on-chain intelligence agent that monitors Ritual Chain ecosystem health.

### Configuration

| Parameter | Value |
|-----------|-------|
| Frequency | 2000 blocks (~11.7 min) |
| Window | 5 calls per window |
| Model | claude-opus-4-8 |
| Funding | 0.1 RITUAL (~33 heartbeats) |
| Lock | 30 days |
| Output | HuggingFace: wzscarlet/guardianritualagent |

### Agent Mission

Each heartbeat, GuardianSentinel performs:
1. **Network Pulse** - Block height, gas trends, health rating
2. **Ecosystem Scan** - New contracts, active agents, token movements
3. **Threat Assessment** - Suspicious patterns, attack signatures
4. **Builder Intelligence** - Development trends, precompile usage, recommendations

---

## Technical Challenges Solved

| Challenge | Solution |
|-----------|----------|
| `eciespy`/`coincurve` won't build on Python 3.14 | Custom ECIES implementation using `eth_keys` + `pycryptodome` |
| Scheduler `MAX_LIFESPAN` exceeded (error `0x88abf714`) | Reduced frequency from 5000 to 2000 blocks |
| Windows cp1252 encoding crashes | All output ASCII-safe, all file reads use `encoding="utf-8"` |
| MetaMask "transaction type not supported" | Direct Python tx signing with EIP-1559 (Type 2) |

---

## Cost Breakdown

| Step | Gas | Cost (RITUAL) |
|------|-----|---------------|
| Deploy Harness | 2,319k | ~0.005 |
| Configure + Fund Agent | 5,973k | ~0.112 |
| Deploy RitualChronicle | 1,948k | ~0.004 |
| Write Genesis Entry | 461k | ~0.001 |
| **Total** | - | **~0.13** |

---

## How to Reproduce

```bash
# 1. Install dependencies
python -m pip install web3 eth-abi pycryptodome cryptography

# 2. Configure .env
cd sovereign-agent
cp .env.example .env
# Fill in: PRIVATE_KEY, OPENAI_API_KEY, HF_TOKEN, HF_REPO_ID

# 3. Deploy sovereign agent
python scripts/deploy.py

# 4. Deploy custom contract
python scripts/deploy_chronicle.py

# 5. Check status
python scripts/check-status.py
```

---

## Links

- [Ritual Explorer - GuardianSentinel](https://explorer.ritualfoundation.org/address/0x857043f674806fa7144251BAbA625746683de0E7)
- [Ritual Explorer - RitualChronicle](https://explorer.ritualfoundation.org/address/0xC01df623EAFC95B77028ceE5c1DA69c8ED79e45E)
- [HuggingFace Dataset](https://huggingface.co/datasets/wzscarlet/guardianritualagent)
- [Ritual Docs](https://docs.ritualfoundation.org)
