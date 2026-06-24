# ADR-014 — Governance System: North Star + Anti-Drift Mechanisms + Audit Cadence

**Status:** Accepted — Session 076 (2026-06-15). Constitutional.
**Context:** Sessions ~28–73 drifted from the founding mission (*build a governed cognition substrate*) into a law-hunt that the Session-074 prior-art check found was largely known theory (META-027). The root cause was a **hierarchy failure**: the repository preserved every fact but stopped enforcing *mission primacy*. The founding documents had even named the danger — *"abstraction inflation disconnected from executable reality"* — and contained the cure (the Prototype Translation Layer), which was abandoned. This ADR installs the permanent mechanisms that make that drift structurally hard to repeat.

## Decision

**1. Constitutional documents (highest authority).**
- `/NORTH_STAR.md` — what RITAM is, why, what counts/does-not-count as success, mission-critical vs subordinate.
- `/SUBSTRATE_DEFINITION.md` — operational definition of a Governed Cognition Substrate (Constitutional Question 001).
These override all other documents (spec, papers, insights, ADRs). They change only by a dated ADR.

**2. Anti-drift mechanisms (installed in the session protocol).**
- **Mission Alignment Gate** — every session, and every new experiment/stage, answers in writing: *"How does this move RITAM toward the executable governed-cognition substrate, and what is its executable form?"* No clear answer → pause.
- **Executable-Form Rule** — no concept is "done" until it maps to observable runtime behaviour; research artifacts are tagged *"supporting evidence — not substrate."* (Re-instates the founders' Prototype Translation Layer.)
- **Drift Alarm** — each session is tagged in `continuity/SESSION_LEDGER.md` as **BUILD / ANCHORED-RESEARCH / GOVERNANCE / TANGENT**. Once the build phase (Phase 2) begins, **4 consecutive sessions with no BUILD progress** force a mandatory re-anchoring session. (During Phase 0–1 reconstitution, GOVERNANCE sessions are on-mission and expected.)
- **Capability-before-code rule** — no runtime work begins without a one-line Capability Statement naming the observable capability v0.1 will gain.

**3. Audit cadence (four audits; tiered, lean; full design in `mission/AUDIT_AND_CADENCE_SYSTEM.md`).**
- **Housekeeping** (~5 sessions) — clean/current/loose-ends/budgets; archive never delete.
- **Health & Efficiency** (~8–10) — no bloat/redundancy, logical, lean *but* complete; + ≥1 efficiency proposal each time.
- **Alignment** (~8–10 + on demand) — three axes: work↔mission, Claude↔Rishi, Rishi↔mission (evolution ratified by ADR, drift corrected).
- **Opportunity** (~15–20 / phase boundaries) — controlled open-mindedness; candidates parked in the opportunity register, none pursued without a deliberate decision (or North Star amendment).
- **Adversarial Self-Audit** retained, runs with each Health/Alignment cycle.
All audits append to `continuity/AUDIT_LOG.md`. The audit system is itself subject to the Health Audit (anti-bloat).

**4. Supersedes:** the previous periodic maintenance cadences block (Housekeeping/Research Audit/Adversarial/Health-Check) is replaced by this system. File-size budgets are retained under Housekeeping.

## Consequences
- Mission primacy is enforced every session, not just preserved in documents.
- Exploration remains possible but becomes a *governed* act (Opportunity Register + deliberate decision), not accidental drift.
- The constitutional hierarchy (Mission → Architecture → Runtime → Research) is now both physical (repo layout, Session 076 reorg) and procedural (this ADR).

## Alternatives considered
- *Rely on documentation alone* — rejected; that is exactly what failed (preservation ≠ direction).
- *A single rule (just a mission statement)* — rejected; insufficient. Drift needs a per-session gate + a mechanical alarm + structural hierarchy, not one statement.

*Relates to: NORTH_STAR, SUBSTRATE_DEFINITION, mission/FORWARD_STRATEGY.md, mission/AUDIT_AND_CADENCE_SYSTEM.md, mission/REANCHORING_AGENDA.md, META-027, ADR-013.*

---

## Amendment 1 — Ongoing Prior-Art and Adversarial Checks (Session 080, 2026-06-18)

**Trigger:** Session 080 pre-work discussion. Rishi named the Session 074 prior-art discovery (META-027) as a structural failure: the project ran for ~45 sessions before checking whether the core finding already existed in the literature (it did — Quickest Change Detection theory). The lesson generalised: prior-art checks and adversarial questioning were treated as periodic audit activities, which made them easy to defer. They need to be lightweight and ongoing.

**Amendment to the research protocol (supplements §3 above; does not replace the audit cadence):**

1. **Prior-art check trigger:** whenever a finding, proposition, or mechanism is described using language suggesting novelty — "law", "principle", "we have discovered", "this is the first" — pause and run a brief prior-art check before continuing. This is a 15-minute search, not a literature review. It can be deferred by one session if it would interrupt a build task, but must happen before the finding is formalised in the INSIGHT register.

2. **Adversarial question at finding creation:** every new INSIGHT entry must include a one-line adversarial challenge written at the time of entry: *"What would make this wrong?"* This is not a separate audit task — it is part of the finding record. If the answer is not known, write "unknown — adversarial test pending" and add an EQ.

3. **Session hygiene (not a gate):** at the start of any session that touches a finding or adds to the INSIGHT register, spend two minutes asking: *"Has anything in this session's reading (prior art, EQ answers, contradictions) undermined an existing INSIGHT?"* If yes, update the INSIGHT; if uncertain, log an EQ.

**Rationale:** The audit cadence catches drift at the programme level. These three rules catch it at the finding level — earlier, cheaper, and without requiring a dedicated audit session.

**What this does NOT change:** the audit cadence, the Drift Alarm, the Mission Alignment Gate, and the constitutional hierarchy remain unchanged.

*Session 080. Amendment author: Claude (Rishi's explicit instruction).*
