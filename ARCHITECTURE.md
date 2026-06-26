# Architecture: Privacy-Preserving AI Bounty Judge

## Problem Statement

The original `AIJudge` contract stores submissions as **plaintext strings on-chain**. Since all on-chain data is publicly readable, any participant can:

1. Read existing submissions via `getSubmission()`
2. Copy the best ideas
3. Submit an improved version before the deadline

This defeats the purpose of a fair bounty competition.

## Solution: Commit-Reveal Scheme

We implement a **cryptographic commit-reveal pattern** that splits the submission process into two phases separated by a deadline.

### Phase Diagram

```
                         deadline              deadline + REVEAL_WINDOW
                            │                           │
    ┌───────────────────────┼───────────────────────────┼──────────────────────┐
    │      COMMIT PHASE     │       REVEAL PHASE        │    JUDGING PHASE     │
    │                       │                           │                      │
    │  • Accept hash only   │  • Accept answer + salt   │  • Owner calls AI    │
    │  • No plaintext       │  • Verify hash match      │  • LLM reviews all   │
    │  • Anyone can submit  │  • Store revealed answers │  • Owner finalizes   │
    │                       │                           │    winner             │
    └───────────────────────┴───────────────────────────┴──────────────────────┘
```

### Commitment Hash Construction

```
commitment = keccak256(abi.encodePacked(answer, salt, msg.sender, bountyId))
```

Each component serves a specific security purpose:

| Component | Type | Security Role |
|-----------|------|---------------|
| `answer` | `string` | Locks the answer content — cannot be changed after commit |
| `salt` | `bytes32` | Adds entropy — prevents brute-force guessing of short answers |
| `msg.sender` | `address` | Binds to submitter — prevents another address from claiming the commitment |
| `bountyId` | `uint256` | Scopes to bounty — prevents replaying a commitment across bounties |

### State Machine

```
                    createBounty()
                         │
                         ▼
              ┌─────────────────────┐
              │   BountyPhase.Commit │◀─── submitCommitment()
              └─────────┬───────────┘
                        │ block.timestamp >= deadline
                        ▼
              ┌─────────────────────┐
              │   BountyPhase.Reveal │◀─── revealAnswer()
              └─────────┬───────────┘
                        │ block.timestamp >= deadline + REVEAL_WINDOW
                        ▼
              ┌─────────────────────┐
              │  BountyPhase.Judging │◀─── judgeAll()
              └─────────┬───────────┘
                        │ finalizeWinner()
                        ▼
              ┌─────────────────────┐
              │ BountyPhase.Finalized│
              └─────────────────────┘
```

## Contract Changes from Original

### Removed
- `submitAnswer(bountyId, answer)` — accepted plaintext directly (the vulnerability)

### Added
- `submitCommitment(bountyId, commitment)` — accepts only a hash during commit phase
- `revealAnswer(bountyId, answer, salt)` — verifies hash match during reveal phase
- `getBountyPhase(bountyId)` — returns current phase of a bounty
- `BountyPhase` enum — `Commit`, `Reveal`, `Judging`, `Finalized`
- `commitments` mapping — stores hashes per bounty per address
- `hasCommitted` / `hasRevealed` mappings — prevents double actions
- `commitCount` — tracks number of commitments per bounty
- `CommitmentSubmitted` event
- `AnswerRevealed` event

### Modified
- `judgeAll()` — now requires `block.timestamp >= deadline + REVEAL_WINDOW`
- `createBounty()` — added `deadline > block.timestamp` validation
- `finalizeWinner()` — added `winnerIndex < submissions.length` validation

## Ritual Chain Integration

The contract inherits from `PrecompileConsumer` which provides access to Ritual Chain's native precompiles:

```
┌─────────────────────────────────────────────────────────────┐
│                      AIJudge Contract                       │
│                                                             │
│   inherits PrecompileConsumer                               │
│     ├── LLM_INFERENCE_PRECOMPILE (0x0802)  ← AI judging    │
│     ├── DKMS_PRECOMPILE (0x081B)           ← Key mgmt      │
│     └── ASYNC_DELIVERY (0x5A16...39F6)     ← Callbacks     │
│                                                             │
│   uses IRitualWallet (0x532F...3948)       ← Fee payment   │
└─────────────────────────────────────────────────────────────┘
```

### LLM Judging Flow

```
1. Owner calls judgeAll(bountyId, llmInput)
2. Contract calls _executePrecompile(LLM_INFERENCE_PRECOMPILE, llmInput)
3. Ritual Sidecar (TEE) receives the request
4. LLM processes all revealed submissions against the rubric
5. Result returned as bytes (AI review)
6. Contract stores aiReview and emits AllAnswersJudged event
7. Owner reads review, calls finalizeWinner(bountyId, winnerIndex)
8. Contract transfers reward to winner
```

## Security Analysis

### Attacks Prevented

| Attack | How It's Prevented |
|--------|-------------------|
| **Plagiarism** | Answers hidden during commit phase; only hash visible |
| **Front-running** | `msg.sender` in hash prevents using someone else's commitment |
| **Answer modification** | Hash locks answer at commit time; any change = different hash |
| **Cross-bounty replay** | `bountyId` in hash scopes commitment to specific bounty |
| **Brute-force guessing** | 32-byte random salt makes brute-force computationally infeasible |
| **Double submission** | `hasCommitted` mapping prevents multiple commits per address |
| **Late submission** | Deadline enforced: commit only before, reveal only after |
| **Skipped reveal** | Non-revealed commitments simply don't enter the judging pool |

### Known Limitations

1. **Reveal window is fixed** (1 day) — if a participant misses it, their submission is lost
2. **Answers become public after reveal** — this is inherent to commit-reveal on EVM
3. **Gas costs** — storing answer strings on-chain is expensive for long answers
4. **Salt responsibility** — if a user loses their salt, they cannot reveal

## Test Plan

### Happy Path
1. ✅ Create bounty with reward and future deadline
2. ✅ Submit valid commitment before deadline
3. ✅ Reveal correct answer + salt after deadline
4. ✅ Judge all submissions after reveal window
5. ✅ Finalize winner and verify reward transfer

### Security Tests
6. ❌ Commit after deadline → revert "commit phase ended"
7. ❌ Reveal before deadline → revert "reveal phase not started"
8. ❌ Reveal with wrong salt → revert "hash mismatch"
9. ❌ Reveal with wrong answer → revert "hash mismatch"
10. ❌ Double commit → revert "already committed"
11. ❌ Double reveal → revert "already revealed"
12. ❌ Reveal without commit → revert "no commitment found"
13. ❌ Reveal after window → revert "reveal window closed"
14. ❌ Judge before reveal window closes → revert "reveal window still open"
15. ❌ Non-owner calls judgeAll → revert "not bounty owner"
16. ❌ Judge with no revealed submissions → revert "no revealed submissions"
17. ❌ Empty commitment (bytes32(0)) → revert "empty commitment"
18. ❌ Finalize with invalid winner index → revert "invalid winner index"

### Edge Cases
19. ✅ Partial reveals — only revealed answers enter judging
20. ✅ Max submissions (10) reached → revert for new commits
