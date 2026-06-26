// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title RitualChronicle
 * @notice An on-chain AI chronicle that stores analysis entries permanently on Ritual Chain.
 * @dev Owner can write entries. Anyone can read. Designed as a companion to GuardianSentinel agent.
 *
 * Architecture:
 *   - Owner submits topics for analysis
 *   - Entries are stored immutably with timestamp and block number
 *   - Events are emitted for off-chain indexing
 *   - Public read functions for transparency
 */
contract RitualChronicle {
    // ── Types ──
    struct Entry {
        uint256 id;
        uint256 timestamp;
        uint256 blockNumber;
        string topic;
        string analysis;
        address author;
    }

    // ── State ──
    address public owner;
    Entry[] public entries;
    mapping(string => uint256[]) private topicIndex;
    uint256 public totalEntries;

    // ── Events ──
    event EntryStored(
        uint256 indexed id,
        string topic,
        address indexed author,
        uint256 timestamp,
        uint256 blockNumber
    );
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    // ── Errors ──
    error OnlyOwner();
    error EmptyTopic();
    error EmptyAnalysis();
    error EntryNotFound();

    // ── Modifiers ──
    modifier onlyOwner() {
        if (msg.sender != owner) revert OnlyOwner();
        _;
    }

    // ── Constructor ──
    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    // ── Write Functions ──

    /**
     * @notice Store a new analysis entry on-chain.
     * @param topic The subject of the analysis
     * @param analysis The AI-generated analysis text
     * @return id The ID of the new entry
     */
    function storeEntry(string calldata topic, string calldata analysis) external onlyOwner returns (uint256 id) {
        if (bytes(topic).length == 0) revert EmptyTopic();
        if (bytes(analysis).length == 0) revert EmptyAnalysis();

        id = totalEntries;

        entries.push(Entry({
            id: id,
            timestamp: block.timestamp,
            blockNumber: block.number,
            topic: topic,
            analysis: analysis,
            author: msg.sender
        }));

        topicIndex[topic].push(id);
        totalEntries++;

        emit EntryStored(id, topic, msg.sender, block.timestamp, block.number);
    }

    /**
     * @notice Store a batch of entries in one transaction.
     * @param topics Array of topics
     * @param analyses Array of analyses (must match topics length)
     */
    function storeBatch(string[] calldata topics, string[] calldata analyses) external onlyOwner {
        require(topics.length == analyses.length, "Length mismatch");
        for (uint256 i = 0; i < topics.length; i++) {
            if (bytes(topics[i]).length == 0) revert EmptyTopic();
            if (bytes(analyses[i]).length == 0) revert EmptyAnalysis();

            uint256 id = totalEntries;
            entries.push(Entry({
                id: id,
                timestamp: block.timestamp,
                blockNumber: block.number,
                topic: topics[i],
                analysis: analyses[i],
                author: msg.sender
            }));
            topicIndex[topics[i]].push(id);
            totalEntries++;
            emit EntryStored(id, topics[i], msg.sender, block.timestamp, block.number);
        }
    }

    // ── Read Functions ──

    /**
     * @notice Get an entry by ID.
     */
    function getEntry(uint256 id) external view returns (Entry memory) {
        if (id >= totalEntries) revert EntryNotFound();
        return entries[id];
    }

    /**
     * @notice Get the latest entry.
     */
    function getLatestEntry() external view returns (Entry memory) {
        if (totalEntries == 0) revert EntryNotFound();
        return entries[totalEntries - 1];
    }

    /**
     * @notice Get all entry IDs for a specific topic.
     */
    function getEntriesByTopic(string calldata topic) external view returns (uint256[] memory) {
        return topicIndex[topic];
    }

    /**
     * @notice Get the last N entries (most recent first).
     * @param count Number of entries to return
     */
    function getRecentEntries(uint256 count) external view returns (Entry[] memory) {
        if (count > totalEntries) count = totalEntries;
        Entry[] memory result = new Entry[](count);
        for (uint256 i = 0; i < count; i++) {
            result[i] = entries[totalEntries - 1 - i];
        }
        return result;
    }

    // ── Admin ──

    /**
     * @notice Transfer ownership to a new address.
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }
}
