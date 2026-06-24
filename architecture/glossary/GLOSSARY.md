# Ritam — Operational Glossary

**Purpose:** Operational definitions of key terms used throughout Ritam. These definitions pin concepts to specific, testable behaviours. Wherever a term is used loosely in architecture documents and could mean more than one thing, this glossary resolves the ambiguity.

**Rules:**
- Definitions must be operational — they describe behaviour, not just concepts.
- Definitions must be falsifiable — it should be possible to observe whether the defined behaviour is occurring.
- Definitions evolve as prototypes reveal that initial definitions were wrong. Updates are versioned.
- Where a term is used differently in external literature, that difference is noted.

---

## Core Terms

---

### Cognition

**Definition:** Any process by which the substrate generates, transforms, evaluates, persists, or retrieves representations of the world or the system's own state.

**Operational meaning:** Cognition in Ritam is not limited to inference. It includes memory retrieval, state mutation, contradiction detection, confidence updating, ontology restructuring, and repair. A substrate performing any of these operations is performing cognition.

**What it is not:** Cognition is not synonymous with intelligence, reasoning, or generation. A memory decay operation is cognition. A governance checkpoint is cognition. A contradiction tag is cognition.

---

### Governed Cognition

**Definition:** Cognition that occurs within an explicitly defined constraint space, where every state transition is observable, every persistence decision is validated, and every deviation from defined boundaries is detectable and repairable.

**Operational meaning:** A governed cognition system can answer, for any state it is in: (1) how did it get here, (2) what constraints apply, (3) what would constitute a violation, and (4) what the repair pathway is.

**What it is not:** Governance does not mean the system cannot change state. It means state changes are visible and bounded.

---

### Substrate

**Definition:** The foundational layer of shared cognitive primitives from which more specialised cognition systems can emerge.

**Operational meaning:** The substrate is not an application or a product. It is infrastructure. It provides the governed primitives that future systems compose. A system built on the substrate inherits its governance constraints, observability, and persistence mechanics.

**What it is not:** The substrate is not the nine primitives themselves — it is the governed interaction between them.

---

### Primitive

**Definition:** A minimal, composable cognitive component with defined responsibilities, explicit boundaries, documented failure modes, and a governance interface.

**Operational meaning:** A primitive is primitive in the computer science sense — it cannot be further decomposed without losing its essential identity. The Memory Engine is a primitive. "Memory" is not.

**What it is not:** A primitive is not a class, a module, or a microservice (though it may eventually be implemented as one). It is an architectural unit defined by its responsibilities and failure modes.

---

### Persistence

**Definition:** The governed transition of a cognition artifact from active/transient state into stored state that can influence future cognition.

**Operational meaning:** Persistence is not equivalent to saving. A persistence event in Ritam requires: (1) a governance evaluation of whether the artifact should persist, (2) a weighting decision, (3) a lineage record, and (4) an expiry or decay policy. Unweighted, untracked storage is not persistence — it is accumulation.

**What it is not:** Persistence is not permanent. All persisted artifacts have a decay policy, explicit or default.

---

### Forgetting

**Definition:** The governed reduction of a persisted artifact's authority, retrieval weight, or existence over time.

**Operational meaning:** Forgetting is a first-class operation, not the absence of persistence. It can manifest as: (1) decay — gradual reduction of retrieval weight, (2) compression — replacement of detailed event memory with abstracted strategic memory, (3) expiry — removal of an artifact after a defined period or condition, (4) quarantine — isolation of an artifact from retrieval pathways without deletion.

**What it is not:** Forgetting is not failure. Forgetting is a stabilisation mechanism. A system that cannot forget will accumulate context corruption.

---

### Contradiction

**Definition:** A state in which two or more persisted artifacts, epistemic claims, or ontology structures are mutually incompatible under the substrate's current truth maintenance rules.

**Operational meaning:** Contradictions are not errors to be silently resolved. They are signals that require: (1) tagging and visibility, (2) confidence recalibration of involved artifacts, (3) possible escalation to governance, and (4) repair or explicit deferral. A substrate that hides contradictions is producing artificial coherence.

**What it is not:** A contradiction is not the same as uncertainty. Uncertainty is a property of a single claim. A contradiction is a relationship between claims.

---

### Epistemic Confidence

**Definition:** A scalar property of a persisted artifact representing the substrate's current assessment of the artifact's reliability as a basis for future cognition.

**Operational meaning:** Confidence is distinct from: (1) recency — a recent artifact is not automatically high-confidence, (2) persistence duration — a long-persisted artifact is not automatically high-confidence, (3) retrieval frequency — frequently retrieved artifacts must not automatically gain authority. Confidence is updated by governance evaluation, contradiction density, evidence lineage, and explicit challenge.

**What it is not:** Confidence is not truth. High confidence is a substrate assessment, not a guarantee.

---

### Governance Checkpoint

**Definition:** A defined point in a cognition or persistence workflow at which the Governance Engine evaluates whether the current state transition is admissible.

**Operational meaning:** A governance checkpoint is an explicit gate — the workflow stops, the Governance Engine evaluates, and the workflow either continues, is modified, is escalated, or is halted. Checkpoints must be logged.

**What it is not:** A governance checkpoint is not a logging event or a monitoring hook. It is an intervention point — the workflow cannot bypass it.

---

### Observability

**Definition:** The property of a substrate component by which its internal state, transitions, and reasoning can be inspected without modifying its behaviour.

**Operational meaning:** A component is observable if: (1) its state at any moment can be read without triggering a state change, (2) its transition history is retrievable, and (3) its current constraints and governance status are readable. Observability is an architectural requirement, not a debugging feature.

**What it is not:** Observability is not logging. Logging records what happened. Observability allows inspection of what is happening.

---

### Repair

**Definition:** A governed operation that attempts to restore coherence to a substrate state that has been destabilised by contradiction, corruption, or instability.

**Operational meaning:** Repair operations must: (1) be bounded in scope, (2) not silently suppress contradictions, (3) remain visible through the Observation Engine, (4) be haltable by governance if repair is producing artificial coherence rather than genuine stabilisation.

**What it is not:** Repair is not cleanup. Repair is not the same as deleting contradictory artifacts. Repair that removes the evidence of instability is worse than the original instability.

---

### Ontology Mutation

**Definition:** A governed change to the substrate's structured world representation — the relationships, entities, categories, and abstractions through which memory and cognition are interpreted.

**Operational meaning:** Ontology mutations are high-risk operations. They do not only change the current world model — they recontextualise all existing memory that was stored under the previous ontology. Mutations require governance review proportional to their systemic impact.

**What it is not:** Ontology mutation is not the same as learning a new fact. Learning a new fact updates memory. Ontology mutation changes the structure through which all facts are interpreted.

---

### Artificial Coherence

**Definition:** A substrate state in which apparent stability is produced by suppressing, hiding, or removing contradictions rather than resolving them.

**Operational meaning:** Artificial coherence is the most dangerous failure mode in the substrate — it produces a system that appears stable but is accumulating unresolved tension. Detection requires: (1) contradiction log completeness monitoring, (2) repair scope auditing, (3) governance challenge rate tracking. A substrate with zero contradictions is suspicious, not healthy.

**What it is not:** Artificial coherence is not the same as genuine stability. Genuine stability includes visible contradictions being held and managed.

---

### Lineage

**Definition:** The traceable record of how a persisted artifact came to exist: its source cognition events, transformations, governance evaluations, and confidence history.

**Operational meaning:** Every persisted artifact has a lineage record. The lineage is not optional metadata — it is what allows the substrate to evaluate whether an artifact's persistence authority is justified, and what allows repair operations to work backward from corruption to source.

---

### Challengeability

**Definition:** The property of a persisted artifact or governance rule by which it can be explicitly questioned, re-evaluated, and potentially revised or withdrawn.

**Operational meaning:** A substrate in which some artifacts or rules are permanently unchallengeable is a substrate that has developed institutional rigidity. All artifacts remain challengeable. High-authority artifacts require stronger challenge evidence, but they are not immune.

---

*Glossary version: 1.0 — 2026-05-28*  
*Next review: after Prototype 1 completion — definitions will be revised against empirical observations.*

---

### Detection / Escalation / Intervention / Enforcement

**Definition:** Four distinct stages of governance action, introduced in Session 029 as precise vocabulary for the governance response lifecycle.

**Detection:** The governance layer observes a signal that meets or exceeds a threshold. Detection is passive: no state is changed, no artifact is blocked.

**Escalation:** The governance layer updates its internal classification in response to a detected signal (e.g., regime changes from SLOW to MODERATE). Escalation is representational: it changes what governance believes, not what artifacts are accessible.

**Intervention:** The governance layer changes an artifact's governance status (e.g., CPE marks an artifact as `pending_review` or `quarantined`). Intervention is state-modifying but not necessarily enforcement.

**Enforcement:** The behaviour of a component that consults governance labels and acts on them (e.g., `retrieve()` refusing to return quarantined artifacts). Enforcement is where governance labels become constitutive rather than advisory.

**The critical distinction (INSIGHT-075):** Detection + Escalation + Intervention without Enforcement produce an advisory governance system. Enforcement is what makes governance labels constitutive — it is the difference between a governance label meaning something and merely existing. The SLOW blind spot (INSIGHT-074) is a case where Detection and Escalation work correctly but Enforcement is absent at the retrieval layer.

---

### Advisory vs Constitutive Governance

**Definition:** A distinction between two modes of governance label use.

**Advisory:** A governance label is advisory when the component reading artifacts does not consult it. The label exists (e.g., `governance_status = quarantined`) but retrieval ignores it. The label describes reality without changing behaviour.

**Constitutive:** A governance label is constitutive when access-time components enforce it. `retrieve()` with `governance_filter=True` refuses to return quarantined artifacts — the label is constitutive because it constitutes what is accessible.

**Operational implication:** Prior to OQ-027 resolution (Session 030), governance labels were advisory at the retrieval layer — correctly set by CPE and escalation, but not enforced at retrieval. OQ-027 decision (Option A) makes labels constitutive by default, with `governance_filter=False` preserved as opt-in for diagnostics and research.

---

### Governance Vacuum

**Definition:** The substrate state in which the admitted artifact pool is empty — all artifacts have been removed from admissibility by governance action (quarantine, pending_review) or decay.

**Operational meaning:** A governance vacuum is a legitimate and detectable state, not a silent failure. When `retrieve()` is called with `governance_filter=True` and no admitted artifacts exist, the substrate raises `GovernanceVacuumError` rather than returning empty results without explanation. The substrate is allowed to say "I have no admissible knowledge." Governance vacuum is the operationally-triggered form of Absence Failure — the admitted pool is not merely incomplete, it is exhausted.

**What it is not:** Governance vacuum is not substrate failure. It is a governance-correct state. A substrate that surfaces governance vacuum explicitly is functioning correctly. A substrate that silently returns empty results under quarantine saturation is masking a governance state.

---

*Glossary version: 1.1 — 2026-06-06*
*Session 030 additions: Detection/Escalation/Intervention/Enforcement, Advisory vs Constitutive Governance, Governance Vacuum.*
*Next review: after OQ-027 implementation in Session 031.*

---

### Blindness Classes (Governance Blindness Taxonomy)

**Definition:** A governance blindness is a structural failure mode in which a governance channel produces incorrect CLEAN classifications for adversarial signals, not due to miscalibration, but because a property of the adversary's pattern is unrepresentable at some stage of the channel's information-to-decision pipeline.

Blindness failures are not fixable by tuning. They require architectural change: new observation dimensions, or a different predicate class.

**Four classes (Session 038):**

**Observation Blindness (Class 1):** The adversarial signal is outside the channel's observation scope entirely. Fix: extend acquisition scope. Evidence: EQ-100 (non-cognitive substrate exhibits same constraint — acquisition boundary failure, not cognitive failure).

**Dimensional Blindness (Class 2):** Signal is observed, but only in one dimension. Harm is encoded in a second dimension not measured. Fix: add a measurement channel for the missing dimension. Evidence: EQ-104 (magnitude-only governance; harm is in sequence structure, which the magnitude channel does not measure).

**Relational Blindness (Class 3):** Signal and relevant dimension are observed, but cross-signal relationships are not evaluated. Each signal assessed independently; harm only visible in the relationship between signals. Fix: add cross-signal evaluation (temporal window, sequence predicate). Evidence: INSIGHT-088; EQ-104/EQ-107.

**Representation Blindness (Class 4):** Signal observed, dimension included, cross-signal evaluation present — but predicate language cannot express the specific adversary pattern. Fix: adopt a different predicate class (not more predicates of the same class). Evidence: INSIGHT-095 (EQ-110: Pattern channel cannot encode alternating-value pattern). INSIGHT-096 (EQ-111: all three channels — Pattern, Frequency, Delta — reach Representation Ceiling against distinct-value attack).

**Unifying principle:** A governance channel is blind to adversary pattern P if no predicate in the channel's evaluation language evaluates True for any signal sequence matching P. The four classes differ in WHERE this failure occurs along the information-to-decision pipeline.

**See also:** BLINDNESS_TAXONOMY.md (architecture/glossary/) for full operational definitions, confusion risks, evidence, and open questions.

---

### Representation Ceiling

**Definition:** The system-level Representation Blindness reached when no combination of predicates from the current channel set can detect the adversary's attack pattern, regardless of parameter tuning or number of channels.

**Distinguishing property:** Per-channel Representation Blindness (INSIGHT-095) is about a single channel failing to represent a pattern. Representation Ceiling (INSIGHT-096) is the system-level property: ALL channels fail simultaneously by construction.

**Operational test:** The Representation Ceiling is reached when an adversary can construct an attack satisfying:
- Within magnitude bounds (avoids Observation Blindness)
- No value repetition (avoids Frequency)
- No consecutive identical values (avoids Pattern)
- Small step delta (avoids Delta)
...and still achieves H_adversary = 1.0.

**Architectural implication:** When the Representation Ceiling is reached, the fix cannot be adding more predicates of the same class. A new predicate class is required. In Ritam: Distribution Channel (mean shift, KL divergence) is the next required primitive.

**Evidence:** EQ-111 (Session 038). Distinct-value attack achieves H_adversary = 1.0 against all three temporal channels.

---

*Glossary version: 1.2 — 2026-06-07*
*Session 038 additions: Blindness Classes (full taxonomy), Representation Ceiling.*
*BLINDNESS_TAXONOMY.md created in architecture/glossary/ with full operational definitions.*


---

## Named Clarification: Constituent Component vs. Coordination Topology

**Added:** Session 063, 2026-06-11
**Addresses:** Potential confusion between the Governance Primitive (§2.6 of the Canonical Specification) and the GovernanceMonitor/GovernanceGateway (§3.2–§3.3).

### The Governance Primitive

The **Governance Primitive** is one of the nine substrate building blocks (Chapter 2). It is a *constituent component* — an actor within the substrate responsible for meta-oversight of other governance components. Its domain is the governance pipeline itself: it observes whether other primitives are operating within bounds, detects expired baselines, and triggers recalibration.

The Governance Primitive has a domain, a detection function, a governance function, and must satisfy the minimal estimation interface (I11). It is structurally parallel to the Memory Primitive, the Temporal Primitive, and the others.

### The GovernanceMonitor and GovernanceGateway

The **GovernanceMonitor** and **GovernanceGateway** are *coordination topology components* — architectural patterns that operate *across* substrate primitives. They are not one of the nine primitives. They are cross-cutting overlays:

- GovernanceMonitor: observes and classifies signals passing through governed components (CLEAN/SUSPECT/HARMFUL).
- GovernanceGateway: enforces those classifications at the retrieval boundary.

They emerged from Stage 4 prototyping as the operational implementation of the substrate's cross-primitive governance requirement.

### The Analogy

> The Governance Primitive is to the GovernanceMonitor/Gateway what the **heart** is to the **circulatory system**.
>
> The heart is a constituent component — one organ with a defined function.
> The circulatory system is a coordination topology — it spans all organs and connects them.
>
> Same distinction.

A substrate can have a Governance Primitive (meta-oversight actor) AND a GovernanceMonitor/Gateway (coordination topology) simultaneously. They are not the same thing and do not compete. The Governance Primitive uses the GovernanceMonitor's output as part of its detection function.

### Why This Matters

A reader of the Canonical Specification encountering both Chapter 2 (Nine Primitives) and Chapter 3 (Governance Architecture) could reasonably ask: "Is GovernanceMonitor just the Governance Primitive by another name?" The answer is no. This clarification should be referenced in §2.6 and §3.2 of the spec during the Session 064 coherence pass.

*Glossary version: 1.3 — 2026-06-11*
*Session 063 addition: Constituent Component vs. Coordination Topology named clarification.*
