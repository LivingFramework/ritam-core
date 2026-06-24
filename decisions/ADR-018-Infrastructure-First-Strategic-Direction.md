# ADR-018 — Infrastructure-First Strategic Direction

**Date:** 2026-06-22 (Session 111)
**Status:** ACCEPTED
**Authority:** Rishi (project owner) + Muad'Dib (Claude) strategic review of Mahdi Advisory 008
**Overrides:** None. Adds strategic direction layer above existing ADRs.

---

## Context

Following completion of Phase 5B (Adversarial Audit, v1.1.0, 139/139 tests), RITAM has crossed a threshold. The central question is no longer "can governed cognition be built?" The question is now: "can it be preserved, transferred, and reconstructed without the original builders present?"

Mahdi Advisory 008 (Post-Phase-5 Strategic Review) recommended fixing RITAM's primary identity as infrastructure. Rishi requested a final, non-wavering decision. Muad'Dib evaluated the advisory as strategist, engineer, builder, and co-architect before accepting with modifications.

---

## Decision

**RITAM's destination is a Governed Cognition Substrate that third-party builders can install and build upon.**

Priority hierarchy (frozen):
1. **Infrastructure** — the substrate other systems stand on (`pip install ritam` or equivalent)
2. **Specification** — canonical documentation that preserves and explains the infrastructure
3. **Validation** — external builders, auditors, reproductions proving it is usable
4. **Papers** — explaining what was built, after it has been built and used

---

## Muad'Dib Modifications to Mahdi's Advisory (agreed by Rishi, Session 111)

These modifications refine but do not contradict Mahdi's direction:

**1. Infrastructure as destination, not current identity.**
Calling RITAM "infrastructure" now would be premature. Infrastructure implies stable APIs, packaging, versioning contracts, and support semantics — none of which exist yet. The current phase is Preservation. RITAM's identity shifts to infrastructure when Phase 3 (Productization) begins. Until then: "we are building toward installable infrastructure."

**2. One public technical report during Phase 2, not Phase 6.**
Mahdi placed papers entirely at Phase 6. However, the external landscape is moving — practitioners are converging on RITAM's thesis independently (INSIGHT-134). A single public technical overview (~15–20 pages) should be written during Phase 2 (Public Canon). This is not a journal paper; it is a citable architectural overview document. It serves external builders AND becomes the first draft of any future paper. This does not accelerate papers at the cost of infrastructure — it runs in parallel with Canon work.

**3. Precise freeze boundary.**
"Freeze feature growth" means: no new primitives, no major architectural branches, no speculative capability additions until documentation catches up. It does NOT mean: stop research. Open questions (OQ-061, OQ-062) remain live. Empirical investigation continues. GAP-6 remediation and spec writing are explicitly allowed.

**4. Acknowledge Ritam-Niyom boundary in the roadmap.**
Mahdi's roadmap does not address the Ritam-Niyom relationship. When RITAM becomes installable infrastructure (Phase 3), the question of how it relates to Niyom becomes unavoidable. This is flagged as a decision required before or during Phase 4 (External Builders). See ADR-001 for the separation principle.

**5. Phase 3 (Productization) is a substantial engineering effort.**
The gap between "research prototype with 139 tests" and "installable infrastructure with stable API, packaging, builder guide, and consumer examples" is significant. Phase 3 is not documentation work. It is a multi-month re-engineering effort requiring API design, dependency cleanup, packaging, versioning contracts, and stability guarantees.

---

## Fixed Roadmap (Sessions 111+)

| Phase | Name | Goal | Done when | Est. sessions |
|---|---|---|---|---|
| 1 | Stabilize | Close GAP-6, freeze runtime v1.1.x, write documentation coherence ADR | Stable substrate, no known gaps | S111 (today) |
| 2 | Public Canon | Technical overview doc + README + v1.1 Declaration + Architecture Spec + Public repo live | Someone understands RITAM without Rishi or Claude | S112–S115 |
| 3 | Productization | Builder Guide, API Reference, Consumer Examples, Installation Package | Developer can install and use RITAM | S116–S130+ |
| 4 | External Builders | Engineers/researchers attempt to build on RITAM independently | Independent consumer built | TBD |
| 5 | Ecosystem | Reference implementations (GovernedAgent, GovernedMemory, GovernedPlanner, GovernedResearch) | Multiple independent consumers | TBD |
| 6 | Papers | Technical papers with evidence — built, validated, adopted, then published | Papers that say "we built it, others used it" | TBD |

**Website** (livingframework.github.io): comes after Public repo is populated. Design and content discussed with Rishi before any changes — current site has a specific look and feel that must be preserved or deliberately evolved.

---

## Three-Layer Public Architecture

```
Private Repository (LivingFramework/ritam — current)
    Purpose: Research Brain
    Contains: all sessions, ADRs, experiments, failures, debates, raw history
    Access: private, permanent

Public Repository (new)
    Purpose: Canonical Technical Source
    Contains: spec, builder guide, validation reports, releases, technical overview
    Access: public

Website (livingframework.github.io)
    Purpose: Orientation Layer
    Contains: what is RITAM, current status, architecture summary, links to repo and docs
    Access: public
    Note: changes require discussion with Rishi — design and feel must be agreed before update
```

This structure maps to RITAM's own primitives:
- Private repo = memory
- Public repo = specification
- Website = observation layer

---

## Consequences

- Phase 1 target: Session 111 (today) — GAP-6 closed, ADR-019 written
- Phase 2 target: Sessions 112–115 — technical overview written, public repo live
- Full CH1–CH9 spec: written progressively into public repo during and after Phase 2
- Research continues throughout: open questions live, empirical investigation continues
- No new primitives or major architectural branches until Phase 3 begins

---

## Dissenting / Cautionary Notes (for the record)

Muad'Dib notes that the infrastructure destination, while correct, carries risk of scope inflation if Phase 3 is underestimated. The project's credibility comes from restraint (INSIGHT-133, Warning 2 from Mahdi). Infrastructure should be built incrementally, not declared prematurely.

Mahdi's warning preserved: "Do not confuse validation with completion. The substrate now works. That does not mean the problem space is solved. It means the first governed-cognition substrate exists. Those are different statements."
