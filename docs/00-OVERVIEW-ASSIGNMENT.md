# 📋 RINGKASAN ASSIGNMENT: Privacy-Preserving AI Bounty Judge

> **Sumber:** Ritual Academy — Sessions & Proof of Building
> **Repo Fork:** https://github.com/cozfuttu/ritual-chain-workshop
> **VOD Workshop:** https://x.com/i/broadcasts/1AxRnnVDYMrxl
> **Submit via:** https://discord.com/channels/1210468736205852672/1516880140867469481/1517222943229345814

---

## 🎯 Masalah Utama

Di workshop sebelumnya, sistem bounty judge memiliki **kelemahan kritis**:
- Submission peserta bersifat **publik** (tersimpan on-chain sebagai plaintext)
- Peserta lain bisa **melihat & menyalin** jawaban orang lain
- Lalu submit versi yang "lebih baik" → **tidak fair**

**Tujuan assignment:** Mengamankan proses bounty agar jawaban **tetap tersembunyi** sampai proses judging selesai.

---

## 📁 Struktur Repo Asli

```
ritual-chain-workshop/
├── hardhat/                    ← Smart contract (Solidity)
│   ├── contracts/
│   │   ├── AIJudge.sol         ← Contract utama (HARUS dimodifikasi)
│   │   └── utils/
│   │       └── PrecompileConsumer.sol  ← Base contract untuk Ritual precompiles
│   ├── hardhat.config.ts       ← Solidity 0.8.24, viem toolbox
│   ├── package.json            ← Hardhat 3 + pnpm
│   └── ignition/               ← Deployment modules
│
└── web/                        ← Frontend (Next.js + wagmi + viem)
    ├── src/
    │   ├── abi/AIJudge.ts      ← Contract ABI
    │   ├── config/
    │   │   ├── contract.ts     ← Address + executor + chain id
    │   │   └── wagmi.ts        ← Custom Ritual Chain config
    │   └── app/
    │       └── providers.tsx   ← wagmi + React providers
    ├── .env.example
    └── package.json            ← Next.js + TailwindCSS
```

---

## 🏗️ Dua Track Assignment

### Track 1: REQUIRED — Commit-Reveal Bounty (Solidity)

Implementasi mekanisme **commit-reveal** yang bekerja di semua EVM chain.

### Track 2: ADVANCED — Ritual-Native Hidden Submissions

Menggunakan **TEE (Trusted Execution Environment)** dari Ritual untuk enkripsi jawaban.

---

## 📦 Deliverables (Yang Harus Dikumpulkan)

| # | Item | Keterangan |
|---|------|------------|
| 1 | ✅ Updated Solidity Contract | `AIJudge.sol` yang sudah ada commit-reveal |
| 2 | ✅ README | Menjelaskan lifecycle lengkap |
| 3 | ✅ Test Plan | Skenario test untuk reveal cases |
| 4 | ✅ Architecture Note | Catatan arsitektur sistem |
| 5 | ✅ Reflection Question | Jawaban 5-8 kalimat |

### Reflection Question:
> *"What should be public, what should stay hidden, and what should be decided by AI versus by a human in a bounty system?"*

---

## ⚙️ Tech Stack

| Layer | Teknologi |
|-------|-----------|
| Smart Contract | Solidity 0.8.24 |
| Dev Framework | Hardhat 3 (pnpm) |
| Testing | node:test + viem |
| Frontend | Next.js (App Router) + TypeScript + TailwindCSS |
| Wallet | wagmi + viem |
| Chain | Ritual Chain (Chain ID: 1979) |
| RPC | `https://rpc.ritualfoundation.org` |
| AI Infra | Ritual Precompiles (LLM di `0x0802`) |
