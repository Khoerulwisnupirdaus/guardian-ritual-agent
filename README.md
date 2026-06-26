# Privacy-Preserving AI Bounty Judge & GuardianSentinel

This repository contains the solution for the **Ritual Academy: Privacy-Preserving AI Bounty Judge** assignment, along with an advanced **Level 3** bonus submission featuring a Sovereign Agent and a Custom Smart Contract.

## 🏆 Track 1: REQUIRED - Commit-Reveal Bounty (AIJudge)

**Deployed AIJudge Contract:** [`0x77331384Bb1808151C7111234464E403B4382251`](https://explorer.ritualfoundation.org/address/0x77331384Bb1808151C7111234464E403B4382251)  
**Deploy Tx Hash:** `0xa7954f7196d0a5c06b19c0119c2dadc76338622a9f8308f7acaab82a54f11175`

### Bounty Lifecycle
The `AIJudge` contract has been updated to prevent plagiarism and front-running by implementing a Commit-Reveal scheme. The lifecycle is:
1. **Create:** Owner creates a bounty with a rubric, reward, and deadline.
2. **Commit Phase:** Participants submit a `bytes32` hash of their answer (`keccak256(answer + salt + msg.sender + bountyId)`). No plaintext is exposed on-chain.
3. **Reveal Phase:** After the deadline, participants reveal their `answer` and `salt`. The contract verifies the hash. Only verified answers are stored.
4. **Judging Phase:** Owner triggers the Ritual LLM Precompile (`0x0802`) to evaluate all revealed answers as a batch against the rubric.
5. **Finalize:** Owner reads the AI's review and finalize the winner, transferring the reward.

> 📚 **Detailed Architecture & Test Plan:** See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the complete state machine, security analysis, and test cases.

### 💡 Reflection Question

> *"What should be public, what should stay hidden, and what should be decided by AI versus by a human in a bounty system?"*

**Answer:**
1. **Public:** The bounty rubric, rules, deadline, reward, and the final winner must be public to ensure transparency and trust in the system.
2. **Hidden:** The participants' submissions must remain hidden during the commit phase (using hashes or TEEs) to prevent plagiarism, front-running, and bias.
3. **AI Decisions:** The AI should handle objective evaluation, filtering spam, scoring against the rubric, and providing detailed analytical reviews of the submissions.
4. **Human Decisions:** Humans should handle the final approval and fund distribution, acting as an ultimate arbiter to catch AI hallucinations or nuanced context the LLM might miss.

---

## 🚀 Track 2 (Advanced) / Level 3: GuardianSentinel Sovereign Agent

In addition to the required assignment, this repository includes a fully autonomous **Sovereign Agent** deployed on Ritual Chain using the Factory Harness pattern, accompanied by a custom permanent storage contract.

| Component | Address | Type |
|-----------|---------|------|
| **GuardianSentinel** | [`0x857043f674806fa7144251BAbA625746683de0E7`](https://explorer.ritualfoundation.org/address/0x857043f674806fa7144251BAbA625746683de0E7) | Sovereign Agent (Harness) |
| **RitualChronicle** | [`0xC01df623EAFC95B77028ceE5c1DA69c8ED79e45E`](https://explorer.ritualfoundation.org/address/0xC01df623EAFC95B77028ceE5c1DA69c8ED79e45E) | Custom Solidity Contract |

### GuardianSentinel Features
- **Autonomous Execution:** Wakes up every 2000 blocks (~11.7 min) via Ritual's Scheduler.
- **Custom Identity:** Purpose-built prompt for chain security monitoring, threat assessment, and builder intelligence.
- **Custom ECIES Implementation:** Wrote a from-scratch ECIES encryption module (`ecies_helper.py`) compatible with Ritual's TEE executor using `eth_keys` + `pycryptodome` (bypassing `eciespy` installation issues on Windows).
- **HuggingFace Output:** [wzscarlet/guardianritualagent](https://huggingface.co/datasets/wzscarlet/guardianritualagent)

### RitualChronicle Contract
A custom Solidity contract (`RitualChronicle.sol`) that acts as a permanent on-chain AI chronicle. It features topic indexing, batch writes, and custom events to store the agent's insights immutably.
