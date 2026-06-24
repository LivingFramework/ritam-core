# ADR-019 — Documentation Coherence as Governed Process

**Date:** 2026-06-22 (Session 111)
**Status:** ACCEPTED
**Authority:** Rishi + Muad'Dib, following Mahdi Advisory 008
**Relates to:** ADR-014 (Mission Alignment Gate), ADR-018 (Infrastructure-First Direction)

---

## Context

Historically, RITAM's runtime has evolved faster than its narrative documents. This was observed multiple times across sessions 80–110. As RITAM transitions from construction phase to preservation phase (ADR-018), documentation drift becomes a primary risk rather than a secondary concern.

Mahdi Advisory 008 named this explicitly: "Treat documentation coherence as a governed process." The runtime now depends on the documentation — the accumulated ADR history, primitive rationale, audit findings, and transfer evidence are architectural assets, not notes.

---

## Decision

**No architectural change is considered complete until all four artifacts are updated:**

1. **Runtime** — the code reflects the change
2. **Tests** — the change is covered by new or updated tests
3. **Specification** — the relevant CH or architecture document reflects the change
4. **Historical record** — SESSION-LOG, CHANGELOG, and/or HANDOFF updated

**One artifact missing = change incomplete.**

This rule applies to:
- GAP remediations (e.g., GAP-6)
- New invariants or ADRs
- Primitive interface changes
- Governance model changes
- Any change that affects the external specification

---

## Scope

This rule does NOT apply to:
- Pure research entries (new EQ, new OQ, new INSIGHT) — these are append-only records, not changes to the architecture
- Session-level logging (HANDOFF updates, LEDGER entries) — these are always done at session close regardless
- Housekeeping and file maintenance

---

## Rationale

During construction phase, the bottleneck was implementation — documentation could lag. During preservation phase, the bottleneck is understanding — a future builder who cannot understand the system cannot use it. Documentation debt in the preservation phase is equivalent to a test failure in the construction phase: it means the work is not done.

This also guards against the failure Mahdi named: "a wrong ontology element becomes infrastructure once other systems depend on it." Applied to RITAM: a change without documentation becomes invisible to future builders. Invisible changes accumulate into a system that works but cannot be understood or extended.

---

## Implementation

Starting Session 111, the session close checklist already includes specification and historical record updates. ADR-019 formalises this as a constitutional rule rather than a best practice.

The four-artifact check becomes part of every future code review and every session close verification.

---

## Consequences

- GAP-6 remediation this session must produce: runtime fix + new tests + INSIGHT/ADR update + SESSION-LOG entry
- CH1–CH9 spec writing (Phase 2) must stay in sync with the runtime as chapters are written
- Any future primitive interface change requires a spec chapter update before the change is considered merged
