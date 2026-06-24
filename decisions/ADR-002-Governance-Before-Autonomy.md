# ADR-002 — Governance Before Autonomy

**Status:** Accepted  
**Date:** 2026-05-28  
**Deciders:** Rishi Sood  

---

## Context

In designing the Ritam substrate, there is a persistent tension between two impulses:

1. **Governance-first**: build validation, constraint enforcement, and observability into every primitive before expanding capability.
2. **Capability-first**: build the thing that does something interesting, then add governance later.

The capability-first impulse is natural. Governance feels like overhead until the system fails in ways that governance would have prevented. The historical pattern in AI systems is: build capability fast, discover governance problems in production, scramble to retrofit constraints that were much cheaper to build in.

The Genesys intelligence programme documents this pattern empirically: 41–87% of production multi-agent system failures are attributable to coordination and governance architecture failures, not model capability failures. The six-stage cascade (Context Drift → Reasoning Drift → Boundary Erosion → Trust Fracture) is a governance failure sequence, not a capability sequence.

---

## Decision

**No substrate primitive will be built or expanded without governance constraints being defined first.**

Specifically:
- Every prototype must define its governance checkpoints before implementation begins.
- Every persistent state transition must be observable and governed before it is functional.
- Autonomy — any behaviour the system performs without explicit external validation — is not introduced until the governance layer for that behaviour is designed, tested, and stable.
- Governance is not a wrapper added after the fact. It is embedded in the primitive's architecture from the first line.

---

## Rationale

The Genesys intelligence synthesis identified a critical empirical finding: **the Capability-Governance Inversion**. More capable models do not automatically require less governance — governance requirements depend on architecture type and are non-monotone with capability. This means: governance cannot be deferred until capability is "good enough." Governance requirements grow in complexity as the system grows.

More importantly for Ritam: the substrate is not a production system with clear failure signals. It is a research system exploring failure modes. An ungoverned research system will produce observations that are artifacts of uncontrolled conditions rather than genuine substrate behaviour. The governance layer is not just safety infrastructure — it is scientific infrastructure.

---

## Consequences

**Positive:**
- Failures are interpretable because they occur within a governed, observable context.
- Governance constraints force explicit architectural decisions that would otherwise be implicit.
- The substrate accumulates governance primitives as a byproduct of building everything else.
- Prevents the "build now, govern later" trap that produces ungovernable systems.

**Negative / Accepted Costs:**
- Slower initial progress — every primitive requires governance design before implementation.
- Some governance constraints will be over-specified early and will require revision.
- Risk of governance becoming bureaucratic overhead if constraints are not kept lean and testable.

---

## Enforcement

- No Prototype spec is approved without a governance checkpoints section.
- No state mutation is implemented without an observable audit trail.
- Any proposal to "add governance later" requires explicit ADR justification.

---

*See also: [ADR-001](ADR-001-Separation-Of-Ritam-And-Niyom.md), [ADR-003](ADR-003-State-Memory-Before-Agents.md)*
