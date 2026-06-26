# 📖 Reference: Contract Asli & Ritual Precompiles

## Contract Asli: AIJudge.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {PrecompileConsumer} from "./utils/PrecompileConsumer.sol";

interface IRitualWallet {
    function deposit(uint256 lockDuration) external payable;
    function depositFor(address user, uint256 lockDuration) external payable;
    function withdraw(uint256 amount) external;
    function balanceOf(address) external view returns (uint256);
    function lockUntil(address) external view returns (uint256);
}

contract AIJudge is PrecompileConsumer {
    uint256 public constant MAX_SUBMISSIONS = 10;
    uint256 public constant MAX_ANSWER_LENGTH = 2_000;

    uint256 public nextBountyId = 1;

    IRitualWallet wallet =
        IRitualWallet(0x532F0dF0896F353d8C3DD8cc134e8129DA2a3948);

    struct Submission {
        address submitter;
        string answer;          // ← MASALAH: plaintext, bisa dibaca semua orang
    }

    struct Bounty {
        address owner;
        string title;
        string rubric;
        uint256 reward;
        uint256 deadline;
        bool judged;
        bool finalized;
        bytes aiReview;
        uint256 winnerIndex;
        Submission[] submissions;
    }

    struct ConvoHistory {
        string storageType;
        string path;
        string secretsName;
    }

    mapping(uint256 => Bounty) public bounties;

    event BountyCreated(
        uint256 indexed bountyId,
        address indexed owner,
        string title,
        uint256 reward,
        uint256 deadline
    );

    event AnswerSubmitted(
        uint256 indexed bountyId,
        uint256 indexed submissionIndex,
        address indexed submitter
    );

    event AllAnswersJudged(uint256 indexed bountyId);
    // ... (rest of contract)
}
```

### Catatan Penting tentang Contract Asli:
- `Submission.answer` tersimpan sebagai **string publik** → siapa saja bisa baca
- Tidak ada mekanisme untuk menyembunyikan jawaban
- `submitAnswer` langsung menerima plaintext

---

## Ritual Precompiles Reference

```solidity
// PrecompileConsumer.sol
abstract contract PrecompileConsumer {
    // ═══════════════════════════════════════════
    // SYNCHRONOUS PRECOMPILES (instant result)
    // ═══════════════════════════════════════════
    address internal constant ONNX_PRECOMPILE       = address(0x0800);  // ML inference
    address internal constant JQ_PRECOMPILE         = address(0x0803);  // JSON parsing
    address internal constant ED25519_PRECOMPILE    = address(0x0009);  // Signature verification
    address internal constant SECP256R1_PRECOMPILE  = address(0x0100);  // Signature verification
    address internal constant TX_HASH_PRECOMPILE    = address(0x0830);  // Get tx hash

    // ═══════════════════════════════════════════
    // SHORT-RUNNING ASYNC PRECOMPILES
    // ═══════════════════════════════════════════
    address internal constant HTTP_CALL_PRECOMPILE       = address(0x0801);  // HTTP requests
    address internal constant LLM_INFERENCE_PRECOMPILE   = address(0x0802);  // ⭐ AI/LLM judging
    address internal constant DKMS_PRECOMPILE            = address(0x081B);  // 🔐 Key management

    // ═══════════════════════════════════════════
    // LONG-RUNNING ASYNC PRECOMPILES
    // ═══════════════════════════════════════════
    // (ada di contract tapi terpotong di fetch)
}
```

### Yang Paling Relevan untuk Assignment:

| Precompile | Untuk Apa |
|-----------|-----------|
| `LLM_INFERENCE_PRECOMPILE` (0x0802) | Menjalankan LLM untuk judge jawaban di TEE |
| `DKMS_PRECOMPILE` (0x081B) | Encrypt/decrypt jawaban (untuk Track 2) |
| `HTTP_CALL_PRECOMPILE` (0x0801) | Fetch data dari off-chain (opsional) |

---

## Ritual Wallet Interface

```solidity
// Digunakan untuk manage reward/deposit
IRitualWallet wallet = IRitualWallet(0x532F0dF0896F353d8C3DD8cc134e8129DA2a3948);

interface IRitualWallet {
    function deposit(uint256 lockDuration) external payable;
    function depositFor(address user, uint256 lockDuration) external payable;
    function withdraw(uint256 amount) external;
    function balanceOf(address) external view returns (uint256);
    function lockUntil(address) external view returns (uint256);
}
```

---

## Web Frontend Config

```env
# .env.local (dari .env.example)
NEXT_PUBLIC_CONTRACT_ADDRESS=        # Alamat contract yang di-deploy
NEXT_PUBLIC_RITUAL_RPC_URL=https://rpc.ritualfoundation.org
NEXT_PUBLIC_RITUAL_CHAIN_ID=1979
NEXT_PUBLIC_RITUAL_EXECUTOR_ADDRESS=0x0000000000000000000000000000000000000802
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=  # Opsional
```

---

## Keccak256 Hash Formula

```
commitment = keccak256(abi.encodePacked(answer, salt, msg.sender, bountyId))

Dimana:
├── answer      : string    → Jawaban peserta
├── salt        : bytes32   → 32 byte random (rahasia user)
├── msg.sender  : address   → Wallet address peserta
└── bountyId    : uint256   → ID bounty yang diikuti
```

### Kenapa masing-masing parameter penting:

| Parameter | Alasan dimasukkan ke hash |
|-----------|--------------------------|
| `answer` | Agar jawaban terkunci dan tidak bisa diubah setelah commit |
| `salt` | Agar orang lain tidak bisa brute-force jawaban dari hash |
| `msg.sender` | Agar orang lain tidak bisa "steal" commitment orang lain |
| `bountyId` | Agar commitment tidak bisa di-replay ke bounty lain |

---

## Links Penting

| Resource | URL |
|----------|-----|
| Repo Fork | https://github.com/cozfuttu/ritual-chain-workshop |
| VOD Workshop | https://x.com/i/broadcasts/1AxRnnVDYMrxl |
| Submit Assignment | https://discord.com/channels/1210468736205852672/1516880140867469481/1517222943229345814 |
| Ritual RPC | https://rpc.ritualfoundation.org |
| Ritual Chain ID | 1979 |
| Ritual Wallet | 0x532F0dF0896F353d8C3DD8cc134e8129DA2a3948 |
| LLM Precompile | 0x0802 |
| DKMS Precompile | 0x081B |
| FHE Precompile | 0x0807 |
| AsyncDelivery | 0x5A16214fF555848411544b005f7Ac063742f39F6 |
| Scheduler | 0x56e776BAE2DD60664b69Bd5F865F1180ffB7D58B |

---

## Async Callback Pattern (dari Docs Resmi)

Contract yang pakai precompile async (LLM, DKMS) harus implement callback:

```solidity
address constant ASYNC_DELIVERY = 0x5A16214fF555848411544b005f7Ac063742f39F6;

// Phase 1: Kirim request ke LLM
function judgeAll(uint256 bountyId, bytes calldata llmInput) external {
    (bool success, bytes memory taskIdData) = LLM_PRECOMPILE.call(llmInput);
    // Simpan taskId ↔ bountyId mapping
}

// Phase 2: Terima hasil dari AsyncDelivery
function onResult(bytes32 jobId, bytes calldata result) external {
    require(msg.sender == ASYNC_DELIVERY, "Unauthorized callback");
    // Parse AI judgment, simpan review
}
```

## Deploy ke Ritual Chain (Foundry alternative)

```bash
forge script script/Deploy.s.sol:DeployScript \
  --rpc-url https://rpc.ritualfoundation.org \
  --broadcast -vvvv
```
