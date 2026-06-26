# 🚀 Guide Track 2: Ritual-Native Hidden Submissions (ADVANCED)

## Apa Bedanya dengan Commit-Reveal?

| Aspek | Commit-Reveal (Track 1) | Ritual-Native (Track 2) |
|-------|------------------------|------------------------|
| Kerahasiaan | Jawaban tersembunyi sampai reveal | Jawaban tersembunyi sampai judging selesai |
| Reveal oleh peserta | ✅ Wajib | ❌ Tidak perlu — TEE yang membuka |
| Jawaban on-chain | Setelah reveal → publik | Tetap terenkripsi on-chain |
| AI judging | Setelah reveal, dari plaintext | Di dalam TEE, tidak ada yang bisa lihat |
| Kompleksitas | Sedang | Tinggi |

---

## Arsitektur Ritual TEE

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FLOW OVERVIEW                               │
│                                                                     │
│  ┌──────────┐     ┌──────────────┐     ┌─────────────────────────┐ │
│  │  PESERTA  │────▶│   ON-CHAIN   │────▶│   RITUAL TEE (ENCLAVE)  │ │
│  │           │     │  (Encrypted) │     │                         │ │
│  │ Encrypt   │     │  Stores:     │     │ 1. Decrypt semua answer │ │
│  │ jawaban   │     │  ciphertext  │     │ 2. Jalankan LLM judge   │ │
│  │ dengan    │     │  + metadata  │     │ 3. Return ranking       │ │
│  │ TEE pubkey│     │              │     │ 4. Hapus plaintext      │ │
│  └──────────┘     └──────────────┘     └─────────────────────────┘ │
│                                                                     │
│  Plaintext HANYA ada di dalam TEE saat judging                      │
│  Tidak ada manusia/node yang bisa lihat jawaban sebelum finalize    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Dimana Plaintext Berada?

| Lokasi | Apa yang tersimpan | Siapa yang bisa akses |
|--------|-------------------|----------------------|
| **On-chain** | Ciphertext (jawaban terenkripsi) | Siapa saja (tapi tidak berguna tanpa key) |
| **TEE Enclave** | Plaintext (sementara, saat judging) | Hanya kode di dalam TEE |
| **Off-chain** | Metadata bounty (opsional: rubric, title) | Tergantung desain |
| **Frontend/User** | Jawaban + key lokal (sebelum submit) | Hanya user itu sendiri |

### ⚠️ Poin Kritis:
- **Plaintext HANYA exist di dalam TEE** saat proses judging berlangsung
- Setelah judging selesai, TEE **menghapus plaintext** dari memory
- Tidak ada operator node, validator, atau MEV bot yang bisa membaca jawaban

---

## Ritual Precompiles yang Relevan

Dari `PrecompileConsumer.sol`:

```solidity
abstract contract PrecompileConsumer {
    // Untuk AI judging (LLM inference)
    address internal constant LLM_INFERENCE_PRECOMPILE = address(0x0802);

    // Untuk enkripsi/dekripsi (Key Management)
    address internal constant DKMS_PRECOMPILE = address(0x081B);

    // Untuk HTTP calls (jika perlu off-chain data)
    address internal constant HTTP_CALL_PRECOMPILE = address(0x0801);
}
```

| Precompile | Address | Fungsi |
|-----------|---------|--------|
| **LLM Inference** | `0x0802` | Menjalankan AI model di TEE |
| **DKMS** | `0x081B` | Distributed Key Management — encrypt/decrypt |
| **HTTP Call** | `0x0801` | HTTP request dari dalam contract |

---

## Desain Solusi Ritual-Native

### 1. Submission (Encrypted)

```solidity
struct EncryptedSubmission {
    address submitter;
    bytes encryptedAnswer;    // Jawaban yang dienkripsi dengan TEE public key
    bytes32 answerHash;       // Hash jawaban asli (untuk verifikasi integritas)
}

function submitEncrypted(
    uint256 bountyId,
    bytes calldata encryptedAnswer,
    bytes32 answerHash
) external {
    // Simpan ciphertext on-chain
    // Tidak ada yang bisa baca tanpa TEE private key
}
```

### 2. Batch Judging (Di dalam TEE)

```solidity
function judgeAll(uint256 bountyId, bytes calldata llmInput) external {
    // Owner panggil ini setelah deadline
    // Contract memanggil DKMS precompile untuk decrypt semua jawaban
    // Lalu memanggil LLM precompile untuk batch judging
    // Semua terjadi di dalam TEE — tidak ada plaintext yang keluar

    // PENTING: Satu panggilan LLM untuk SEMUA jawaban (batch)
    // Bukan satu panggilan per jawaban (mahal + lambat)
}
```

### 3. Kenapa Batch, Bukan Per-Jawaban?

```
❌ SALAH (1 LLM call per jawaban):
   submitAnswer("jawaban1") → LLM call 1
   submitAnswer("jawaban2") → LLM call 2
   submitAnswer("jawaban3") → LLM call 3
   → Mahal, lambat, urutan bisa bocorkan info

✅ BENAR (1 LLM call untuk semua):
   judgeAll(bountyId) → Kumpulkan semua → 1 LLM call → ranking
   → Efisien, fair, konsisten
```

---

## On-chain vs Off-chain

### Opsi A: Semua On-chain (Sederhana)

```
On-chain: ciphertext jawaban, metadata bounty, hasil judging
Off-chain: tidak ada (kecuali frontend)
Pro: Fully verifiable, immutable
Con: Gas cost tinggi untuk jawaban panjang
```

### Opsi B: Hybrid (Efisien)

```
On-chain: hash jawaban, commitment, hasil judging
Off-chain: ciphertext jawaban (IPFS/Arweave), rubric
Pro: Gas efficient
Con: Perlu memastikan off-chain storage reliable
```

### Opsi C: Ritual Secrets (Paling Ritual-Native)

```
On-chain: reference ke encrypted secret, hash, hasil judging
Off-chain: Jawaban disimpan sebagai Ritual encrypted secret
Pro: Fully integrated dengan Ritual ecosystem
Con: Tergantung pada Ritual infra
```

---

## 📝 Yang Harus Dijelaskan di Architecture Note

1. **Dimana plaintext exist?**
   → Hanya di TEE saat judging, dihapus setelah selesai

2. **Apa yang on-chain vs off-chain?**
   → On-chain: ciphertext/hash + hasil judging; Off-chain: opsional storage

3. **Bagaimana LLM menerima submissions untuk batch judging?**
   → TEE decrypt semua ciphertext → format prompt → 1x LLM call → return ranking

4. **Keuntungan vs Commit-Reveal:**
   → Jawaban TIDAK PERNAH publik (bahkan setelah judging)
   → Tidak perlu fase reveal (lebih simpel UX)
   → Perlindungan dari MEV & front-running
