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
    uint256 public constant REVEAL_WINDOW = 1 days;

    uint256 public nextBountyId = 1;

    IRitualWallet wallet =
        IRitualWallet(0x532F0dF0896F353d8C3DD8cc134e8129DA2a3948);

    // ─── Data Structures ────────────────────────────────────────────

    struct Submission {
        address submitter;
        string answer;
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

    // ─── Bounty Phase Enum ──────────────────────────────────────────

    enum BountyPhase {
        Commit,    // Before deadline: accept commitments only
        Reveal,    // After deadline, within REVEAL_WINDOW: accept reveals
        Judging,   // After reveal window: ready for AI judging
        Finalized  // Winner selected and paid
    }

    // ─── State ──────────────────────────────────────────────────────

    mapping(uint256 => Bounty) public bounties;

    /// @notice Commitment hash per bounty per submitter
    mapping(uint256 => mapping(address => bytes32)) public commitments;

    /// @notice Whether an address has committed to a bounty
    mapping(uint256 => mapping(address => bool)) public hasCommitted;

    /// @notice Whether an address has revealed their answer
    mapping(uint256 => mapping(address => bool)) public hasRevealed;

    /// @notice Number of commitments per bounty
    mapping(uint256 => uint256) public commitCount;

    // ─── Events ─────────────────────────────────────────────────────

    event BountyCreated(
        uint256 indexed bountyId,
        address indexed owner,
        string title,
        uint256 reward,
        uint256 deadline
    );

    event CommitmentSubmitted(
        uint256 indexed bountyId,
        address indexed submitter
    );

    event AnswerRevealed(
        uint256 indexed bountyId,
        uint256 indexed submissionIndex,
        address indexed submitter
    );

    event AllAnswersJudged(uint256 indexed bountyId, bytes aiReview);

    event WinnerFinalized(
        uint256 indexed bountyId,
        uint256 indexed winnerIndex,
        address indexed winner,
        uint256 reward
    );

    // ─── Modifiers ──────────────────────────────────────────────────

    modifier onlyOwner(uint256 bountyId) {
        require(msg.sender == bounties[bountyId].owner, "not bounty owner");
        _;
    }

    modifier bountyExists(uint256 bountyId) {
        require(bounties[bountyId].owner != address(0), "bounty not found");
        _;
    }

    // ─── View Helpers ───────────────────────────────────────────────

    /// @notice Returns the current phase of a bounty
    function getBountyPhase(
        uint256 bountyId
    ) public view bountyExists(bountyId) returns (BountyPhase) {
        Bounty storage bounty = bounties[bountyId];
        if (bounty.finalized) return BountyPhase.Finalized;
        if (block.timestamp < bounty.deadline) return BountyPhase.Commit;
        if (block.timestamp < bounty.deadline + REVEAL_WINDOW)
            return BountyPhase.Reveal;
        return BountyPhase.Judging;
    }

    // ─── Core Functions ─────────────────────────────────────────────

    /// @notice Create a new bounty with a reward, title, rubric, and deadline
    function createBounty(
        string calldata title,
        string calldata rubric,
        uint256 deadline
    ) external payable returns (uint256 bountyId) {
        require(msg.value > 0, "reward required");
        require(deadline > block.timestamp, "deadline must be in the future");

        bountyId = nextBountyId++;

        Bounty storage bounty = bounties[bountyId];

        bounty.owner = msg.sender;
        bounty.title = title;
        bounty.rubric = rubric;
        bounty.reward = msg.value;
        bounty.deadline = deadline;
        bounty.winnerIndex = type(uint256).max;

        emit BountyCreated(bountyId, msg.sender, title, msg.value, deadline);
    }

    /// @notice Submit a commitment hash during the commit phase.
    ///         The commitment is: keccak256(abi.encodePacked(answer, salt, msg.sender, bountyId))
    function submitCommitment(
        uint256 bountyId,
        bytes32 commitment
    ) external bountyExists(bountyId) {
        Bounty storage bounty = bounties[bountyId];

        require(
            block.timestamp < bounty.deadline,
            "commit phase ended"
        );
        require(!hasCommitted[bountyId][msg.sender], "already committed");
        require(
            commitCount[bountyId] < MAX_SUBMISSIONS,
            "too many submissions"
        );
        require(commitment != bytes32(0), "empty commitment");

        commitments[bountyId][msg.sender] = commitment;
        hasCommitted[bountyId][msg.sender] = true;
        commitCount[bountyId]++;

        emit CommitmentSubmitted(bountyId, msg.sender);
    }

    /// @notice Reveal an answer after the deadline but within the reveal window.
    ///         Verifies that keccak256(abi.encodePacked(answer, salt, msg.sender, bountyId))
    ///         matches the stored commitment.
    function revealAnswer(
        uint256 bountyId,
        string calldata answer,
        bytes32 salt
    ) external bountyExists(bountyId) {
        Bounty storage bounty = bounties[bountyId];

        // Must be in reveal phase
        require(
            block.timestamp >= bounty.deadline,
            "reveal phase not started"
        );
        require(
            block.timestamp < bounty.deadline + REVEAL_WINDOW,
            "reveal window closed"
        );

        // Must have committed and not yet revealed
        require(hasCommitted[bountyId][msg.sender], "no commitment found");
        require(!hasRevealed[bountyId][msg.sender], "already revealed");

        // Answer length check
        require(
            bytes(answer).length <= MAX_ANSWER_LENGTH,
            "answer too long"
        );

        // Verify commitment hash
        bytes32 computedHash = keccak256(
            abi.encodePacked(answer, salt, msg.sender, bountyId)
        );
        require(
            computedHash == commitments[bountyId][msg.sender],
            "hash mismatch"
        );

        // Store the revealed submission
        bounty.submissions.push(
            Submission({submitter: msg.sender, answer: answer})
        );
        hasRevealed[bountyId][msg.sender] = true;

        emit AnswerRevealed(
            bountyId,
            bounty.submissions.length - 1,
            msg.sender
        );
    }

    /// @notice Judge all revealed submissions using the Ritual LLM precompile.
    ///         Can only be called after the reveal window closes.
    function judgeAll(
        uint256 bountyId,
        bytes calldata llmInput
    ) external bountyExists(bountyId) onlyOwner(bountyId) {
        Bounty storage bounty = bounties[bountyId];

        require(
            block.timestamp >= bounty.deadline + REVEAL_WINDOW,
            "reveal window still open"
        );
        require(!bounty.judged, "already judged");
        require(!bounty.finalized, "already finalized");
        require(bounty.submissions.length > 0, "no revealed submissions");

        bytes memory output = _executePrecompile(
            LLM_INFERENCE_PRECOMPILE,
            llmInput
        );

        (
            bool hasError,
            bytes memory completionData,
            ,
            string memory errorMessage,

        ) = abi.decode(output, (bool, bytes, bytes, string, ConvoHistory));

        require(!hasError, errorMessage);

        bounty.judged = true;
        bounty.aiReview = completionData;

        emit AllAnswersJudged(bountyId, completionData);
    }

    /// @notice Finalize the winner and pay out the reward.
    function finalizeWinner(
        uint256 bountyId,
        uint256 winnerIndex
    ) external bountyExists(bountyId) onlyOwner(bountyId) {
        Bounty storage bounty = bounties[bountyId];

        require(bounty.judged, "not judged yet");
        require(!bounty.finalized, "already finalized");
        require(
            winnerIndex < bounty.submissions.length,
            "invalid winner index"
        );

        bounty.finalized = true;
        bounty.winnerIndex = winnerIndex;

        address winner = bounty.submissions[winnerIndex].submitter;
        uint256 reward = bounty.reward;
        bounty.reward = 0;

        (bool ok, ) = payable(winner).call{value: reward}("");
        require(ok, "payment failed");

        emit WinnerFinalized(bountyId, winnerIndex, winner, reward);
    }

    // ─── View Functions ─────────────────────────────────────────────

    /// @notice Get bounty details
    function getBounty(
        uint256 bountyId
    )
        external
        view
        bountyExists(bountyId)
        returns (
            address owner,
            string memory title,
            string memory rubric,
            uint256 reward,
            uint256 deadline,
            bool judged,
            bool finalized,
            uint256 submissionCount,
            uint256 winnerIndex,
            bytes memory aiReview
        )
    {
        Bounty storage bounty = bounties[bountyId];

        return (
            bounty.owner,
            bounty.title,
            bounty.rubric,
            bounty.reward,
            bounty.deadline,
            bounty.judged,
            bounty.finalized,
            bounty.submissions.length,
            bounty.winnerIndex,
            bounty.aiReview
        );
    }

    /// @notice Get a specific revealed submission
    function getSubmission(
        uint256 bountyId,
        uint256 index
    )
        external
        view
        bountyExists(bountyId)
        returns (address submitter, string memory answer)
    {
        Bounty storage bounty = bounties[bountyId];

        require(index < bounty.submissions.length, "invalid index");

        Submission storage submission = bounty.submissions[index];

        return (submission.submitter, submission.answer);
    }

    /// @notice Get the number of commitments for a bounty
    function getCommitCount(
        uint256 bountyId
    ) external view bountyExists(bountyId) returns (uint256) {
        return commitCount[bountyId];
    }

    /// @notice Check if an address has committed to a bounty
    function getHasCommitted(
        uint256 bountyId,
        address submitter
    ) external view returns (bool) {
        return hasCommitted[bountyId][submitter];
    }

    /// @notice Check if an address has revealed their answer
    function getHasRevealed(
        uint256 bountyId,
        address submitter
    ) external view returns (bool) {
        return hasRevealed[bountyId][submitter];
    }
}
