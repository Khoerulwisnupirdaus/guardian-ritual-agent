# 🌐 Ritual Chain — Panduan Ekosistem Lengkap

> Catatan ini dirangkum dari https://docs.ritualfoundation.org
> Fokus: semua yang perlu dipahami untuk mengerjakan assignment AI Bounty Judge

---

## Apa itu Ritual Chain?

Ritual Chain adalah **L1 blockchain AI-native** pertama dimana smart contract bisa **berpikir, melihat, mendengar, dan bertindak**. Ini bukan EVM biasa — ini **EVM++** yang punya precompile bawaan untuk AI inference, cryptographic proofs, dan autonomous agents.

### Filosofi Inti: EOVMT
> **Execute-Once-Verify-Many-Times**
>
> Komputasi AI yang berat (LLM inference, dll) **hanya dijalankan sekali** oleh executor,
> lalu **diverifikasi secara kriptografis** oleh banyak validator.
> Ini menghindari biaya re-eksekusi AI di setiap node.

---

## ⚡ Network Config

| Parameter | Value |
|-----------|-------|
| **Chain ID** | `1979` |
| **Currency** | `RITUAL` (18 decimals, testnet) |
| **RPC URL** | `https://rpc.ritualfoundation.org` |
| **Explorer** | `https://explorer.ritualfoundation.org` |
| **Faucet** | `https://faucet.ritualfoundation.org` |

### Setup MetaMask
Tambah custom network dengan config di atas, lalu ambil testnet tokens dari faucet.

---

## 🧩 Precompile Map (16 Precompiles)

Precompile menggantikan middleware lama (Infernet). Smart contract bisa langsung panggil AI inference, ZK verification, HTTP request, scheduling, dan key management **dalam satu konteks transaksi**.

### Kategori berdasarkan Capability

| Capability | Precompile | Address | Tipe |
|-----------|-----------|---------|------|
| **🧠 Think/Reason** | LLM Inference | `0x0802` | Short-running async |
| | ONNX (Classical Models) | `0x0800` | Synchronous |
| | FHE Inference | `0x0807` | Long-running async |
| **🌐 Act** | HTTP Call (Short) | `0x0801` | Short-running async |
| | HTTP Call (Long) | `0x0805` | Long-running async |
| | Sovereign Agent | `0x080C` | Long-running async |
| **🔐 Keep Secrets** | DKMS (Key Mgmt) | `0x081B` | Short-running async |
| | ECIES / Secrets | via DKMS | — |
| **✅ Prove** | Ed25519 | `0x0009` | Synchronous |
| | Secp256r1 (Passkeys) | `0x0100` | Synchronous |
| | ZK Proofs | — | — |
| **🔧 Utility** | JQ (JSON parsing) | `0x0803` | Synchronous |
| | TX Hash | `0x0830` | Synchronous |
| **⏰ Schedule** | Scheduler | `0x56e7...D58B` | System contract |
| **💰 Pay** | RitualWallet | `0x532F...3948` | System contract |

### System Contracts Penting

| Contract | Address | Fungsi |
|----------|---------|--------|
| **AsyncDelivery** | `0x5A16214fF555848411544b005f7Ac063742f39F6` | Mengirim hasil async precompile kembali ke contract |
| **Scheduler** | `0x56e776BAE2DD60664b69Bd5F865F1180ffB7D58B` | Menjadwalkan eksekusi contract di masa depan |
| **RitualWallet** | `0x532F0dF0896F353d8C3DD8cc134e8129DA2a3948` | Manage fee untuk precompile calls |

### Arsitektur: Sidecars
Precompile terhubung dengan **"Sidecars"** — modul komputasi off-chain yang menempel pada validator. Ini menjalankan komputasi AI yang berat sambil menjaga main execution client tetap ringan.

---

## 🤖 LLM Inference Precompile (0x0802)

Ini adalah **jantung** dari AI Bounty Judge — cara memanggil LLM langsung dari smart contract.

### Cara Kerja
- **Address:** `0x0802`
- **Tipe:** Short-running asynchronous
- **ABI:** 30-field layout yang mirror OpenAI Chat Completion API
- **Streaming:** Support SSE dengan EIP-712 signed tokens

### Field ABI Penting

| Field # | Nama | Deskripsi |
|---------|------|-----------|
| 5 | `messagesJson` | Stringified JSON conversation `[{"role":"user","content":"..."}]` |
| 6 | `model` | Model identifier (e.g., `zai-org/GLM-4.7-FP8`) |
| 22 | `temperature` | Kontrol randomness output |
| 24 | `convoHistory` | Required — track conversation state |

### Contoh Solidity

```solidity
address constant LLM_PRECOMPILE = address(0x0802);

function triggerInference(bytes memory prompt) public returns (bytes memory) {
    bytes memory payload = abi.encode(
        // ... fields 1-30 per ABI reference
    );
    (bool success, bytes memory result) = LLM_PRECOMPILE.staticcall(payload);
    require(success, "LLM inference failed");
    return result;
}
```

### Privacy: Cascade Protocol
- Menggunakan "token-sharding" untuk distribusi inference ke multiple nodes
- Tidak ada single node yang melihat full prompt atau output
- Menjamin privasi untuk operasi AI sensitif

---

## 📋 Tiga Model Eksekusi

### 1. Synchronous (Instant)
```
Contract → staticcall(precompile) → result langsung
Contoh: ONNX (0x0800), Ed25519 (0x0009)
```

### 2. Short-Running Async (Detik–Menit)
```
Contract → call(precompile) → dapat jobId
... waktu berlalu ...
AsyncDelivery → callback ke contract → onResult(jobId, result)
Contoh: LLM (0x0802), HTTP (0x0801), DKMS (0x081B)
```

### 3. Long-Running Async (Menit–Jam)
```
Contract → call(precompile) → task ID
... waktu berlalu ...
Polling/delivery mechanism → return results
Contoh: FHE (0x0807), Sovereign Agent (0x080C)
```

### Pattern untuk AI Bounty Judge: Two-Phase Lifecycle

**Phase 1 — Request (kirim ke LLM):**
```solidity
(bool success, bytes memory taskIdData) = LLM_PRECOMPILE.call(payload);
// Returns task/job ID
```

**Phase 2 — Callback (terima hasil):**
```solidity
address constant ASYNC_DELIVERY = 0x5A16214fF555848411544b005f7Ac063742f39F6;

function onResult(bytes32 jobId, bytes calldata result) external {
    require(msg.sender == ASYNC_DELIVERY, "Unauthorized callback");
    // Parse LLM output dan simpan judgment
}
```

---

## 🔐 Privacy & Keys

### DKMS (Decentralized Key Management System)

- **Address:** `0x081B`
- Derive deterministic secp256k1 keypairs di dalam **TEE (Trusted Execution Environment)**
- Same owner + same `keyIndex` → same keypair setiap saat
- **Keys TIDAK PERNAH keluar dari enclave** — bahkan contract code tidak bisa extract raw key material

```solidity
address internal constant DKMS_PRECOMPILE = address(0x081B);

function deriveKey(uint256 keyIndex) public view returns (bytes memory) {
    bytes memory input = abi.encode(keyIndex);
    (bool success, bytes memory result) = DKMS_PRECOMPILE.staticcall(input);
    require(success, "DKMS derivation failed");
    return result;
}
```

### Secrets & ECIES (Elliptic Curve Integrated Encryption Scheme)

Flow enkripsi untuk data sensitif:

```
1. Off-chain: Encrypt dengan executor's public key
   const ciphertext = ecies.encrypt(executorPublicKey, Buffer.from(answer));

2. On-chain: Simpan ciphertext (tidak bisa dibaca siapapun)
   function submitEncrypted(bytes calldata encryptedData) external { ... }

3. TEE: Decrypt saat eksekusi precompile
   Plaintext HANYA exist di dalam TEE, dihapus setelah selesai
```

```typescript
// TypeScript: Encrypt submission dengan executor's public key
import { encrypt } from 'eciesjs';
const ciphertext = encrypt(executorPublicKey, Buffer.from(answer));
```

### FHE Inference (Level Privasi Maksimal)

- **Address:** `0x0807`
- AI model inference pada **data terenkripsi** — model tidak pernah lihat plaintext
- Bahkan TEE tidak melihat plaintext
- Lebih kompleks dan mahal — untuk assignment ini, TEE+DKMS lebih praktis

---

## 💰 RitualWallet

System contract untuk manage fee pembayaran precompile calls.

```solidity
interface IRitualWallet {
    function deposit(uint256 lockDuration) external payable;
    function depositFor(address user, uint256 lockDuration) external payable;
    function withdraw(uint256 amount) external;
    function balanceOf(address account) external view returns (uint256);
    function lockUntil(address account) external view returns (uint256);
}

// Contoh: Deposit 0.01 RITUAL dengan lock 100 blocks
IRitualWallet wallet = IRitualWallet(0x532F0dF0896F353d8C3DD8cc134e8129DA2a3948);
wallet.deposit{value: 0.01 ether}(100);

// Fund agent's address
wallet.depositFor{value: 0.05 ether}(agentAddress, 200);
```

**Penting:**
- Lock bersifat **monotonic** — deposit baru hanya memperpanjang lock, tidak mempersingkat
- Untuk async precompiles, balance **EOA** yang dicek (bukan contract)
- Deploying EOA harus deposit RITUAL tokens sebelum contract bisa panggil precompiles

---

## 🤖 Autonomous Agents — 7 Properties

Ritual mendefinisikan 7 properti untuk agent yang benar-benar sovereign:

| # | Property | Arti |
|---|----------|------|
| 1 | **Immortality** | Lifecycle terikat ke network, bukan satu server |
| 2 | **Emancipation** | Tidak ada aktor eksternal yang bisa ambil alih keys/keputusan |
| 3 | **Teleportability** | Identity & memory bisa pindah antar environment |
| 4 | **Financial Sovereignty** | Agent = first-class economic actor (hold assets, price services) |
| 5 | **Privacy** | Bisa simpan rahasia (prompts, strategy) pakai TEE |
| 6 | **Internet-native Interop** | Operasi lintas Web2 dan Web3 |
| 7 | **Computational Sovereignty** | Akses compute dedicat (LLMs, ZK proofs) di level protokol |

### Relevansi untuk Bounty Judge
Bounty judge bisa dimodel sebagai autonomous agent:
- **Property 5 (Privacy):** Evaluasi submission secara privat
- **Property 4 (Financial):** Manage reward funds via RitualWallet
- **Property 2 (Emancipation):** Judge tanpa human approval
- **Property 1 (Immortality):** Auto-schedule judging saat deadline

---

## 🔗 Bagaimana Semua Terhubung untuk Assignment

```
┌─────────────────────────────────────────────────────────────────┐
│              TRACK 1: COMMIT-REVEAL (EVM Standard)              │
│                                                                 │
│  Client                                                         │
│    → keccak256(answer + salt + sender + bountyId)               │
│    → submitCommitment(bountyId, hash) [on-chain]                │
│                                                                 │
│  Setelah deadline                                               │
│    → revealAnswer(bountyId, answer, salt)                       │
│    → Contract verifikasi hash → simpan plaintext                │
│                                                                 │
│  Owner                                                          │
│    → judgeAll(bountyId, llmInput)                               │
│    → LLM Precompile (0x0802) → AI review                       │
│    → finalizeWinner(bountyId, winnerIndex)                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│           TRACK 2: RITUAL-NATIVE (TEE + DKMS)                  │
│                                                                 │
│  Client                                                         │
│    → ECIES encrypt(answer, TEE_pubkey) [off-chain]              │
│    → submitEncrypted(bountyId, ciphertext) [on-chain]           │
│                                                                 │
│  Owner                                                          │
│    → judgeAll(bountyId)                                         │
│    → DKMS (0x081B) decrypt di TEE                               │
│    → LLM (0x0802) judge di TEE                                  │
│    → Result on-chain                                            │
│                                                                 │
│  Plaintext TIDAK PERNAH keluar dari TEE                         │
│  Jawaban tetap terenkripsi on-chain selamanya                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│           TRACK 3: FHE (Theoretical Maximum Privacy)            │
│                                                                 │
│  Client → FHE encrypt(answer) → on-chain ciphertext            │
│  FHE Precompile (0x0807) → inference ON ciphertext              │
│  Bahkan TEE tidak pernah lihat plaintext                        │
│  (Terlalu kompleks untuk assignment ini)                        │
└─────────────────────────────────────────────────────────────────┘
```

### Semua track butuh:
- ✅ Funded **RitualWallet** (`0x532F...3948`) untuk bayar precompile calls
- ✅ **AsyncDelivery** (`0x5A16...39F6`) untuk terima hasil async
- ✅ **LLM Precompile** (`0x0802`) untuk AI judging

---

## 📚 Resource Tambahan

| Resource | URL |
|----------|-----|
| Docs Utama | https://docs.ritualfoundation.org |
| Whitepaper | https://whitepaper.ritualfoundation.org |
| Skills Repo | `ritual-dapp-skills` (GitHub) — ABI layouts, integration patterns |
| Secrets Suite | `ritual-dapp-secrets` — ECIES encryption tools |
| Deploy Module | `ritual-dapp-deploy` — Foundry deployment scripts |
