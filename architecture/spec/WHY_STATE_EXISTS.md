# WHY_STATE_EXISTS.md

**Primitive:** State
**Version:** v1.1.1
**Author:** Muaddib (Claude), Ritam Session 115
**Status:** SIGNED OFF

---

## §1 The Concrete Substrate Failure This Primitive Addresses

Without an explicit State primitive, a substrate has no coherent account of what it currently believes.

Items are admitted. Items may be retracted. But without State, there is no single authoritative answer to the question: *what is the substrate's current position on this topic?* The admission log records what entered; the contradiction store records conflicts; but the current operative belief — the answer the substrate would give right now if asked — is not a first-class object. It must be reconstructed by traversing history, resolving retractions, and inferring which beliefs won.

This creates a specific failure: **the substrate's current state is implicit, reconstructable-in-principle but not observable in practice.** Diagnosis becomes archaeology. When a governed system produces an unexpected output, the investigator must reconstruct current state from historical records rather than reading it directly.

State exists to make current operative belief an explicit, queryable, governed object — distinct from the history that produced it.

---

## §2 Why "State" and Not "Current Beliefs"

"Current beliefs" implies epistemology. State is simpler and more structural: it is the coherent operating condition of the substrate at a given moment. It includes active admissions, retracted items, current contradiction set, and repair status. It is the answer to "what is true right now from the substrate's perspective?" — not "what does the substrate believe with what confidence?" (that is the Epistemic primitive).

State is the synchronic slice. History is the diachronic record. Both are necessary; they are not the same thing.

---

## §3 What Breaks Without State

**1. Opacity of current position.** Without explicit State, determining what the substrate currently holds requires traversing admission records, contradiction records, and repair records and resolving them. This is expensive, error-prone, and not possible at query time without full log access.

**2. Ungoverned transitions.** State transitions — admitting a new belief, retracting an old one, resolving a contradiction — are governance events. Without an explicit State object, these transitions are implicit side effects of admission and repair operations. They cannot be signalled, audited, or made observable as state changes specifically.

**3. Incoherence under concurrent update.** In a substrate receiving multiple proposals in sequence, the coherent current state between proposals is undefined without explicit State management. What the substrate "currently holds" is ambiguous mid-sequence.

**4. No recovery target.** Repair requires knowing what state is being repaired toward. Without an explicit State primitive, "recover to a coherent state" has no defined target. The Repair primitive depends on State for its postcondition.

---

## §4 What the State Primitive Provides

- An explicit, queryable representation of what the substrate currently holds as operative
- Governed transitions: every change to current state is a first-class governance event with a signal and a record
- A defined recovery target for the Repair primitive
- Separation between current state (synchronic) and history (diachronic), both accessible but distinct
- Observable state-change events that downstream consumers and observers can subscribe to

---

## §5 Relationship to Other Primitives

**Memory** tracks how beliefs age and decay over time — it operates on the history of admissions. State is what those admissions resolve to right now. Memory answers "how did we get here?"; State answers "where are we?"

**Governance** determines admission criteria — what enters the substrate. State records what has entered and remains operative. Governance is the gate; State is what passed through it.

**Repair** moves the substrate from an incoherent state to a coherent one. Without explicit State, "coherent" has no definition. Repair's postcondition is a valid State.

**Observation** makes State visible to external consumers. State is the object; Observation is the channel through which it is reported.

---

## §6 Evidence

The State primitive is implemented as the operative layer within `AdmissionGateway` and `Substrate` in `runtime/v0.1/ritam/runtime/v01/`. State transitions (ADMITTED, QUARANTINED, REJECTED, RETRACTED) are first-class signals emitted on every governance event. Current state is queryable via the public API at any point. All 146 tests operate against explicit state — no test reconstructs state from logs.

The adversarial audit (Session 110) confirmed that State coherence holds under all six attack scenarios, including the GAP-6 scenario where category removal during an in-flight repair threatened to create an unobservable state inconsistency. The REPAIR_ONTOLOGY_CONFLICT signal (Session 111) addresses this by making the inconsistency a first-class State event rather than a silent condition.

---

*Authored Session 115 · 2026-06-24 · v1.1.1*
