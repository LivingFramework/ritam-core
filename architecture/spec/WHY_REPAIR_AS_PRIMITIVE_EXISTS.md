# WHY_REPAIR_AS_PRIMITIVE_EXISTS.md

**Primitive:** Repair-as-Primitive
**Version:** v1.0.8 (target)
**Author:** Muaddib (Claude), Ritam Session 108
**Status:** DRAFT — awaiting Rishi sign-off

---

## §1 The Concrete Substrate Failure This Primitive Addresses

Repair is currently a suggestion that disappears.

When a governance event fires — QUARANTINE, contradiction detected — the substrate
generates a `RepairSuggestion` and attaches it to the `AdmissionResult`. The suggestion
contains a diagnosis, a list of `ResolutionPathway` options, and a timestamp. The caller
receives it.

Then nothing.

The substrate has no way to know whether the suggestion was read. It cannot know whether
the caller chose a pathway. It cannot know whether the repair was attempted. It cannot
know whether the attempt succeeded. Once the `AdmissionResult` is returned, the
suggestion is gone from the substrate's awareness entirely.

This is the failure: **the substrate can detect that something is wrong, and it can
propose how to fix it, but it cannot observe whether it was fixed.** The recovery loop
— the most critical part of any governed system — is invisible.

Consider what this means in practice. A singular category fires QUARANTINE on a second
conflicting admission. A `RepairSuggestion` is generated with pathways:
`RETRACT_AND_REPLACE`, `DOWNGRADE`, `REQUEST_EVIDENCE`. The consumer reads it. Chooses
`RETRACT_AND_REPLACE`. Retracts the old item. Admits the new one. Everything is
correct — but the substrate has no record of any of this. Future audit of the
contradiction log shows: quarantine at time T, resolution: unknown.

That is not a governed system. That is a monitoring system with a suggestion box.

**Repair-as-Primitive exists to make the recovery loop a first-class governed act
with observable state, durable records, and signals at every transition.**

---

## §2 Why "Primitive" and Not "Feature"

Every preceding primitive governs a specific property of cognition:
- Temporal governs age
- Epistemic governs confidence
- Observation governs perceptual limits
- Coordination governs concurrent proposals
- Ontology governs conceptual vocabulary

Repair governs **recovery**. It is not an optional feature bolted onto governance —
it is the mechanism by which a governed system demonstrates that governance is not
merely descriptive but actionable. Without Repair, governance produces records of
failure. With Repair, governance produces records of failure *and* records of what
was done about them. The second is what makes a substrate trustworthy over time.

Invariant I5 (Observable Repair Loops) has been in the constitution since Session 001.
This primitive is its operational implementation.

---

## §3 The Lifecycle: PENDING → ACKNOWLEDGED → EXECUTED → VERIFIED

Four states. Each transition is a governed act.

```
PENDING
  │
  ▼ acknowledge_repair(repair_id)
ACKNOWLEDGED
  │
  ▼ execute_repair(repair_id, notes=)
EXECUTED
  │
  ▼ verify_repair(repair_id, outcome=)
VERIFIED
```

**PENDING:** The repair suggestion has been generated and persisted. The substrate
knows a repair is needed. No human or agent has yet engaged with it.

**ACKNOWLEDGED:** A caller has declared "I have read this repair suggestion and I am
taking responsibility for it." This is not a claim that the repair has been done —
only that it has been seen and is being handled. This state matters because it
distinguishes "waiting for attention" from "in progress."

**EXECUTED:** A caller has declared "The repair action has been carried out." In v1,
this is a declaration, not an automated action. The substrate records the claim and
optional notes. It does not verify the claim independently — that is VERIFIED's job.

**VERIFIED:** A caller has declared "The repair outcome has been confirmed." This is
the terminal state. Optional outcome notes are recorded. This is the state that
closes the governance loop — the substrate now has a complete record from detection
to resolution.

---

## §4 What "Execute" Means in v1

This is the most important design question for this primitive.

The temptation is to make `execute_repair()` actually perform the repair — retract
the conflicting item, update the category, call `add_category()`. That would be
automation. And automation without explicit human authorization violates Invariant I1
(Governance Before Autonomy): the substrate governs; it does not act autonomously.

**In v1, execute is a declaration.**

`execute_repair(repair_id, notes="Retracted item X, admitted item Y")` records that
the caller took the action described. The substrate does not verify that item X was
actually retracted. It trusts the declaration and updates the lifecycle state.

This is not a weakness — it is an architectural choice. The substrate's role is to
make the recovery loop *visible*, not to automate it. A substrate that autonomously
retracts and re-admits items is making governance decisions without a human in the
loop. That is exactly what Ritam is designed to prevent.

The same logic applies to `verify_repair()`. Verification in v1 is a declaration:
"I have confirmed the outcome is correct." The substrate records it.

**Protected distinction: generating a repair ≠ acknowledging it ≠ executing it ≠
verifying the outcome.** These are four distinct governance events. Collapsing them
would hide the most important information: at which stage did the recovery loop break?

---

## §5 What Happens to Existing RepairSuggestion

`RepairSuggestion` already exists as a frozen dataclass (Session 094). It is generated
on QUARANTINE events and attached to `AdmissionResult.repair`. This does not change.

What changes: when a `RepairSuggestion` is generated, it is now *also* persisted as
a `RepairRecord` in the `repair_log` table with status `PENDING`. The repair is no
longer just an annotation on a result — it has a durable identity and a lifecycle.

The `RepairSuggestion` remains the structured proposal (what is wrong, what the
options are). The `RepairRecord` is the governance entity (what lifecycle state the
repair is in, what was done about it).

---

## §6 The RepairRecord Dataclass and RepairLog

```
RepairRecord:
  repair_id:      str          # stable UUID — links to RepairSuggestion
  quarantine_id:  str          # links to ContradictionStore record
  category:       str          # singular category that triggered the repair
  status:         str          # "pending" | "acknowledged" | "executed" | "verified"
  pathway_chosen: str | None   # pathway_id from ResolutionPathway, set on execute
  notes:          str | None   # caller-supplied notes, set on execute or verify
  outcome:        str | None   # caller-supplied outcome description, set on verify
  created_at:     str          # ISO timestamp — when repair was generated
  updated_at:     str          # ISO timestamp — last lifecycle transition
```

`RepairLog` is a SQLite table. Lifecycle transitions update the existing row
(status, pathway_chosen, notes, outcome, updated_at) — they do not write new rows.
One row per repair, updated in place. The history of transitions is captured by the
signals emitted at each step, not by multiple rows.

---

## §7 The Signal: REPAIR_LIFECYCLE

`REPAIR_LIFECYCLE` fires on every state transition. The signal payload records:
- `repair_id`: the repair being transitioned
- `from_status`: the previous state
- `to_status`: the new state
- `category`: the category involved
- `notes`: any caller-supplied context

`REPAIR_TRIGGERED` already exists in `SignalType` (Session 094) — it fires when a
RepairSuggestion is generated. In this primitive, `REPAIR_TRIGGERED` is reused as the
signal for the PENDING state (repair created). `REPAIR_LIFECYCLE` is the new signal
for subsequent transitions (ACKNOWLEDGED, EXECUTED, VERIFIED).

This keeps signal semantics clean: REPAIR_TRIGGERED = "a repair need was detected";
REPAIR_LIFECYCLE = "a repair is moving through its governed lifecycle."

---

## §8 API

```python
# Lifecycle transitions — called after a RepairSuggestion is received
gw.acknowledge_repair(repair_id)
# → status: PENDING → ACKNOWLEDGED
# → emits REPAIR_LIFECYCLE(from="pending", to="acknowledged")

gw.execute_repair(repair_id, pathway_chosen="RETRACT_AND_REPLACE", notes="Retracted item X")
# → status: ACKNOWLEDGED → EXECUTED
# → emits REPAIR_LIFECYCLE(from="acknowledged", to="executed")

gw.verify_repair(repair_id, outcome="Contradiction resolved. New item admitted cleanly.")
# → status: EXECUTED → VERIFIED
# → emits REPAIR_LIFECYCLE(from="executed", to="verified")

# Query
gw.list_repairs(status="pending")     # all unacknowledged repairs
gw.list_repairs(status="verified")    # all closed repairs
gw.list_repairs()                     # all repairs
```

---

## §9 Failure Modes and How They Are Governed

**F1 — Transition out of order (e.g. verify before execute).**
Result: error. Transitions are strictly sequential. You cannot verify a repair that
has not been executed. You cannot execute a repair that has not been acknowledged.
The substrate enforces the order.

**F2 — repair_id not found.**
Result: error with descriptive message. No state change.

**F3 — Re-acknowledging an already-acknowledged repair.**
Result: no-op or error. The repair is already past PENDING; re-acknowledging does
nothing. This prevents duplicate signals from noisy callers.

**F4 — Repair generated but never acknowledged.**
Result: the repair sits in PENDING indefinitely. `list_repairs(status="pending")`
surfaces it. This is not a substrate failure — it is information. A pile of PENDING
repairs is a governance signal: the substrate is producing repair suggestions that
nobody is acting on.

---

## §10 Relationship to Other Primitives

**Ontology:** A repair might involve adding a category (e.g. OBSERVATION_GAP triggers
a repair suggestion to call `add_category()`). In v1, this relationship is not
automated — the repair record notes what was done; the ontology mutation is a separate
governed act. In v2, a typed link between RepairRecord and OntologyRecord is the
natural forward step (INSIGHT-126 forward pointer).

**Observation:** A repair for an OBSERVATION_GAP follows the same lifecycle as a
repair for a QUARANTINE event. The gap-to-resolution pathway (OBSERVATION_GAP →
`add_category()` → ONTOLOGY_MUTATION) gains an explicit wrapper: the repair record
tracks whether that pathway was acknowledged, executed, and verified.

**Contradiction:** Existing `ContradictionStore.get_repair()` and `mark_resolved()`
remain in place. The Repair primitive's `RepairLog` is a parallel, more granular
governance layer — it does not replace the ContradictionStore's resolved flag; it
enriches it.

---

## §11 What This Closes

With Repair-as-Primitive, all 9 substrate primitives are implemented:

| Tier | Primitive | Session | Status |
|---|---|---|---|
| **Cognition** | Temporal | S103 | ✅ |
| **Cognition** | Epistemic | S104 | ✅ |
| **Cognition** | Observation | S105 | ✅ |
| **Cognition** | Coordination | S106 | ✅ |
| **Structure** | Ontology | S107 | ✅ |
| **Governance Lifecycle** | Repair-as-Primitive | S108 | 🔨 this session |
| **Foundation** | State | S001–S079 | ✅ |
| **Foundation** | Memory | S001–S079 | ✅ |
| **Foundation** | Governance | S001–S079 | ✅ |

The substrate is complete. What comes after Phase 4 is not more primitives — it is
validation, integration, and the research question of whether these 9 primitives are
truly sufficient for governed cognition or whether new failure modes will expose gaps.
That is Phase 5.

---

*Awaiting Rishi sign-off before implementation.*

---

## Session 111 Addendum — Cross-Primitive Context Mutation (GAP-6 Remediation)

**Date:** 2026-06-22 · **Author:** Muaddib (Session 111)

### What GAP-6 Revealed

Adversarial audit (Session 110) found that `remove_category()` did not emit any governance
signal when a PENDING/ACKNOWLEDGED/EXECUTED repair referenced the category being removed.
The repair could complete its lifecycle against an ontological context that no longer
existed in the substrate. This is an **Ontology/Repair cross-primitive interaction gap**.

### The Fix (Option B — Warning Flag)

`remove_category()` now:
1. Queries `repair_log` for in-flight repairs (status IN pending, acknowledged, executed) in the removed category
2. Emits `REPAIR_ONTOLOGY_CONFLICT` (new `SignalType`) for each, AFTER the `ONTOLOGY_MUTATION` signal
3. Does NOT block the repair lifecycle — open-world semantics (INSIGHT-135)

### Architectural Principle Established (INSIGHT-136)

**Governance gates must fire on context mutation, not only on event admission.**

A repair is admitted under an ontological context. When that context changes (category
removed), a governance signal must fire — even though the repair's own state did not
change. Cross-primitive interactions are first-class governance events.

### Specification Requirement

CH-Repair (Chapter 8 of canonical spec) must include:
- A "cross-primitive context mutation" section
- A table of known cross-primitive interaction points
- The invariant: any primitive mutation that affects an in-flight operation in another
  primitive MUST emit an observable governance signal

CH-Ontology (Chapter 7) must cross-reference this requirement.

**INSIGHT-136, INSIGHT-140, ADR-019 govern this requirement.**
