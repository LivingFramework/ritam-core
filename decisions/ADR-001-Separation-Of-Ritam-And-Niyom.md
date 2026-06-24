# ADR-001 — Separation of Ritam and Niyom

**Status:** Accepted  
**Date:** 2026-05-28  
**Deciders:** Rishi Sood  

---

## Context

Two distinct AI infrastructure initiatives are being developed simultaneously:

1. **Niyom** — a governed execution and runtime orchestration system. Practical, operational, production-oriented. Focused on PLAN → EXECUTE → VERIFY → REPAIR architecture, bounded execution, verification layers, and production cognition workflows.

2. **Ritam** — a foundational cognition substrate research initiative. Focused on cognitive primitives, persistence mechanics, memory governance, epistemics, ontology, contradiction handling, and long-horizon cognition stability.

Both projects share conceptual vocabulary and may eventually share primitives. This overlap creates a real risk of **architectural drift** — decisions in one project gradually absorbing or distorting the other, without the drift being explicitly noticed or recorded.

---

## Decision

Ritam and Niyom are maintained as **permanently separate repositories, architectures, and initiatives**.

This separation is not merely administrative. It is a fundamental design constraint:

- Ritam is **foundational and architectural**. Its purpose is substrate research.
- Niyom is **operational and runtime-oriented**. Its purpose is production execution.

No feature, primitive, or design decision in one project should be justified by its usefulness to the other at the current stage. Future integration is possible but must not drive present architecture.

---

## Consequences

**Positive:**
- Prevents conceptual contamination between substrate research and runtime engineering.
- Allows each project to move at its own pace without mutual dependency.
- Preserves the integrity of Ritam's foundational orientation — it will not be pulled toward productisation prematurely.
- Preserves Niyom's operational focus — it will not be stalled by substrate research timelines.

**Negative / Accepted Costs:**
- Some duplication of concepts across repos in the short term.
- Cannot share code between projects until primitives are explicitly validated and stabilised.
- Requires ongoing discipline to prevent drift in conversations and architecture documents.

---

## Enforcement

- Every Ritam document must treat Niyom as external.
- Every architecture decision in Ritam must be justified on Ritam's own terms, not by Niyom's roadmap.
- When a question arises about whether a feature "could be used by Niyom," the answer is: not relevant to the current decision.
- This ADR should be referenced any time the Niyom/Ritam boundary is questioned.

---

## Future Review

This decision should be revisited only when:
- Ritam has validated at least one primitive through controlled experimentation (Prototype 1+)
- Niyom has reached a stable production architecture
- A specific integration need has been clearly identified and formally scoped

Until those conditions are met, this separation is permanent.

---

*See also: [ADR-002](ADR-002-Governance-Before-Autonomy.md), [ADR-003](ADR-003-State-Memory-Before-Agents.md)*
