import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";

import hre from "hardhat";
import {
  keccak256,
  encodePacked,
  parseEther,
  getAddress,
} from "viem";

// Helper: generate random salt
function randomSalt(): `0x${string}` {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return `0x${Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")}` as `0x${string}`;
}

// Helper: compute commitment hash matching the Solidity logic
function computeCommitment(
  answer: string,
  salt: `0x${string}`,
  sender: `0x${string}`,
  bountyId: bigint
): `0x${string}` {
  return keccak256(
    encodePacked(
      ["string", "bytes32", "address", "uint256"],
      [answer, salt, sender, bountyId]
    )
  );
}

describe("AIJudge Commit-Reveal", () => {
  const ONE_DAY = 86400;
  const REWARD = parseEther("1");

  // Shared state set in beforeEach
  let viem: Awaited<ReturnType<typeof hre.network.connect>>["viem"];
  let helpers: Awaited<ReturnType<typeof hre.network.connect>>["networkHelpers"];
  let contract: any;
  let owner: any;
  let alice: any;
  let bob: any;
  let bountyId: bigint;

  beforeEach(async () => {
    const connection = await hre.network.connect();
    viem = connection.viem;
    helpers = connection.networkHelpers;

    const clients = await viem.getWalletClients();
    owner = clients[0];
    alice = clients[1];
    bob = clients[2];

    // Deploy contract
    contract = await viem.deployContract("AIJudge");

    // Create a bounty with 1 day deadline
    const publicClient = await viem.getPublicClient();
    const latestTimestamp = await helpers.time.latest();
    const deadline = BigInt(latestTimestamp) + BigInt(ONE_DAY);

    await contract.write.createBounty(
      ["Test Bounty", "Grade quality of answer", deadline],
      { value: REWARD }
    );

    bountyId = 1n;
  });

  // ─── Happy Path ─────────────────────────────────────────────

  it("should create a bounty with correct parameters", async () => {
    const result = await contract.read.getBounty([bountyId]);
    const [bountyOwner, title, rubric, reward] = result;

    assert.equal(
      getAddress(bountyOwner),
      getAddress(owner.account.address)
    );
    assert.equal(title, "Test Bounty");
    assert.equal(rubric, "Grade quality of answer");
    assert.equal(reward, REWARD);
  });

  it("should accept commitment before deadline", async () => {
    const answer = "My great answer";
    const salt = randomSalt();
    const commitment = computeCommitment(
      answer,
      salt,
      alice.account.address,
      bountyId
    );

    await contract.write.submitCommitment([bountyId, commitment], {
      account: alice.account,
    });

    const hasCommitted = await contract.read.getHasCommitted([
      bountyId,
      alice.account.address,
    ]);
    assert.equal(hasCommitted, true);

    const count = await contract.read.getCommitCount([bountyId]);
    assert.equal(count, 1n);
  });

  it("should accept valid reveal after deadline", async () => {
    const answer = "My great answer";
    const salt = randomSalt();
    const commitment = computeCommitment(
      answer,
      salt,
      alice.account.address,
      bountyId
    );

    // Commit
    await contract.write.submitCommitment([bountyId, commitment], {
      account: alice.account,
    });

    // Advance time past deadline
    await helpers.time.increase(ONE_DAY + 1);

    // Reveal
    await contract.write.revealAnswer([bountyId, answer, salt], {
      account: alice.account,
    });

    // Verify submission was stored
    const [submitter, revealedAnswer] = await contract.read.getSubmission([
      bountyId,
      0n,
    ]);
    assert.equal(getAddress(submitter), getAddress(alice.account.address));
    assert.equal(revealedAnswer, answer);
  });

  // ─── Security Tests ─────────────────────────────────────────

  it("should reject commitment after deadline", async () => {
    const commitment = randomSalt();

    // Advance time past deadline
    await helpers.time.increase(ONE_DAY + 1);

    await assert.rejects(
      async () => {
        await contract.write.submitCommitment([bountyId, commitment], {
          account: alice.account,
        });
      },
      (err: any) => {
        assert.ok(
          err.message?.includes("commit phase ended") ||
            err.details?.includes("commit phase ended"),
          `Expected "commit phase ended", got: ${err.message}`
        );
        return true;
      }
    );
  });

  it("should reject reveal before deadline", async () => {
    const answer = "My answer";
    const salt = randomSalt();
    const commitment = computeCommitment(
      answer,
      salt,
      alice.account.address,
      bountyId
    );

    // Commit (valid)
    await contract.write.submitCommitment([bountyId, commitment], {
      account: alice.account,
    });

    // Try reveal before deadline
    await assert.rejects(
      async () => {
        await contract.write.revealAnswer([bountyId, answer, salt], {
          account: alice.account,
        });
      },
      (err: any) => {
        assert.ok(
          err.message?.includes("reveal phase not started") ||
            err.details?.includes("reveal phase not started"),
          `Expected "reveal phase not started", got: ${err.message}`
        );
        return true;
      }
    );
  });

  it("should reject reveal with wrong salt", async () => {
    const answer = "My answer";
    const salt = randomSalt();
    const wrongSalt = randomSalt();
    const commitment = computeCommitment(
      answer,
      salt,
      alice.account.address,
      bountyId
    );

    // Commit
    await contract.write.submitCommitment([bountyId, commitment], {
      account: alice.account,
    });

    // Advance past deadline
    await helpers.time.increase(ONE_DAY + 1);

    // Reveal with wrong salt
    await assert.rejects(
      async () => {
        await contract.write.revealAnswer([bountyId, answer, wrongSalt], {
          account: alice.account,
        });
      },
      (err: any) => {
        assert.ok(
          err.message?.includes("hash mismatch") ||
            err.details?.includes("hash mismatch"),
          `Expected "hash mismatch", got: ${err.message}`
        );
        return true;
      }
    );
  });

  it("should reject double commitment", async () => {
    const commitment1 = randomSalt();
    const commitment2 = randomSalt();

    // First commit
    await contract.write.submitCommitment([bountyId, commitment1], {
      account: alice.account,
    });

    // Second commit — should fail
    await assert.rejects(
      async () => {
        await contract.write.submitCommitment([bountyId, commitment2], {
          account: alice.account,
        });
      },
      (err: any) => {
        assert.ok(
          err.message?.includes("already committed") ||
            err.details?.includes("already committed"),
          `Expected "already committed", got: ${err.message}`
        );
        return true;
      }
    );
  });

  it("should reject reveal without prior commitment", async () => {
    // Advance past deadline
    await helpers.time.increase(ONE_DAY + 1);

    await assert.rejects(
      async () => {
        await contract.write.revealAnswer(
          [bountyId, "some answer", randomSalt()],
          { account: alice.account }
        );
      },
      (err: any) => {
        assert.ok(
          err.message?.includes("no commitment found") ||
            err.details?.includes("no commitment found"),
          `Expected "no commitment found", got: ${err.message}`
        );
        return true;
      }
    );
  });

  it("should reject empty commitment", async () => {
    const emptyCommitment =
      "0x0000000000000000000000000000000000000000000000000000000000000000" as `0x${string}`;

    await assert.rejects(
      async () => {
        await contract.write.submitCommitment(
          [bountyId, emptyCommitment],
          { account: alice.account }
        );
      },
      (err: any) => {
        assert.ok(
          err.message?.includes("empty commitment") ||
            err.details?.includes("empty commitment"),
          `Expected "empty commitment", got: ${err.message}`
        );
        return true;
      }
    );
  });

  it("should handle multiple participants correctly", async () => {
    const aliceAnswer = "Alice's answer";
    const aliceSalt = randomSalt();
    const aliceCommitment = computeCommitment(
      aliceAnswer,
      aliceSalt,
      alice.account.address,
      bountyId
    );

    const bobAnswer = "Bob's answer";
    const bobSalt = randomSalt();
    const bobCommitment = computeCommitment(
      bobAnswer,
      bobSalt,
      bob.account.address,
      bountyId
    );

    // Both commit
    await contract.write.submitCommitment([bountyId, aliceCommitment], {
      account: alice.account,
    });
    await contract.write.submitCommitment([bountyId, bobCommitment], {
      account: bob.account,
    });

    // Verify 2 commitments
    const count = await contract.read.getCommitCount([bountyId]);
    assert.equal(count, 2n);

    // Advance past deadline
    await helpers.time.increase(ONE_DAY + 1);

    // Both reveal
    await contract.write.revealAnswer([bountyId, aliceAnswer, aliceSalt], {
      account: alice.account,
    });
    await contract.write.revealAnswer([bountyId, bobAnswer, bobSalt], {
      account: bob.account,
    });

    // Verify both submissions
    const [sub0Addr, sub0Answer] = await contract.read.getSubmission([
      bountyId,
      0n,
    ]);
    assert.equal(sub0Answer, aliceAnswer);

    const [sub1Addr, sub1Answer] = await contract.read.getSubmission([
      bountyId,
      1n,
    ]);
    assert.equal(sub1Answer, bobAnswer);
  });

  it("should return correct bounty phase", async () => {
    // Phase 0 = Commit (before deadline)
    let phase = await contract.read.getBountyPhase([bountyId]);
    assert.equal(phase, 0); // Commit

    // Advance past deadline
    await helpers.time.increase(ONE_DAY + 1);

    // Phase 1 = Reveal
    phase = await contract.read.getBountyPhase([bountyId]);
    assert.equal(phase, 1); // Reveal

    // Advance past reveal window (another day)
    await helpers.time.increase(ONE_DAY + 1);

    // Phase 2 = Judging
    phase = await contract.read.getBountyPhase([bountyId]);
    assert.equal(phase, 2); // Judging
  });
});
