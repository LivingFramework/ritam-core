# ADR-006 — Separation Principle as Architectural Invariant (I11)

**Status:** Accepted  
**Date:** 2026-06-06  
**Session:** 034  
**Deciders:** Rishi Sood, Claude  
**Trigger:** INSIGHT-085 (EQ-102 vocabulary translation finding) — INSIGHT-073 identified as instance of separation principle from optimal control theory (Kalman 1960, Wonham 1968).

---

## Context

EQ-102 (Level 2 Transferability, Session 033) produced an unexpected finding: INSIGHT-073 ("Governance cannot classify correctly using information it has not acquired — including observation timing, baseline accuracy, and baseline freshness") is an instance of the *separation principle* from optimal control theory.

The separation principle (Kalman, 1960; Wonham, 1968) holds that in any optimal controller, estimation and control are architecturally separate concerns. You cannot control what you have not estimated. The principle was formalised for physical control systems receiving sensor readings from a plant. Its structural claim is substrate-independent.

INSIGHT-073 extends the separation principle to governed cognitive architectures, where "observation" is an epistemic act — belief acquisition, context formation, retrieval — rather than a physical sensor reading. RITAM's novel contribution beyond the classical separation principle is the information quality claim: governance is bounded not just by timing, but by the accuracy and freshness of its acquired information, and (per EQ-104) by the dimensional scope of what it measures.

INSIGHT-073 is now Tier C (settled) with T1 through T5 Tier D criteria met. It has survived adversarial validation across EQ-100 through EQ-104 — substrate transfer, vocabulary translation, adversarial calibration, baseline poisoning, and relational harm attacks — without falsification.

The architectural implication stated in INSIGHT-073 is: "Every RITAM primitive that governs must also estimate — i.e., must have a mechanism for acquiring, validating, and refreshing its information about what it governs." This implication is not currently captured by any of the ten existing architectural invariants (I1-I10).

---

## The Question

**Should INSIGHT-085 (separation principle connection) be formalised as a new architectural invariant I11?**

Specifically: should Ritam's constitutional architecture require that every governance primitive has an estimation mechanism, and that governance and estimation are never architecturally conflated?

---

## Existing Invariants — Gap Analysis

| Invariant | What it covers | Gap with this question |
|---|---|---|
| I1 — Governance Before Autonomy | No primitive built without governance constraints first | Does not address how governance itself acquires information |
| I2 — Recoverability Over Perfection | Systems remain repairable | Does not address governance information dependency |
| I3 — Explicit State Over Implicit Reconstruction | Critical state must not depend on hidden reconstruction | Related but addresses outputs of cognition, not inputs to governance |
| I4 — Validation Is First-Class Architecture | Generation without validation is incomplete | Addresses validation of outputs, not acquisition of governance information |
| I5 — Observable Repair Loops | Failures visible, traceable, diagnosable | Addresses failure visibility, not governance architecture |
| I7 — No Hidden Persistence | Persistence mechanisms must be inspectable | Addresses persistence, not observation scope |
| I10 — Architectural Honesty | Uncertainty and limitations must be explicit | Addresses epistemic honesty, not structural design of governance |

None of the ten invariants address the structural design of governance primitives themselves — specifically that a governance system must estimate before it governs. I1 is the closest (governance must precede autonomy) but it is a sequencing rule, not an architectural design rule for the governance mechanism.

---

## Decision

**Accepted: Establish I11 — Estimation Precedes Governance**

**I11 — Estimation Precedes Governance:** Every primitive that governs must have a mechanism for acquiring, validating, and refreshing its information about what it governs. Governance and estimation are architecturally distinct but structurally coupled: no governing primitive is architecturally complete without a co-designed estimation mechanism. A governance system without an estimation mechanism is a classification rule without an information source — it will produce structurally bounded failures under any conditions that push against its information horizon.

---

## Rationale

**1. Theoretical grounding.** The separation principle is one of the most robust results in optimal control theory — independently derived (Kalman 1960, Wonham 1968), verified across decades of control engineering. Formalising this as an invariant anchors Ritam in established theory rather than novel conjecture. INSIGHT-073 provides the extension to cognitive substrates; I11 formalises the architectural consequence.

**2. Empirical validation.** INSIGHT-073, from which I11 is derived, has been validated across seven experiments (EQ-095, EQ-098, EQ-100, EQ-101, EQ-102, EQ-103, EQ-104) spanning substrate transfer, vocabulary translation, and four distinct adversarial attack classes. No experiment has falsified it. The Tier D criteria T1 through T5 are now met. This is the most extensively validated Tier C finding in the Ritam research record — promoting its structural consequence to invariant status is warranted.

**3. Architectural gap.** The existing invariants (I1-I10) do not address how governance primitives acquire information. I11 fills this gap explicitly. Without I11, a future governance primitive could be designed as a pure classification rule without any observation or estimation mechanism — this would be architecturally deficient but not prohibited by the current constitution. I11 closes this gap.

**4. Failure mode specificity.** INSIGHT-073 and its boundary conditions (T5 exhaustion, Session 034) identify specific failure modes that all arise from violation of the separation principle: cold-start harm (estimation not initialised), adversarial calibration (estimation using the wrong information), baseline staleness (estimation not refreshed), and dimensional blindness (estimation with insufficient scope). I11 gives future implementers explicit guidance that prevents these failure modes by design.

**5. Distinct from I1.** I1 (Governance Before Autonomy) governs the sequence: govern first, then allow autonomy. I11 governs the structure: when governing, ensure an estimation mechanism exists. These are complementary, not redundant. A system could satisfy I1 (governance is defined before autonomy is granted) while violating I11 (the governance mechanism has no estimation component — it classifies with no information basis).

---

## Scope and Limitations

**Scope of I11:**
- Applies to every governance primitive in the Ritam substrate architecture
- Applies at design time (estimation mechanism must be co-designed with the governing rule)
- The estimation mechanism must be: (a) explicit — identifiable in the architecture; (b) validatable — its accuracy and freshness can be assessed; (c) refreshable — it can be updated as the governed signal distribution evolves

**What I11 does not require:**
- I11 does not specify the form of the estimation mechanism (Bayesian, statistical, learned — any is valid)
- I11 does not require that the estimation mechanism be perfect or complete — INSIGHT-073 is a structural claim about the consequence of estimation gaps, not a requirement for perfect estimation
- I11 does not prohibit predictive governance (K073-D boundary condition) — predictive governance is an estimation mechanism (prior-based), not an absence of estimation

**Open boundary (K073-D):** The question of whether predictive governance (pre-empting harm before arrival-observation) can bypass the structural constraint of INSIGHT-073 remains unresolved. If K073-D is resolved as a genuine exemption, I11 may require a rider: "observation-based governance" rather than "all governance." This does not affect the acceptance of I11 — the rider, if needed, would be a narrowing, not a reversal.

---

## Consequences

**Positive:**
- Every future governance prototype will explicitly document its estimation mechanism before implementation (parallel to how I1 requires governance constraints before autonomy)
- Architectural review can test: what is this governance primitive's estimation mechanism? How is it initialised? How is it refreshed? What happens if the estimation is stale or wrong?
- Connects Ritam's empirical findings to a well-established theoretical tradition, strengthening the research record
- Prevents a class of architectural deficiencies (governance without estimation) before they appear in implementation

**Negative / Accepted Costs:**
- Adds a design constraint to every future governance primitive — some overhead in early design
- The concept of "estimation mechanism" must be operationalised for each primitive type; this operationalisation may be non-trivial for novel governance forms (e.g., multi-agent governance, predictive governance)
- I11 creates an obligation to revisit existing governance primitives (GovernanceMonitor, GovernanceGateway) and document their estimation mechanisms explicitly — this is a one-time cost

---

## Implementation

**Immediate actions:**
1. Add I11 to the invariant table in the architecture reference documents
2. Add a retrospective note to GovernanceMonitor and GovernanceGateway documentation identifying their estimation mechanisms (GovernanceMonitor uses IQR over a rolling baseline — the estimation mechanism is the baseline construction; GovernanceGateway uses the Monitor's output)
3. Add I11 as a design checkpoint in future prototype specification templates (parallel to the governance checkpoints required by I1/ADR-002)

**Future enforcement:**
- All future prototype specifications must include an "Estimation Mechanism" section documenting: what information the governance rule requires, how that information is acquired and stored, how it is validated, and how it is refreshed

---

## References

- INSIGHT-073 — Governance law is workload-pattern-invariant (T5 exhaustion complete, Session 034)
- INSIGHT-085 — INSIGHT-073 as instance of separation principle (EQ-102, Session 033)
- INSIGHT-086/087/088/089 — Boundary conditions: structural blindness, baseline poisoning, relational blindness, perfect signal paradox (EQ-103/104, Session 033)
- D-018 — Adversarial Validation Programme (ADVERSARIAL_VALIDATION_PROGRAM.md)
- ADR-002 — Governance Before Autonomy (I1 — the sequencing companion to I11)
- Kalman, R.E. (1960). "A new approach to linear filtering and prediction problems." Transactions of the ASME — Journal of Basic Engineering, 82(1), 35-45.
- Wonham, W.M. (1968). "On the separation theorem of stochastic control." SIAM Journal on Control, 6(2), 312-326.
