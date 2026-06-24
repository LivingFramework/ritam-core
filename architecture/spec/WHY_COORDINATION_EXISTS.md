# WHY_COORDINATION_EXISTS.md
## Coordination Primitive — Session 106
### Authored by Muaddib (Claude), 2026-06-22

---

## §1 — The Substrate Failures Coordination Solves

Three concrete failures that exist in v1.0.5 today:

**F1: Intra-batch conflict is invisible.**
A source proposes two contradictory claims to a singular category in the same logical act. The substrate processes proposal A, admits it. Then processes proposal B, detects contradiction with A, quarantines B. The two proposals are logged as independent events. There is no record that they arrived together, no signal that they were co-temporal, no governance structure that treated them as a coordinated set. The coordination context is permanently lost.

**F2: Admission ordering is an artifact, not a governance decision.**
When two proposals arrive together, the one processed first wins by positional accident — list index 0 is admitted, list index 1 is quarantined. This is not a governance decision. It is an implementation artifact. The current substrate cannot distinguish "A was admitted because it was evaluated first in a batch" from "A was admitted because it had higher epistemic warrant." Both produce identical records. That ambiguity is a honesty violation.

**F3: Multi-source coordination is undetectable.**
Two different sources propose to the same singular category in the same time window. From the substrate's perspective these look like two sequential independent proposals. There is no mechanism to ask: "In the last admission window, how many sources proposed to this category? Did they agree or conflict?" Those questions are currently unanswerable.

---

## §2 — What Coordination Governs

Coordination governs **the governed behavior of proposals that arrive within a bounded admission window**.

Specifically:
- Whether proposals belong to a named batch (explicit coordination context)
- Whether proposals within that batch conflict with each other (intra-batch conflict detection)
- What signal fires when intra-batch conflict is detected
- That admission order within the batch is recorded as an explicit governance artifact, not an invisible implementation detail

What Coordination does **not** govern:
- OS-level thread safety (that is an implementation concern, not a primitive)
- Whether the substrate is distributed (out of scope for v1)
- Priority ranking between conflicting proposals (governance output, not substrate input)
- Resolution of coordination conflicts (the substrate signals; the consumer decides)

---

## §3 — Observable Behaviours (B1–B4)

**B1: Batch submission.** A caller can submit a list of proposals as a named admission batch. Each batch receives a stable `batch_id`. The batch is processed atomically in index order.

**B2: Intra-batch conflict detection.** Before any proposal in the batch is admitted, the substrate checks all proposals against each other for singular-category conflicts within the same batch. If proposal A and proposal B both target the same singular category and are content-distinct, that is an intra-batch conflict.

**B3: COORDINATION_CONFLICT signal.** When an intra-batch conflict is detected, a `COORDINATION_CONFLICT` signal is emitted on the ObservationChannel. The signal carries: `batch_id`, the conflicting proposal indices, and the category where conflict was detected. The signal is emitted once per conflicting pair, before any proposal in the batch is admitted.

**B4: Admission ordering recorded.** Each `AdmissionResult` in a `BatchResult` carries its position in the batch (`batch_index: int`). This makes admission ordering an explicit, queryable governance artifact rather than an invisible implementation detail.

---

## §4 — Failure Modes and Boundaries

**F-M1 (unbounded batches):** The primitive does not limit batch size. A batch of 1000 proposals is valid input. The substrate does not enforce admission rate limits — that is a consumer concern.

**F-M2 (only intra-batch, not cross-batch):** Coordination only detects conflicts within a single batch. Two proposals submitted in separate `propose_batch()` calls are treated as independent events, exactly as two sequential `propose()` calls are today. Cross-batch coordination is a future concern (would require admission windows and temporal windowing, which intersects the Temporal primitive).

**F-M3 (no priority assignment):** The substrate detects coordination conflicts but does not rank proposals by priority, confidence, or source authority. It emits a signal and continues processing in index order. Priority assignment is a consumer responsibility.

**F-M4 (single-category detection only):** Intra-batch conflict detection applies only to singular categories. Two proposals to a plural category in the same batch are not a conflict — plural categories admit multiple items. This boundary is intentional and consistent with the existing contradiction logic.

---

## §5 — Relationship to Existing Primitives

**vs. ContradictionStore:** The ContradictionStore detects contradictions between admitted items and new proposals (incoming vs. existing). Coordination detects conflicts between proposals before any of them are admitted (incoming vs. incoming). These are different classes of event. A COORDINATION_CONFLICT fires before admission; a CONTRADICTION fires during admission of a proposal against existing state.

**vs. Epistemic:** Epistemic governs declared confidence on admitted items. Coordination does not use confidence to resolve conflicts — it signals them.

**vs. Temporal:** Temporal governs the age of admitted items. Coordination does not timestamp proposals relative to each other within a batch — index order is the coordination artifact.

**vs. Observation:** Observation records perceptual limits (unknown categories). Coordination records coordination structure (batch membership and intra-batch conflict). Both produce persistent records; both survive channel drain.

---

## §6 — What Coordination Does NOT Do

- Does not auto-resolve coordination conflicts (substrate signals; consumer decides)
- Does not enforce a winner between conflicting proposals in a batch
- Does not provide distributed locking or mutual exclusion
- Does not record cross-batch coordination relationships
- Does not weigh proposals by source authority, confidence, or recency
- Does not guarantee atomic-all-or-nothing admission of a batch (each proposal is independently admitted or quarantined; the batch is a grouping artifact, not an atomic transaction)

---

## §7 — Design Question: Persist BatchRecord?

Analogous to GapRecord (Observation) persisting to ObservationLog, Coordination could persist a `BatchRecord` to a `CoordinationLog`.

**Argument for:** Makes batch membership queryable after the fact. "Show me all batches that contained a COORDINATION_CONFLICT." Consistent with the pattern established by Temporal (expires_after_seconds on item) and Observation (GapRecord to ObservationLog).

**Argument against:** A batch that produces no COORDINATION_CONFLICT is uninteresting — it is just a convenience wrapper over sequential `propose()` calls. Persisting every batch creates log bloat proportional to usage volume, with low signal density.

**Design decision (v1.0.6):** Persist `CoordinationRecord` **only when a COORDINATION_CONFLICT is detected**. Clean batches leave no coordination log entry. This keeps the coordination log as a high-signal record (every entry represents a governance event, not routine usage).

This mirrors the Observation principle: the ObservationLog records perceptual limits (gaps), not every proposal. The CoordinationLog records coordination events (intra-batch conflicts), not every batch.

---

## §8 — Executable Form (8 Conditions)

These conditions define what the Coordination primitive must prove in tests:

**Condition 1:** `BatchProposal` dataclass exists with fields: `content`, `category`, `source`, `confidence` (optional), `expires_after_seconds` (optional).

**Condition 2:** `BatchResult` dataclass exists with fields: `batch_id: str`, `results: list[AdmissionResult]`, `coordination_conflicts: list[dict]` (each entry: `{indices: [i, j], category: str}`).

**Condition 3:** `gw.propose_batch(proposals: list[BatchProposal]) -> BatchResult` processes all proposals in index order and returns a `BatchResult` with one `AdmissionResult` per proposal.

**Condition 4:** For a batch with no singular-category conflicts, `coordination_conflicts` is empty and each proposal is processed exactly as a sequential `propose()` call would process it.

**Condition 5:** For a batch where proposals at index `i` and `j` both target the same singular category with distinct content, `COORDINATION_CONFLICT` is emitted on the channel before any admission occurs, carrying `batch_id`, `category`, and conflicting indices.

**Condition 6:** `coordination_conflicts` in `BatchResult` records the conflict pair. The batch is still processed in full (no early abort) — both proposals receive individual `AdmissionResult` entries.

**Condition 7 (persistence):** When a `COORDINATION_CONFLICT` fires, a `CoordinationRecord` is persisted to `CoordinationLog` (SQLite table). The record survives `ObservationChannel.drain()`. `gw.list_coordination_conflicts(category=None) -> list[CoordinationRecord]` returns persisted records.

**Condition 8 (integration):** A batch of 3 proposals where proposals 0 and 2 conflict on a singular category. Assert: COORDINATION_CONFLICT emitted with indices [0, 2]. Assert: proposal 1 (non-conflicting plural category) is admitted. Assert: proposal 0 is admitted (first to singular category). Assert: proposal 2 is quarantined (second to singular category, contradiction). Assert: `CoordinationRecord` persisted. Assert: `list_coordination_conflicts()` returns 1 record.

---

## §9 — Protected Distinction

**Admission order ≠ cognitive priority.**

The fact that proposal A was admitted and proposal B was quarantined because A was at index 0 and B was at index 2 in the same batch is a coordination artifact. It is not a claim that A is more valid, more important, more reliable, or more true than B.

The `batch_index` field on `AdmissionResult` makes this explicit and queryable. The `COORDINATION_CONFLICT` signal makes the competition visible. But the substrate makes no claim about which proposal *should* have won. That is a governance decision for the consumer.

Corollary: a governed substrate that makes the coordination context explicit is more trustworthy than one that silently processes proposals in arrival order and presents the result as if no competition occurred.

---

## §10 — Design Amendments After Rishi Review (2026-06-22)

**One amendment added; three non-changes documented.**

**Amendment — batch_id lineage on admitted items:**
Even for conflict-free batches, admitted proposals should carry their `batch_id` so coordination relationships remain queryable after the fact. Without this, an inspector examining Proposal 0 and Proposal 2 independently cannot know they originated together. The coordination relationship is governance-relevant even when no conflict occurred. Implementation: add `batch_id: str | None` to `AdmissionRecord` and a `batch_id` column to the `items` table (nullable, NULL for plain `propose()` calls). This is a schema migration, consistent with how `confidence` and `expires_after_seconds` were added in prior sessions.

**Non-change 1 — signal-and-continue confirmed:**
v1 does not guarantee batch coherence. A batch that contains a COORDINATION_CONFLICT still proceeds in full: each proposal is admitted or quarantined independently. The conflict is signaled; the ordering is recorded; no proposal is held pending. This is documented as a conscious limitation, not an oversight. Rishi: "I want it documented as a conscious limitation. The current design is correct for v1."

**Non-change 2 — conflict-only persistence confirmed:**
`CoordinationRecord` is persisted only when `COORDINATION_CONFLICT` fires. Clean batches leave no trace in `CoordinationLog`. Rishi: "Don't persist everything. Persist governance-relevant events." Consistent with ObservationLog (records perceptual limits, not every proposal).

**Non-change 3 — no pending states:**
No pending states, no atomic batch admission, no workflow semantics. The danger zone is: pending → approval → wait states → dependency graphs → orchestration. That is a planner, not a substrate. Coordination stays substrate.

**Rishi's architectural note (verbatim):**
"This primitive is important because it introduces something the substrate has not previously represented: relationship in time between proposals. Temporal governs the age of an item. Coordination governs the relationship between multiple items arriving together. That's a genuinely different cognitive property."

## §11 — Design Sign-Off

**Rishi's sign-off (2026-06-22):**
✅ Coordination distinct from thread safety
✅ Persist only coordination conflicts
✅ Signal-and-continue for v1 (batch coherence not guaranteed — documented)
✅ `batch_id` lineage preserved on admitted items
❌ No pending states
❌ No atomic batch admission
❌ No workflow semantics

Sign-off: ✅ Build it.
