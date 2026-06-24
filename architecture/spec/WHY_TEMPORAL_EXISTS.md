# Why Temporal Exists

*Session 103 · 2026-06-21 · Behavioural definition — not implementation*

---

## 1. The Problem

Every item in the current substrate is admitted once and remains valid indefinitely until explicitly retracted. There is no notion of *when* something was true, *whether it is still true*, or *whether its age changes its epistemic status*.

This creates three silent failures that the current substrate cannot detect or surface:

**Failure 1 — Stale admission.**
A working hypothesis admitted six months ago coexists in the substrate with one admitted yesterday as if both are equally current. The substrate has no way to distinguish "recently admitted and actively held" from "admitted long ago and possibly forgotten." A consumer reading `list_admitted("working-hypothesis")` gets both, ranked only by insertion order, with no signal that one may be stale.

**Failure 2 — Time-blind contradiction detection.**
The singular constraint fires when two items *coexist* in the same category. But it cannot detect when an item has effectively been superseded by the passage of time rather than by an explicit replacement. If a task was admitted as "current-task" three weeks ago and never retracted, the substrate treats it as active. No signal fires. No repair is suggested.

**Failure 3 — No expiry contract.**
Consumers that need time-bounded items — a task that expires if not completed, a hypothesis that should be re-evaluated after N days, a memory entry with a defined decay window — have no substrate-level mechanism to express or enforce this. They either implement it themselves (violating the abstraction boundary by adding logic that belongs in the substrate) or silently skip it (leaving time-sensitivity unrepresented).

**The gap in plain terms:** the substrate currently governs *what* is admitted and *whether* it conflicts. It does not govern *when* something was admitted, *how long* it has been active, or *what should happen* when its temporal context becomes relevant.

---

## 2. What Temporal Governs

Temporal is not a clock. It is not a scheduler. It is not a cron job.

Temporal is the primitive that makes **age a first-class property of admitted items** and **time-relatedness a first-class signal** in the substrate's observation channel.

It governs three things:

**2.1 — Admission timestamp visibility**
Every item already has `admitted_at`. Temporal makes this queryable as a substrate property, not just a stored field. Consumers should be able to ask: "what is the age of this item?" and get a governed answer — not by reading `admitted_at` directly from an `AdmissionRecord` and computing it themselves.

**2.2 — Temporal context on proposal**
When a consumer proposes an item, it should be able to supply a temporal context: "this item is valid for N seconds" or "this item was valid as of timestamp T." The substrate records this as part of the admission contract, not as free-form content.

**2.3 — Age signals**
The ObservationChannel currently emits signals for admission, quarantine, retraction, and repair. Temporal adds one new signal class: `TEMPORAL_ALERT` — emitted when an item's age crosses a threshold defined at proposal time. This is not automated retraction (I2: Recoverability over perfection). It is a signal. The consumer — and ultimately the human — decides what to do.

---

## 3. Observable Behaviour

Temporal exists if and only if these behaviours are observable at runtime:

**B1 — Age is queryable without accessing private fields.**
A consumer can ask `gw.age_of(item_id)` and receive a duration. It does not compute `datetime.now() - record.admitted_at` itself.

**B2 — Proposals can carry expiry contracts.**
`gw.propose(content, category, source, expires_after_seconds=N)` records the expiry contract in the substrate. The contract is visible in the `AdmissionRecord`.

**B3 — TEMPORAL_ALERT signals fire.**
When an item's age exceeds its expiry contract, the ObservationChannel emits a `TEMPORAL_ALERT` signal containing `item_id`, `category`, `admitted_at`, `expired_at`, and `age_seconds`. The item is NOT automatically retracted. The signal is the substrate's contribution; action is the consumer's responsibility.

**B4 — Temporal context is provenance.**
The expiry contract and any temporal context supplied at proposal time appear in the item's provenance record. This satisfies I3 (Explicit State Over Implicit Reconstruction) — the temporal reasoning is stored, not reconstructed.

---

## 4. Failure Modes

**F1 — Silent staleness (current failure, pre-Temporal).**
Items remain active indefinitely with no signal. Consumer reads stale data. No alert. No repair suggestion. *Temporal resolves this via B3.*

**F2 — Expiry contract ignored.**
Consumer sets `expires_after_seconds=N` but never drains the ObservationChannel. `TEMPORAL_ALERT` fires but is never read. The substrate has done its job; the consumer has not listened. *This is not a substrate failure — it is a consumer integration failure. The substrate's job is to emit, not to force action.*

**F3 — Clock skew across distributed consumers.**
Two consumers using the same substrate but different system clocks could observe different ages for the same item. *Mitigation: all temporal calculations use the substrate's clock, not the consumer's. admitted_at is set by the gateway at admission time using `_now()`. Age is computed by the gateway relative to its own clock.*

**F4 — Expiry contract on plural categories.**
A consumer sets expiry on an evidence item in a plural category. Multiple evidence items may have different expiry contracts. The substrate emits a separate `TEMPORAL_ALERT` for each. *This is correct behaviour — plural categories accumulate independently, and each item carries its own temporal contract.*

---

## 5. Repair Modes

Temporal introduces a new repair surface: **temporal contradiction**.

When a `TEMPORAL_ALERT` fires, the consumer faces a decision:

- **Retract and replace** — retract the expired item; propose a fresh one. This is the same repair pathway as a singular-category conflict.
- **Extend** — re-propose the same content with a new expiry contract. The substrate treats this as a new admission (new `item_id`, new `admitted_at`).
- **Hold as stale** — mark the alert as acknowledged but take no action. The item remains admitted but is known to be past its expiry. The consumer records this decision explicitly.

The RepairSuggestion mechanism (already in the substrate) should be extended to include temporal repair pathways when a `TEMPORAL_ALERT` fires. This keeps the repair model consistent: every governance event produces a structured repair suggestion with named pathways.

---

## 6. Relationship to State and Memory

**Relationship to State:**
State (as a substrate primitive) governs *what is currently true*. Temporal governs *how long it has been true and whether that duration is significant*. They are complementary. A state item without temporal context is valid forever. A state item with temporal context has an explicit validity window. Temporal makes State time-aware without replacing it.

**Relationship to Memory:**
Memory governs *what has been retained and what has decayed*. The Memory primitive (GovernedAgentMemory, S088) already implements decay via `decay_enabled` in SubstrateConfig — but this is a bulk decay mechanism, not item-level temporal governance. Temporal is more precise: individual items carry individual expiry contracts. The two mechanisms should coexist. Bulk decay handles ambient forgetting; Temporal handles explicit time-bounded commitments.

**Relationship to Repair:**
Temporal extends the repair surface. Every `TEMPORAL_ALERT` should produce a `RepairSuggestion` with temporal-specific pathways (RETRACT_AND_REPLACE, EXTEND, HOLD_AS_STALE). This keeps the repair model uniform across all governance events.

---

## 7. What Temporal Does NOT Do

- **Does not automatically retract items.** I2 (Recoverability over Perfection) — the substrate signals; the consumer acts.
- **Does not implement scheduling.** No background threads, no cron, no async. Temporal signals fire when the substrate is queried, not on a wall-clock timer. This preserves the substrate's synchronous, testable design.
- **Does not replace Memory decay.** Decay is ambient and probabilistic. Temporal contracts are explicit and item-level. Both are needed.
- **Does not govern semantic freshness.** Whether content is *still true in the world* is outside the substrate's scope. Temporal governs *age of admission*, not *truth over time*.

---

## 8. Executable Form

Temporal exists when:
1. `AdmissionRecord` carries `expires_after_seconds: int | None` and `expired_at: str | None`
2. `gw.propose(..., expires_after_seconds=N)` stores the expiry contract
3. `gw.age_of(item_id) -> float` returns seconds since `admitted_at`
4. `gw.check_expired() -> list[AdmissionRecord]` returns all items past their expiry contract
5. `SignalType.TEMPORAL_ALERT` is a member of the `SignalType` enum
6. The ObservationChannel emits `TEMPORAL_ALERT` signals when `check_expired()` is called and expired items are found
7. A `RepairSuggestion` is produced for each expired item with pathways: `RETRACT_AND_REPLACE`, `EXTEND`, `HOLD_AS_STALE`
8. A test exists that: admits an item with `expires_after_seconds=1`, waits 2 seconds, calls `check_expired()`, and asserts a `TEMPORAL_ALERT` signal was emitted with correct fields

*When all eight conditions are true and tested, Temporal exists.*

---

*Supporting evidence — not substrate. Substrate is the runtime. This document is the behavioural specification that precedes it.*

---

## 9. Protected Distinction — Age of Admission vs Age of Truth

*Added after Rishi's review (Session 103)*

Temporal governs **age of admission** — how long ago an item entered the substrate.

It does not govern **age of truth** — whether the content of the item is still true in the world.

These are different things. An item admitted three years ago may still be true. An item admitted yesterday may already be false. The substrate cannot know. It can only know when the item was admitted and whether the consumer has declared an expiry contract.

**The dangerous drift to prevent:**

> "This item has expired, therefore it is false."

This is wrong. The substrate emits a `TEMPORAL_ALERT` because the item is old relative to its declared contract. It says nothing about whether the content is still valid. That judgment belongs to the consumer and ultimately to the human.

**Why this matters architecturally:** if Temporal is conflated with epistemic validity, it becomes Epistemology — a different primitive entirely. Temporal is a clock-and-contract mechanism. Epistemology governs degrees of belief, confidence, and revision. Keeping them separate preserves both.

**Implementation rule:** `TEMPORAL_ALERT` signal payloads must never include language like "expired claim" or "invalid item." The correct language is "item age exceeds declared contract." The signal is about time, not truth.

---

## 10. Rishi's One-Line Review (Session 103)

> "Temporal is the first post-v1 primitive I've seen that clearly solves a substrate failure rather than merely extending an abstraction. Implement it and see whether the runtime naturally adopts it; if it does, that is strong evidence the primitive model is discovering architecture rather than inventing categories."

**Primitive confidence table (Rishi, Session 103):**

| Primitive | Confidence |
|---|---|
| Governance | Very High |
| Memory | Very High |
| Observation | Very High |
| Repair | High |
| Temporal | High (pending implementation) |
| State | Unknown |
| Ontology | Unknown |
| Epistemic | Unknown |
| Coordination | Unknown |

**Architectural note:** Rishi's reading is that Temporal may introduce a genuinely new axis — Age — distinct from Content, Conflict, and Category. If the implementation confirms this, it is evidence that the substrate model is discovering primitives rather than manufacturing them.

*Append-only: this section records the review that preceded implementation. Do not edit.*
