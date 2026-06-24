# RITAM v1.0 Declaration

**Date:** 2026-06-21
**Session:** 097
**Authority:** ADR-016 completion condition (signed Session 093 by Rishi + Claude + ChatGPT/Mahdi Advisory 003)
**Status:** DECLARED

---

## What v1.0 Is

RITAM v1.0 is a governed-cognition substrate prototype.

It is a functioning runtime system that enforces epistemic governance across AI-adjacent applications — rejecting claims that violate declared constraints, detecting and structuring contradictions, supporting repair, and doing this portably across independently built consumer applications.

v1.0 does not claim to solve governed cognition. It claims to demonstrate that a substrate-level governance layer can exist, operate, and be reproduced by a builder who was not involved in its construction. That is what was set out to prove. That is what was proved.

---

## ADR-016 Completion Scorecard

ADR-016 defined three criteria for v1.0. All three are met.

| Criterion | Description | Status | Session | Evidence |
|-----------|-------------|--------|---------|----------|
| **C1 — Outcome** | Governance must measurably improve outcomes vs a baseline that lacks governance | ✅ COMPLETE | 095 | `runtime/v0.1/tests/test_outcome_s095.py` — 0 governed violations vs 4 baseline on adversarial stream (structural guarantee, not probabilistic) |
| **C2 — Repair** | Every quarantined event must produce a structured repair suggestion; the repair loop must be closeable | ✅ COMPLETE | 094 | `runtime/v0.1/tests/test_repair_s094.py` — 6 tests; I5 (Observable Repair Loops) operational; `get_repair()` + `mark_resolved()` |
| **C3 — Buildability** | A new governed consumer must be constructable from a self-contained spec packet by a cold builder | ✅ COMPLETE | 096 | `runtime/v0.1/tests/test_buildability_s096.py` — 5/5 criteria pass; GovernedDecisionLog built cold from BUILDABILITY_PACKET.md; 5 spec gaps found and recorded |

**Total tests passing at v1.0 declaration:** 22/22

---

## What v1.0 Proves

**1. Governance can exist as a substrate layer.**
The runtime is not a governance feature inside an application. It is a governance layer beneath applications. AdmissionGateway, ContradictionStore, and ObservationChannel are shared infrastructure. Consumer applications (GovernedNotebook, GovernedAgentMemory, GovernedTaskPlanner, GovernedDecisionLog) sit above the layer and interact with it through a public API. This is what "substrate" means operationally.

**2. Governance discriminates contradictions.**
Singular-category constraints enforce at-most-one membership. Plural-category constraints allow coexistence. The boundary between the two is explicit and configurable per consumer. A second admission attempt in a singular category triggers QUARANTINE with both sides of the conflict named, the violated rule recorded, and three resolution pathways generated.

**3. Governance produces structured repair.**
Every quarantined event produces a `RepairSuggestion` containing: both conflicting sides, the rule triggered, and three ordered pathways (RETRACT_EXISTING, KEEP_EXISTING, HOLD_AS_CONTRADICTION). `mark_resolved()` closes the repair loop while preserving the original contradiction record. Invariant I5 (Observable Repair Loops) is operational.

**4. Governance changes outcomes.**
Under adversarial input (conflicting goals + conflicting tasks + plural items), a governed consumer produces zero constraint violations. An equivalent baseline without governance produces four violations on the same input. This is a structural guarantee — not statistical — because singular-category admission is enforced at the gateway, not checked after the fact.

**5. Governance is reusable across multiple consumers.**
Four consumer applications built by the same team on the same substrate across four sessions, each with distinct semantic domains: notebook entries (GovernedNotebook), agent memory objects (GovernedAgentMemory), task/goal planning (GovernedTaskPlanner), decision records (GovernedDecisionLog).

**6. Governance can be reproduced from a specification.**
A cold build from BUILDABILITY_PACKET.md produced a working governed consumer (GovernedDecisionLog) with 5/5 buildability criteria passing. The builder (Claude in a fresh session with no RITAM context) identified 5 specification gaps during construction. The gaps are evidence, not failure — they are the first output of cold-build auditing.

---

## What v1.0 Does Not Prove

These are standing limitations, not future work items to dismiss. They are the honest boundary of the v1.0 claim.

**1. Real-world governance.**
All consumers were built in clean-room conditions: categories assigned by the researcher, contradictions injected by the test, consequences limited to test assertions. The substrate has not yet operated on ambiguous input, imperfect category assignment, or real user behaviour.

**2. External-builder portability.**
All four consumers were built by the same team. "Reusability across same-team consumers" has been demonstrated. "Portability to an external builder who was not involved in substrate design" has not. The cold-build test (C3) approximates this but used the same underlying researcher.

**3. Substrate-generality.**
All four consumers share text + categories + SQLite + single process. Governance portability across same-stack consumers has been demonstrated. Portability to a materially different architectural substrate (event-driven, graph-based, multi-agent, distributed) has not.

**4. Governance of semantic structure.**
Category boundaries are currently supplied by the researcher before admission. The substrate enforces governance on pre-categorised content. It does not yet govern the categorisation process itself. The question "can semantic structure itself become governed?" is open.

**5. Long-term contradiction accumulation.**
Tests create and resolve contradictions within a single session. Governance operating on contradictions that emerge organically across weeks, months, and hundreds of decisions has not been tested.

---

## Five Known Specification Gaps (from C3 Cold Build)

These gaps were discovered during the C3 buildability audit (Session 096). They are the direct output of cold-build testing. Full remediation plan: ADR-017.

| Gap | Severity | Description |
|-----|----------|-------------|
| **GAP-1** | BREAKING | `singular_categories` in BUILDABILITY_PACKET.md spec vs `plural_categories` in implementation — inverted logic; a cold builder must reverse the spec to use the API correctly |
| **GAP-2** | MEDIUM | `get_repair()` and `mark_resolved()` are not listed in the base ContradictionStore specification; a cold builder must infer their existence from prose description |
| **GAP-3** | HIGH | `plural_categories` default behaviour in SubstrateConfig is undocumented; a cold builder cannot determine what happens if the parameter is omitted |
| **GAP-4** | LOW | `RepairSuggestion` import path is not specified; a cold builder must search for it |
| **GAP-5** | HIGH | No public `list_admitted(category)` or equivalent read API on AdmissionGateway; a cold builder must access internal `_db` directly to read current state |

**GAP-1 is the highest-priority remediation target.** It creates a specification/implementation inversion that will cause every future external builder to fail silently until they discover and reverse the logic. It must be resolved before any external handoff.

---

## Four Consumers at v1.0

| Consumer | Session Built | Domain | Singular Categories | Plural Categories |
|----------|---------------|--------|--------------------|--------------------|
| GovernedNotebook | 080 | Research notes | current-hypothesis | notebook-entry, evidence, contradiction-note |
| GovernedAgentMemory | 088 | Agent memory | current-goal | memory-object, belief, past-goal |
| GovernedTaskPlanner | 091 | Task/goal planning | current-task, current-goal, current-plan | completed-task, archived-goal, archived-plan |
| GovernedDecisionLog | 096 | Decision records | active-decision | decision-rationale, decision-question, superseded-decision |

---

## Test Record at v1.0

| Test File | Session | Coverage | Result |
|-----------|---------|----------|--------|
| test_repair_s094.py | 094 | C2 Repair — 6 tests | 6/6 ✅ |
| test_outcome_s095.py | 095 | C1 Outcome — 6 tests | 6/6 ✅ |
| test_buildability_s096.py | 096 | C3 Buildability — 5 tests | 5/5 ✅ |
| (prior test suite) | 080–093 | Consumer + substrate primitives | 5/5 ✅ |

**22/22 tests passing at declaration date.**

---

## Version History to v1.0

| Version | Session | Milestone |
|---------|---------|-----------|
| v0.1 (prototype start) | 080 | GovernedNotebook — first consumer |
| v0.9.50 | 088 | GovernedAgentMemory — second consumer |
| v0.9.51 | 091 | GovernedTaskPlanner — third consumer; plural/singular architecture complete |
| v0.9.52 | 091 | Gate A signed |
| v0.9.53 | 092 | Gate B passed (Advisory 004 multi-AI peer review) |
| v0.9.54 | 093 | ADR-016 signed — v1.0 completion condition formalised |
| v0.9.55 | 094 | C2 Repair complete |
| v0.9.56 | 095 | C1 Outcome complete; ADR-012 Amendment 1 |
| v0.9.57 | 096 | C3 Buildability complete; GovernedDecisionLog; 5 spec gaps found |
| **v1.0** | **097** | **Declaration** |

---

## What Comes Next

**Immediate (Sessions 098–100):**
- GAP remediation per ADR-017 (resolve all 5 gaps, starting with GAP-1)
- API spec alignment: BUILDABILITY_PACKET.md and API_SPEC must match implementation exactly

**Near-term:**
- Prepare external reproduction package (clean spec + packet + test harness for a builder with no RITAM context)
- Identify first real-world use case (one user, one workflow, one problem)

**Medium-term:**
- Continue implementing remaining primitives as architectural experiments (each one tests whether the primitive requires genuinely new machinery or collapses into existing governance)
- Build second-generation substrate roadmap only after external reproduction is achieved

**What is NOT the next step:**
Beginning v1.1 feature development before v1.0 is stable. The external reproduction test is the gate to the next milestone. Building more consumers before an external builder can reproduce one does not advance the substrate.

---

## Declaration Statement

RITAM v1.0 is hereby declared complete.

The substrate exists. Governance fires. Repair is observable. Outcomes improve under governance. A new consumer can be built from the specification. The gaps in that specification are now documented.

The next frontier is proving that people other than its creators can use it, build upon it, and benefit from it.

— Session 097 · 2026-06-21

---

## Addendum — Session 102 (2026-06-22)

**External-builder portability (v1.0 limitation above) has since been partially validated.**

Five independent AI systems built working implementations from the specification alone, without access to the original source code. 60/60 tests passed across these independent implementations (INSIGHT-073, Tier D: transfer-validated). This addresses the "same team" limitation noted at v1.0 declaration. Human-engineer external build remains open (see Technical Overview Section 4).

Current version: v1.1.1 · 146/146 tests · Session 111.
