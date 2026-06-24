# RITAM-REFERENCE.md

> Architecture reference document. Contains: project definition, 9 primitives,
> invariants, standing principles, key decisions, known risks, and ideas log.

---

## WHAT RITAM IS

**One sentence:** Ritam is a long-horizon governed cognition substrate research initiative building the foundational primitives for stable, coherent, governable synthetic cognition.

**What it is not:**
- Not a product or assistant
- Not an orchestration framework
- Not Niyom (see ADR-001)
- Not an AGI project
- Not a startup

**Core thesis:** The future bottleneck in AI is not intelligence generation — it is governed cognition continuity. Persistence, memory governance, epistemic stability, contradiction handling, and ontology drift prevention may matter more than raw model capability.

**Research question:** Can governed cognition become stable infrastructure?

---

## ALIGNMENT SESSION CADENCE

Every 5 sessions, run a structured alignment check before beginning new experimental work. This is not optional.

**Alignment session covers:**
1. Direction — are experiments answering questions that matter for the stated research goals?
2. Accuracy — are all documented findings still supported by the evidence?
3. Organisation — is the repo clean, navigable, free of duplication and bloat?
4. Logical coherence — are insights, decisions, and open questions internally consistent?
5. Course correction — if evidence suggests a change of direction, discuss and decide explicitly.

**Schedule:**

| Session | Type | Status |
|---|---|---|
| 005 | External synthesis (Genesys) | ✅ Done |
| 010 | Stage 3 begins | ✅ Done |
| 015 | **ALIGNMENT SESSION** | ✅ Done |
| 020 | **ALIGNMENT SESSION** | ✅ Done |
| 025 | **ALIGNMENT SESSION** | ✅ Done |
| 030 | **ALIGNMENT SESSION** | ✅ Done |
| 039 | **AUDIT SESSION** | ✅ Done |
| ~048 | Next alignment/audit | Scheduled |

---

## BUILD STAGES

*Macro stage sequence from `architecture/design-notes/RITAM_EXECUTION_ROADMAP_v1.md`. Stages are architectural phases; prototypes are implementation units within stages.*

| Stage | Name | Status | Sessions |
|---|---|---|---|
| 0 | Foundational Architecture | ✅ COMPLETE | 001 |
| 1 | Primitive Formalization | ✅ COMPLETE | 002–006 |
| 2 | Bounded Executable Primitive Probes | ✅ COMPLETE | 007–009 |
| 3 | Primitive Interaction Physiology | ✅ COMPLETE | 010–014 |
| 4 | Governed Continuity Systems | ✅ COMPLETE | 016–018 |
| 5 | Governance Net Benefit Measurement | ✅ COMPLETE | 019–023 |
| 6 | MetaGovernance + Adversarial Validation | ✅ ACTIVE EXIT | 024–040 |
| 7 | Distribution Channel (cross-cutting) | ⚡ ACTIVE | 041+ |

**Prototype Sequence** (implementation units within stages):

| Prototype | Name | Stage | Status |
|---|---|---|---|
| 1 | Governed Memory Object | Stage 1 | ✅ COMPLETE |
| 2 | State Transition Simulator | Stage 1 | ✅ COMPLETE |
| 3 | Contradiction Persistence Engine | Stage 2 | ✅ COMPLETE |
| 4 | Memory Decay & Compression Simulator | Stage 2 | ✅ COMPLETE |
| 5 | Ontology Mutation Sandbox | Stage 2 | ✅ COMPLETE |

---

## THE 9 PRIMITIVES

| Primitive | Purpose | Implementation Status |
|---|---|---|
| State Engine | Persistent cognitive continuity and active system state | ✅ v1.1.1 runtime (AdmissionGateway + substrate state) |
| Memory Engine | Governed persistence, forgetting, weighting, compression | ✅ v1.1.1 runtime (memory store, decay, compression) |
| Ontology Engine | Structured world representations and conceptual abstraction | ✅ v1.1.1 runtime (add_category, remove_category, S107) |
| Governance Engine | Validation, constraints, escalation, trust | ✅ v1.1.1 runtime (AdmissionGateway, GovernanceMonitor, Gateway) |
| Epistemic Engine | Truth maintenance, contradiction detection, uncertainty | ✅ v1.1.1 runtime (confidence tagging, EPISTEMIC_ALERT, S104) |
| Coordination Engine | Distributed cognition coordination and role structures | ✅ v1.1.1 runtime (propose_batch, COORDINATION_CONFLICT, S106) |
| Temporal Engine | Long-horizon cognition cycles, reflection, repair timing | ✅ v1.1.1 runtime (age_of, check_expired, TEMPORAL_ALERT, S103) |
| Observation Engine | Introspection, diagnostics, cognition telemetry | ✅ v1.1.1 runtime (GapRecord, ObservationLog, list_gaps, S105) |
| Repair Engine | Contradiction recovery, coherence restoration | ✅ v1.1.1 runtime (RepairRecord, full lifecycle, REPAIR_LIFECYCLE, S108) |

*All 9 primitives complete as of S108. Integration test (S109): all 9 load-bearing in single scenario. Adversarial audit (S110-S111): 4 CORRECT, 1 ACCEPTABLE, GAP-6 found and remediated. 146/146 tests. Updated S112 housekeeping.*

---

## CORE IMMUTABLE INVARIANTS

*Constitutional-level constraints. Violation should be treated as architectural drift unless explicitly revised through governance.*

| ID | Invariant | Statement |
|---|---|---|
| I1 | Governance Before Autonomy | Ungoverned autonomy is considered structurally unstable |
| I2 | Recoverability Over Perfection | Systems must remain repairable rather than optimized for impossible failure elimination |
| I3 | Explicit State Over Implicit Reconstruction | Critical cognition state must not depend on hidden reconstruction from probabilistic context alone |
| I4 | Validation Is First-Class Architecture | Generation without validation is considered incomplete cognition |
| I5 | Observable Repair Loops | Failures must be visible, traceable, diagnosable, and recoverable |
| I6 | Distributed Cognition Model | Cognition is treated as an emergent system property, not solely a property of models |
| I7 | No Hidden Persistence | Persistence mechanisms must remain inspectable and governable |
| I8 | Contradiction Visibility | Contradictions must surface rather than being silently reconciled |
| I9 | Bounded Recursion | Recursive governance and cognition loops must remain computationally governable |
| I10 | Architectural Honesty | Uncertainty, unresolved tensions, and limitations must remain explicit |
| I11 | Estimation Precedes Governance | Every governing primitive must have an explicit, validatable, refreshable estimation mechanism — governance without estimation is structurally incomplete (ADR-006, derived from INSIGHT-073/085, Session 034) |

---

## STANDING PRINCIPLES

| ID | Principle | Established |
|---|---|---|
| SP-001 | Governance-first: embed governance before capability, not after | Session 001 |
| SP-002 | Observability-first: opaque cognition creates hidden instability | Session 001 |
| SP-003 | Prototype-before-scale: validate architecture assumptions in bounded experiments | Session 001 |
| SP-004 | Reversible: all persistence must remain challengeable and repairable | Session 001 |
| SP-005 | Anti-dogmatic: no architecture assumption is permanently unquestionable | Session 001 |
| SP-006 | Bounded: no prototype should self-expand or integrate the full substrate | Session 001 |
| SP-007 | Append continuity: never rewrite history, only add to it | Session 001 |
| SP-008 | Failure is data: prototype failures are architectural findings, not mistakes | Session 001 |
| SP-009 | Artificial coherence is worse than visible instability | Session 001 |
| SP-010 | Forgetting is a stabilisation mechanism, not data loss | Session 001 |
| SP-011 | Ritam ≠ Niyom: these projects must remain architecturally separate | Session 001 |
| SP-012 | Encode knowledge in the repo, not in chats | Session 001 |

---

## KEY DECISIONS

| ID | Decision | Rationale | Session |
|---|---|---|---|
| D-001 | Ritam formally separated from Niyom | Prevent architectural and conceptual drift | 001 |
| D-002 | Governance prioritised before autonomy | Retrofitted governance is never as effective; governance is scientific infrastructure | 001 |
| D-003 | Persistence/memory before agent systems | Coordination without stable persistence fails for hidden reasons | 001 |
| D-004 | Prototype-first experimental philosophy | Architecture assumptions require bounded validation | 001 |
| D-005 | Observability-first philosophy | Opaque systems create hidden instability | 001 |
| D-006 | Python + stdlib only for Prototype 1 | Simplest implementation that exercises governance mechanics; JSON for human-readable state | 001 |
| D-007 | Markdown-first, append-only repo architecture | Continuity infrastructure for the project itself | 001 |
| D-008 | Contradiction Log as first-class document | A substrate claiming to handle contradiction should handle its own | 001 |

---

## KNOWN RISKS

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| R-001 | Governance theater — elaborate governance structures that don't actually constrain anything | High | Operational success/failure criteria in every spec; governance checkpoints must be testable |
| R-002 | Vocabulary drift — key terms used loosely across documents | Medium | Glossary with operational definitions; reviewed after each prototype |
| R-003 | Premature integration — combining primitives before individual behaviour is understood | High | Strict prototype sequencing (ADR-003); no multi-primitive experiments until individual primitives stable |
| R-004 | Artificial coherence — suppressing contradictions instead of resolving them | High | Contradiction Log maintained actively; zero-contradiction state treated as suspicious |
| R-005 | Ritam/Niyom drift — conceptual contamination between projects | Medium | ADR-001 enforced; every Ritam session starts with Ritam ≠ Niyom reminder |
| R-006 | Architecture without validation — continued document production without empirical grounding | High | Prototype 1 is the corrective; document production pauses until Prototype 1 runs |
| R-007 | Memory authority drift — repeated retrieval silently increasing artifact confidence | Medium | EQ-004; explicit anti-drift rule in Prototype 1 retrieval design |
| R-008 | Governance ossification — governance becoming rigid enough to suppress adaptation | Medium | Anti-dogmatic principle (SP-005); governance rules reviewed at each prototype transition |
| R-009 | Recursive overhead explosion — recursive validation/governance becoming computationally intractable | Medium | Bounded recursion invariant (I9); EQ-010; depth limits required in governance loops |
| R-010 | Identity instability — persistent cognition systems developing unstable continuity semantics across rollback | Medium | EQ-009; explicit identity/lineage model required before repair mechanics are built |
| R-011 | Centralised truth fragility — over-centralised canonical state becoming a brittle single point of failure | Medium | Distributed cognition invariant (I6); no single-source truth enforcement before primitive interaction stage |

---

## IDEAS BACKLOG

| ID | Idea | Added | Why | When |
|---|---|---|---|---|
| IDEA-001 | Coherence metric definition session — before EQ-005 experiment | Session 001 | EQ-005 requires a defined coherence metric | Before Prototype 1 experiments |
| IDEA-002 | Session-level telemetry comparison dashboard — HTML file comparing two experiment runs | Session 001 | Would make experiment results directly comparable | After Prototype 1 first run |
| IDEA-003 | Cross-reference Ritam primitive architecture with Niyom's PLAN→EXECUTE→VERIFY→REPAIR stages | Session 001 | Niyom's architecture likely maps onto specific Ritam primitive interactions | After Prototype 2 |

---

## FAILED IDEAS LOG

| ID | Idea | Rejected | Why |
|---|---|---|---|
| F-001 | Use a vector database for Prototype 1 memory storage | Session 001 | Adds external dependency and obscures the governance mechanics being studied; JSON files satisfy observability requirement |
| F-002 | Build Prototype 1 as a REST API service | Session 001 | Unnecessary complexity; adds network layer before core mechanics are validated; Python class is the right scope |
