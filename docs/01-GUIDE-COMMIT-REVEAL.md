# 🔐 Guide Track 1: Commit-Reveal Bounty (REQUIRED)

## Apa itu Commit-Reveal?

Commit-Reveal adalah **pattern kriptografi** yang menjaga kerahasiaan data sampai waktu yang ditentukan.

```
┌─────────────────────────────────────────────────────────────────┐
│                     TIMELINE BOUNTY                             │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐ │
│  │  CREATE   │───▶│  COMMIT  │───▶│  REVEAL  │───▶│  JUDGING  │ │
│  │  BOUNTY   │    │  PHASE   │    │  PHASE   │    │  + FINAL  │ │
│  └──────────┘    └──────────┘    └──────────┘    └───────────┘ │
│                                                                 │
│  Owner buat      Peserta kirim   Peserta buka    AI judge +     │
│  bounty +        hash saja       jawaban asli    owner pilih    │
│  reward          (rahasia!)      + salt          pemenang       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Fase 1: COMMIT (Submission Phase)

**Peserta TIDAK mengirim jawaban plaintext.** Mereka hanya mengirim **hash** dari jawabannya.

### Cara membuat commitment hash:

```solidity
// Di sisi client (JavaScript/TypeScript):
commitment = keccak256(abi.encodePacked(answer, salt, msg.sender, bountyId))
```

- `answer` → Jawaban peserta (string)
- `salt` → Random bytes32 yang hanya peserta tahu (rahasia!)
- `msg.sender` → Address peserta (mencegah orang lain pakai hash yang sama)
- `bountyId` → ID bounty (mencegah replay ke bounty lain)

### Fungsi yang dipanggil:

```solidity
function submitCommitment(uint256 bountyId, bytes32 commitment) external {
    // Validasi:
    // - Bounty masih dalam deadline (block.timestamp < deadline)
    // - Peserta belum pernah commit untuk bounty ini
    // - Jumlah submission belum melebihi MAX_SUBMISSIONS

    // Simpan commitment
    commitments[bountyId][msg.sender] = commitment;
    committed[bountyId][msg.sender] = true;
}
```

### Apa yang on-chain saat ini?
- ✅ `bytes32 commitment` (hash) → **aman, tidak bisa di-reverse**
- ✅ `address submitter` → siapa yang commit
- ❌ Jawaban plaintext → **TIDAK tersimpan**

---

## Fase 2: REVEAL (Setelah Deadline)

Setelah deadline submission berakhir, peserta **membuka** jawaban mereka dengan memberikan data asli.

### Fungsi yang dipanggil:

```solidity
function revealAnswer(
    uint256 bountyId,
    string calldata answer,
    bytes32 salt
) external {
    // Validasi:
    // - Deadline sudah lewat (block.timestamp >= deadline)
    // - Reveal window masih terbuka (block.timestamp < deadline + REVEAL_WINDOW)
    // - Peserta sudah commit sebelumnya
    // - Peserta belum pernah reveal

    // Verifikasi hash cocok
    bytes32 expectedHash = keccak256(
        abi.encodePacked(answer, salt, msg.sender, bountyId)
    );
    require(expectedHash == commitments[bountyId][msg.sender], "Hash mismatch!");

    // Simpan jawaban yang sudah terverifikasi
    submissions[bountyId].push(Submission({
        submitter: msg.sender,
        answer: answer
    }));

    revealed[bountyId][msg.sender] = true;
}
```

### Keamanan reveal:
- Jika jawaban atau salt berbeda → **hash tidak cocok** → transaksi gagal
- Peserta tidak bisa **mengubah jawaban** setelah commit
- Peserta lain tidak bisa **mengklaim jawaban** orang lain (karena `msg.sender` masuk hash)

---

## Fase 3: JUDGING

Setelah semua reveal selesai, bounty owner memanggil AI judge.

```solidity
function judgeAll(uint256 bountyId, bytes calldata llmInput) external {
    // Validasi:
    // - Hanya bounty owner yang bisa panggil
    // - Reveal window sudah tutup
    // - Belum pernah di-judge
    // - Ada minimal 1 submission yang revealed

    // Kirim ke Ritual LLM Precompile (0x0802)
    // llmInput = encoded prompt yang berisi semua jawaban
    // AI akan memberikan ranking/review

    judged[bountyId] = true;
}
```

---

## Fase 4: FINALIZE

Owner memilih pemenang berdasarkan review AI.

```solidity
function finalizeWinner(uint256 bountyId, uint256 winnerIndex) external {
    // Validasi:
    // - Hanya bounty owner
    // - Sudah di-judge
    // - Belum finalized
    // - winnerIndex valid

    // Transfer reward ke pemenang
    // Mark as finalized
}
```

---

## 📝 Perubahan dari Contract Asli

### Contract Asli (`AIJudge.sol`) — Masalahnya:

```solidity
// ❌ MASALAH: Jawaban langsung tersimpan sebagai plaintext!
struct Submission {
    address submitter;
    string answer;      // ← Semua orang bisa baca ini!
}
```

### Contract Baru — Yang perlu ditambahkan:

```solidity
// ✅ SOLUSI: Tambah state untuk commit-reveal

// Konstanta
uint256 public constant REVEAL_WINDOW = 1 days; // Waktu untuk reveal

// State baru
mapping(uint256 => mapping(address => bytes32)) public commitments;
mapping(uint256 => mapping(address => bool)) public hasCommitted;
mapping(uint256 => mapping(address => bool)) public hasRevealed;
mapping(uint256 => address[]) public committers; // Track siapa saja yang commit

// Enum untuk fase bounty
enum BountyPhase { Commit, Reveal, Judging, Finalized }

function getBountyPhase(uint256 bountyId) public view returns (BountyPhase) {
    Bounty storage b = bounties[bountyId];
    if (block.timestamp < b.deadline) return BountyPhase.Commit;
    if (block.timestamp < b.deadline + REVEAL_WINDOW) return BountyPhase.Reveal;
    if (!b.finalized) return BountyPhase.Judging;
    return BountyPhase.Finalized;
}
```

---

## 🧪 Skenario Test Plan

### Happy Path Tests:
```
1. ✅ Peserta bisa commit sebelum deadline
2. ✅ Peserta bisa reveal setelah deadline dengan jawaban & salt yang benar
3. ✅ Hash cocok → submission tercatat
4. ✅ Owner bisa judge setelah reveal window
5. ✅ Owner bisa finalize winner
6. ✅ Winner menerima reward
```

### Edge Cases & Security Tests:
```
7.  ❌ Commit setelah deadline → REVERT
8.  ❌ Reveal sebelum deadline → REVERT
9.  ❌ Reveal dengan salt salah → REVERT (hash mismatch)
10. ❌ Reveal dengan jawaban beda → REVERT (hash mismatch)
11. ❌ Double commit (commit 2x) → REVERT
12. ❌ Double reveal → REVERT
13. ❌ Reveal tanpa commit → REVERT
14. ❌ Reveal setelah reveal window tutup → REVERT
15. ❌ Judge sebelum reveal window tutup → REVERT
16. ❌ Non-owner panggil judgeAll → REVERT
17. ❌ Orang lain coba reveal pakai hash orang lain → REVERT (msg.sender beda)
18. ❌ Submit commitment ke bounty yang tidak exist → REVERT
19. ✅ Peserta yang tidak reveal → submission-nya tidak masuk judging
20. ✅ Partial reveal → hanya yang reveal yang di-judge
```

---

## 💻 Cara Generate Commitment Hash di Frontend (TypeScript/viem)

```typescript
import { keccak256, encodePacked } from 'viem';

function generateCommitment(
  answer: string,
  salt: `0x${string}`,    // Random 32 bytes
  sender: `0x${string}`,  // Wallet address
  bountyId: bigint
): `0x${string}` {
  return keccak256(
    encodePacked(
      ['string', 'bytes32', 'address', 'uint256'],
      [answer, salt, sender, bountyId]
    )
  );
}

// Generate random salt
function generateSalt(): `0x${string}` {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return `0x${Array.from(array).map(b => b.toString(16).padStart(2, '0')).join('')}`;
}

// ⚠️ PENTING: Salt harus disimpan secara lokal oleh user!
// Jika salt hilang, user tidak bisa reveal dan jawaban hilang.
```
