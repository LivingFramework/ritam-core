# WHY_INTEGRATION_TEST_EXISTS.md
## Phase 5 — Integration Test Design
### Session 109 · Authored 2026-06-22

---

## §1 The Problem This Solves

Phase 4 proved each of the nine substrate primitives individually. Each primitive has:
- A WHY_*_EXISTS.md design document
- A typed dataclass and signal
- A persisted table in SQLite
- A set of unit tests proving isolated behaviour

What has NOT been proven is this:

> Do all nine primitives operate coherently together when a real consumer
> drives the substrate through a realistic, multi-step scenario?

This is a fundamentally different claim from "each part works." A substrate is not nine
working parts. A substrate is nine parts that remain governed when they interact.

NORTH_STAR §3 states success requires "another system can be built on top of it" and that
the substrate "proves a stated capability, not merely that it executes." Nine passing unit
test suites prove execution. The Integration Test proves capability.

---

## §2 The Test Criterion

The integration test passes if and only if:

> A single consumer scenario exercises all nine primitives, and for each primitive,
> the governance record is non-empty, consistent, and auditable at the end of the run.

If any primitive is removed from the substrate, the scenario must fail — either by raising
an error, or by producing an empty governance record for that primitive's contribution.

This is the "necessary and sufficient" criterion: every primitive must be load-bearing,
not merely reachable.

---

## §3 The Consumer: GovernedResearchLog

The integration consumer is called **GovernedResearchLog**. It models a research assistant
that ingests claims about a topic over time, governs what it believes, and maintains a
fully auditable record of every decision — including what it got wrong and how it recovered.

This consumer was chosen because:
1. It requires all nine primitives to function correctly (no primitive is decorative)
2. It maps to a domain humans can reason about (research, claims, evidence, conclusions)
3. It creates natural pressure on singular categories (you can only hold one conclusion)
4. It creates natural pressure on repair (conclusions get overturned)
5. It creates natural pressure on observation (evidence gaps are real)

---

## §4 Primitive-by-Primitive Activation Map

Each primitive must be activated in the scenario. Here is how:

| Primitive | How it is activated | What governance record it produces |
|---|---|---|
| **State** | All admission, signal, and lifecycle transitions write state | SubstrateSignal stream; drain() produces full event log |
| **Memory** | GovernedResearchLog reads admitted items via list_admitted() | AdmissionRecord per item |
| **Ontology** | Categories added at runtime via add_category() before admission | OntologyRecord per mutation; "conclusion" marked singular |
| **Governance** | AdmissionGateway enforces rules on every propose() call | Admission verdict per item |
| **Temporal** | Hypotheses admitted with expiry; expire_before() called | TemporalRecord per item; TEMPORAL_ALERT on expiry |
| **Epistemic** | Evidence items admitted with confidence scores | EpistemicRecord per item; EPISTEMIC_ALERT if fragile |
| **Coordination** | A batch of evidence items proposed simultaneously | CoordinationRecord on conflict; COORDINATION_CONFLICT signal |
| **Observation** | A category defined but never populated triggers a gap | GapRecord; OBSERVATION_GAP signal |
| **Repair** | Two conclusions conflict; repair lifecycle runs to VERIFIED | RepairRecord PENDING→ACKNOWLEDGED→EXECUTED→VERIFIED |

---

## §5 The Scenario (step by step)

### Phase A — Ontology Setup
1. Add category "hypothesis" (plural, no expiry governance)
2. Add category "evidence" (plural, confidence-tracked)
3. Add category "conclusion" (singular — only one conclusion permitted at a time)
4. Add category "methodology" (plural — intentionally left empty to trigger Observation gap)

At end of Phase A: 4 OntologyRecords in ontology_log. "conclusion" is singular.

### Phase B — Temporal: Hypotheses with expiry
5. Admit hypothesis H1: "The substrate generalises across consumer types" — expires in 1 second
6. Admit hypothesis H2: "Governance adds latency overhead" — expires in 1 hour
7. Call expire_before(now) to trigger expiry
8. TEMPORAL_ALERT fires for H1. H2 survives.

At end of Phase B: 2 AdmissionRecords (hypothesis). 1 TemporalRecord. 1 TEMPORAL_ALERT.

### Phase C — Epistemic: Evidence with confidence
9. Admit evidence E1: "Kill Test 11 shows 5/5 governance events caught" — confidence 0.95
10. Admit evidence E2: "External reproduction packet: 5/5 AI systems passed" — confidence 0.92
11. Admit evidence E3: "Single integration scenario not yet tested" — confidence 0.40 (fragile)
12. EPISTEMIC_ALERT fires for E3 (below fragility threshold).

At end of Phase C: 3 AdmissionRecords (evidence). 1 EpistemicRecord (fragile). 1 EPISTEMIC_ALERT.

### Phase D — Coordination: Batch conflict
13. propose_batch([E4: "Temporal primitive adds <1ms overhead",
                   E5: "Temporal primitive adds <1ms overhead"]) — identical content, same category
14. COORDINATION_CONFLICT fires (duplicate in batch).
15. First item admitted; second quarantined within the batch.

At end of Phase D: 1 CoordinationRecord. 1 COORDINATION_CONFLICT signal.

### Phase E — Observation: Gap detection
16. Call observe_gaps() — "methodology" category has zero admitted items.
17. OBSERVATION_GAP fires.

At end of Phase E: 1 GapRecord. 1 OBSERVATION_GAP signal.

### Phase F — Contradiction + Repair: Singular category conflict
18. Admit conclusion C1: "RITAM substrate is generalisable" — ADMITTED (first in singular category)
19. Admit conclusion C2: "RITAM substrate requires further transfer validation" — QUARANTINED
    (conflicts with C1 in singular "conclusion" category)
20. RepairRecord created: status=PENDING
21. acknowledge_repair(repair_id) — PENDING → ACKNOWLEDGED
22. execute_repair(repair_id, pathway_chosen="RETRACT_AND_REPLACE",
    notes="C1 retracted; C2 is more epistemically precise") — ACKNOWLEDGED → EXECUTED
23. verify_repair(repair_id,
    outcome="C2 is now the sole conclusion. Audit chain complete.") — EXECUTED → VERIFIED

At end of Phase F: 1 RepairRecord (VERIFIED). 3 REPAIR_LIFECYCLE signals.

---

## §6 The Audit Check (what the test verifies)

After the full scenario runs, the test asserts:

```
ONTOLOGY:     4 OntologyRecords exist (hypothesis, evidence, conclusion, methodology)
TEMPORAL:     1 TemporalRecord exists; TEMPORAL_ALERT fired
EPISTEMIC:    1 EpistemicRecord (fragile) exists; EPISTEMIC_ALERT fired
COORDINATION: 1 CoordinationRecord exists; COORDINATION_CONFLICT fired
OBSERVATION:  1 GapRecord exists; OBSERVATION_GAP fired
REPAIR:       1 RepairRecord with status=verified exists
SIGNALS:      drain() produces signals from all 6 signal-emitting primitives
ADMISSION:    list_admitted() returns only ADMITTED items (no quarantined items)
```

Every assertion must pass. If any fails, a primitive either wasn't activated or its
governance record wasn't persisted — and the integration test has found a real gap.

---

## §7 What This Proves (and What It Does Not)

**Proves:**
- All nine primitives are load-bearing in a single coherent scenario
- The substrate produces a complete, auditable governance record across all primitives
- A consumer can be built on top of the substrate that exercises the full capability
- Phase 4's component-level proofs compose into system-level governance

**Does not prove:**
- Performance at scale (this is a correctness test, not a load test)
- That every possible interaction between primitives is safe (that is Phase 5B — adversarial)
- That the substrate is complete as a specification (that is Phase 5C — spec writing)

---

## §8 Implementation Plan

1. Single file: `runtime/v0.1/tests/test_integration_s109.py`
2. Single consumer class: `GovernedResearchLog` — thin wrapper around `Substrate`
3. Single test function: `test_full_governance_scenario()` — runs all six phases in order
4. Audit assertions at the end of each phase + a final full-audit assertion block
5. No new primitives, no new dataclasses — this test uses only what already exists

Estimated test count: 1 integration test + 6 phase-level assertion blocks = effectively
testing ~30 governance conditions in a single coherent scenario.

---

## §9 Relation to NORTH_STAR

NORTH_STAR §3: "another system can be built on top of it"
→ GovernedResearchLog is that system. It is built on top. It works.

NORTH_STAR §3: "proves a stated capability, not merely that it executes"
→ The capability stated: nine governed primitives operating coherently.
→ The proof: audit check passes across all nine.

NORTH_STAR §4: "code that runs but demonstrates no governed-cognition capability"
→ This test is the explicit guard against that failure mode.

---

*Authored Session 109 — awaiting Rishi sign-off before implementation.*
