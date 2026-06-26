# 🔧 Guide: Setup & Langkah Kerja Step-by-Step

## Langkah 1: Fork & Clone Repo

```bash
# Fork repo di GitHub terlebih dahulu, lalu:
git clone https://github.com/<USERNAME-KAMU>/ritual-chain-workshop.git
cd ritual-chain-workshop
```

---

## Langkah 2: Setup Hardhat (Smart Contract)

```bash
cd hardhat
pnpm install          # Install dependencies

# Cek semua berjalan
npx hardhat compile   # Compile contracts
```

### File yang perlu dimodifikasi:
```
hardhat/contracts/AIJudge.sol    ← Contract utama, TAMBAH commit-reveal logic
```

### File yang TIDAK perlu diubah:
```
hardhat/contracts/utils/PrecompileConsumer.sol   ← Base contract (jangan diubah)
hardhat/hardhat.config.ts                         ← Config sudah siap
```

---

## Langkah 3: Modifikasi Smart Contract

### 3a. Buka `hardhat/contracts/AIJudge.sol`

### 3b. Tambah state variables baru:

```solidity
// Tambah di bawah MAX_ANSWER_LENGTH
uint256 public constant REVEAL_WINDOW = 1 days;

// Tambah di bawah mapping bounties
mapping(uint256 => mapping(address => bytes32)) public commitments;
mapping(uint256 => mapping(address => bool)) public hasCommitted;
mapping(uint256 => mapping(address => bool)) public hasRevealed;
mapping(uint256 => uint256) public commitCount;
```

### 3c. Tambah fungsi `submitCommitment`:

```solidity
function submitCommitment(uint256 bountyId, bytes32 commitment) external {
    Bounty storage bounty = bounties[bountyId];
    require(bounty.owner != address(0), "Bounty does not exist");
    require(block.timestamp < bounty.deadline, "Submission deadline passed");
    require(!hasCommitted[bountyId][msg.sender], "Already committed");
    require(commitCount[bountyId] < MAX_SUBMISSIONS, "Max submissions reached");

    commitments[bountyId][msg.sender] = commitment;
    hasCommitted[bountyId][msg.sender] = true;
    commitCount[bountyId]++;

    emit CommitmentSubmitted(bountyId, msg.sender);
}
```

### 3d. Tambah fungsi `revealAnswer`:

```solidity
function revealAnswer(
    uint256 bountyId,
    string calldata answer,
    bytes32 salt
) external {
    Bounty storage bounty = bounties[bountyId];
    require(block.timestamp >= bounty.deadline, "Reveal not started");
    require(block.timestamp < bounty.deadline + REVEAL_WINDOW, "Reveal window closed");
    require(hasCommitted[bountyId][msg.sender], "No commitment found");
    require(!hasRevealed[bountyId][msg.sender], "Already revealed");
    require(bytes(answer).length <= MAX_ANSWER_LENGTH, "Answer too long");

    // Verifikasi hash
    bytes32 expectedHash = keccak256(
        abi.encodePacked(answer, salt, msg.sender, bountyId)
    );
    require(expectedHash == commitments[bountyId][msg.sender], "Hash mismatch");

    // Simpan submission
    bounty.submissions.push(Submission({
        submitter: msg.sender,
        answer: answer
    }));
    hasRevealed[bountyId][msg.sender] = true;

    emit AnswerSubmitted(bountyId, bounty.submissions.length - 1, msg.sender);
}
```

### 3e. Modifikasi `judgeAll`:

```solidity
function judgeAll(uint256 bountyId, bytes calldata llmInput) external {
    Bounty storage bounty = bounties[bountyId];
    require(msg.sender == bounty.owner, "Only owner");
    require(block.timestamp >= bounty.deadline + REVEAL_WINDOW, "Reveal still open");
    require(!bounty.judged, "Already judged");
    require(bounty.submissions.length > 0, "No revealed submissions");

    // Panggil Ritual LLM precompile
    // ... (existing logic untuk LLM call)

    bounty.judged = true;
    emit AllAnswersJudged(bountyId);
}
```

### 3f. Tambah events baru:

```solidity
event CommitmentSubmitted(uint256 indexed bountyId, address indexed submitter);
```

### 3g. Hapus/disable fungsi submit lama:

Fungsi `submitAnswer` yang asli (kirim plaintext langsung) harus **dihapus** atau di-comment.

---

## Langkah 4: Tulis Tests

Buat file test baru:

```bash
# Buat file test (Hardhat 3 style)
touch hardhat/test/AIJudge.test.ts
```

### Contoh structure test:

```typescript
import { describe, it } from "node:test";
import assert from "node:assert";
import { keccak256, encodePacked } from "viem";

describe("AIJudge Commit-Reveal", () => {
  // Setup: deploy contract, create bounty

  it("should accept commitment before deadline", async () => {
    // ...
  });

  it("should reject commitment after deadline", async () => {
    // ...
  });

  it("should accept valid reveal after deadline", async () => {
    // ...
  });

  it("should reject reveal with wrong salt", async () => {
    // ...
  });

  it("should reject reveal with wrong answer", async () => {
    // ...
  });

  it("should reject double commitment", async () => {
    // ...
  });

  it("should allow judging after reveal window", async () => {
    // ...
  });
});
```

---

## Langkah 5: Setup Frontend (Opsional tapi Recommended)

```bash
cd web
pnpm install

# Copy environment
cp .env.example .env.local

# Edit .env.local:
# NEXT_PUBLIC_CONTRACT_ADDRESS=<alamat contract yang sudah di-deploy>
# NEXT_PUBLIC_RITUAL_RPC_URL=https://rpc.ritualfoundation.org
# NEXT_PUBLIC_RITUAL_CHAIN_ID=1979

pnpm dev   # Buka http://localhost:3000
```

### Frontend perlu diupdate untuk:
1. Halaman **Commit** — user input jawaban + generate salt + kirim hash
2. Halaman **Reveal** — user input jawaban + salt → contract verifikasi
3. Simpan salt di **localStorage** (agar user tidak lupa)
4. Update ABI di `src/abi/AIJudge.ts`

---

## Langkah 6: Deploy ke Ritual Chain

```bash
cd hardhat

# Deploy menggunakan Hardhat Ignition
npx hardhat ignition deploy ignition/modules/AIJudge.ts --network ritual
```

### Hardhat config sudah support Ritual Chain:
- RPC: `https://rpc.ritualfoundation.org`
- Chain ID: `1979`
- Solidity: `0.8.24`

---

## Langkah 7: Tulis README & Architecture Note

Buat file `README.md` di root project yang menjelaskan:

1. **Lifecycle bounty** (create → commit → reveal → judge → finalize)
2. **Cara generate commitment** (hash formula)
3. **Cara run tests**
4. **Cara deploy**
5. **Architecture diagram**

---

## Langkah 8: Jawab Reflection Question

> *"What should be public, what should stay hidden, and what should be decided by AI versus by a human in a bounty system?"*

### Contoh kerangka jawaban (5-8 kalimat):

```
1. Yang HARUS publik: bounty title, rubric, deadline, reward amount,
   dan hasil akhir (pemenang). Transparansi ini penting agar semua
   peserta tahu aturan main yang sama.

2. Yang HARUS tersembunyi: jawaban peserta selama fase submission,
   dan salt yang digunakan. Ini mencegah plagiarisme dan
   front-running.

3. Keputusan AI: Ranking dan review jawaban berdasarkan rubric.
   AI cocok untuk evaluasi objektif berdasarkan kriteria yang jelas.

4. Keputusan manusia: Finalisasi pemenang dan distribusi reward.
   Manusia tetap memiliki otoritas final karena AI bisa salah
   atau miss konteks yang nuanced.

5. Prinsip dasarnya: "Verify, don't trust" — semua keputusan harus
   bisa diaudit, tapi tidak semua data harus publik.
```

---

## Langkah 9: Submit

Submit melalui Discord:
https://discord.com/channels/1210468736205852672/1516880140867469481/1517222943229345814

### Checklist submission:
- [ ] Fork repo ✅
- [ ] Solidity contract dengan commit-reveal ✅
- [ ] README dengan lifecycle explanation ✅
- [ ] Test plan (dan/atau test code) ✅
- [ ] Architecture note ✅
- [ ] Reflection question (5-8 kalimat) ✅
- [ ] Push ke GitHub ✅
- [ ] Submit link di Discord ✅
