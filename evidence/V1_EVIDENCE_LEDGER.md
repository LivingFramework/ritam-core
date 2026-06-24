# RITAM v1.0 Evidence Ledger

**Created:** 2026-06-21, Session 097
**Purpose:** Permanent historical anchor for the v1.0 declaration. Six months from now — or six years — this document answers the question: "Why was v1.0 declared, and what exactly was the evidence?"
**Recommended by:** Mahdi (ChatGPT) Advisory 005: "Because six months from now nobody — including Claude — will perfectly remember why v1.0 was declared. The declaration should be backed by a permanent evidence ledger."
**Status:** Append-only. Do not edit existing entries. Add new rows when evidence is added or superseded.

---

## How to Read This Ledger

Each section covers one evidence type. Within sections, entries are in chronological order. Verdicts use:
- ✅ PASS — criterion met
- ⚠️ PASS WITH QUALIFICATION — criterion met, scope narrowed by reviewer
- ❌ FAIL — criterion not met
- 📋 FINDING — observation recorded (not a pass/fail criterion)
- 🔍 OPEN — question open at v1.0 declaration

---

## Part 1 — ADR-016 Completion Criteria

The v1.0 declaration rests on three criteria defined in ADR-016 (signed Session 093).

### C1 — Outcome Test

**Criterion:** Governance must measurably improve outcomes vs a baseline that lacks governance.

**Unit of measurement:** Constraint violations — count of admitted items in a singular category exceeding one. A governed system must have fewer violations than a baseline on identical adversarial input.

**Test file:** `runtime/v0.1/tests/test_outcome_s095.py` (Session 095)

**Test design:**
- Consumer: GovernedTaskPlanner (has two singular categories: current-task, current-goal)
- Baseline: BaselinePlanManager (identical interface, no governance layer)
- Adversarial input: 3 goal proposals + 3 task proposals + 2 plural items (designed to create 4 violations under any at-most-one rule)
- Metric: `constraint_violations(planner, categories)` — counts admitted items > 1 per singular category

**Results:**

| Scenario | Governed violations | Baseline violations |
|----------|--------------------|--------------------|
| 3 goal proposals, 3 task proposals | 0 | 4 |

**Why the governed result is a structural guarantee, not statistical:** The AdmissionGateway enforces singular-category constraints at admission time. A second item in a singular category cannot be admitted — it is quarantined before it enters. Therefore zero violations is not a measured probability; it is a necessary consequence of the architecture.

**C1 verdict:** ✅ PASS — Session 095

---

### C2 — Repair Test

**Criterion:** Every quarantined event must produce a structured repair suggestion. The repair loop must be closeable (resolved state must be reachable).

**Test file:** `runtime/v0.1/tests/test_repair_s094.py` (Session 094)

**Test design:** 6 tests covering:
1. RepairSuggestion produced on QUARANTINE (both sides, rule named, 3 pathways present)
2. RepairSuggestion retrievable from ContradictionStore via `get_repair()`
3. `mark_resolved()` closes the repair loop without deleting the contradiction record (I8 preserved)
4. Full RETRACT_EXISTING pathway in practice (retract A, re-admit B)
5. `get_repair()` returns None on ADMITTED verdict
6. `get_repair()` returns None on REJECTED verdict

**Repair pathways defined:**
- RETRACT_EXISTING — retract the current holder, admit the new item
- KEEP_EXISTING — retract the new item, keep the current holder
- HOLD_AS_CONTRADICTION — quarantine both, surface for human resolution

**New data structures (Session 094):**
- `RepairSuggestion` — dataclass produced on every QUARANTINE verdict
- `ResolutionPathway` — enum of three pathways
- `ContradictionStore.get_repair(quarantine_id)` — retrieves repair from persistent store
- `ContradictionStore.mark_resolved(quarantine_id, resolution_note)` — narrow write operation; closes I5 loop

**I5 (Observable Repair Loops) status:** OPERATIONAL at v1.0

**C2 verdict:** ✅ PASS — Session 094

---

### C3 — Buildability Test

**Criterion:** A new governed consumer must be constructable from a self-contained specification packet without access to prior RITAM context.

**Specification packet:** `research/verification/BUILDABILITY_PACKET.md` (224 lines, Session 096)
**Consumer built:** GovernedDecisionLog — `runtime/v0.1/decision_log/governed_decision_log.py` (237 lines)
**Test file:** `runtime/v0.1/tests/test_buildability_s096.py`

**Buildability success criteria (5/5 pass):**
1. ✅ Consumer can be constructed from SubstrateConfig + storage path alone
2. ✅ `set_decision()` proposes to SINGULAR category; a second proposal is quarantined
3. ✅ RETRACT_EXISTING pathway works: retract decision A, admit decision B
4. ✅ `add_rationale()` operates in PLURAL category; multiple rationales coexist
5. ✅ Quarantined decision has a repair suggestion with both conflict sides

**Spec gaps discovered (5):**

| Gap | Severity | Description |
|-----|----------|-------------|
| GAP-1 | BREAKING | `singular_categories` (spec) vs `plural_categories` (impl) — inverted semantics |
| GAP-2 | MEDIUM | `get_repair()` and `mark_resolved()` not in base ContradictionStore spec |
| GAP-3 | HIGH | `plural_categories` default behaviour not documented in SubstrateConfig |
| GAP-4 | LOW | `RepairSuggestion` import path not specified |
| GAP-5 | HIGH | No public `list_admitted(category)` API on AdmissionGateway |

**Interpretation:** The gaps are the output of the buildability test, not its failure. C3 criterion was "constructable from the packet." It was. The gaps record where construction required inference beyond the spec. They are preserved as-found in the codebase per Advisory 005 and the append-only principle.

**Remediation:** ADR-017. Sessions 098–100.

**C3 verdict:** ✅ PASS (5/5 criteria, 5 gaps documented) — Session 096

---

## Part 2 — Gate Evidence

### Gate A — Internal Validation (Session 091)

**What:** Internal gate requiring multiple consumers on the substrate before v1.0 consideration.

**Evidence at Gate A:**
- GovernedNotebook ✅ (Session 080)
- GovernedAgentMemory ✅ (Session 088)
- GovernedTaskPlanner ✅ (Session 091)
- Plural/singular category distinction implemented and tested ✅
- Kill Test suite passing ✅

**Gate A verdict:** ✅ SIGNED — Session 091

---

### Gate B — External Validation (Sessions 092–093)

**What:** External review of two substrate claims before v1.0 consideration.

**Claims reviewed:**
- INSIGHT-114: Regime-Bounded Governance Sensitivity — governance detects abrupt categorical conflict reliably; misses gradual semantic drift systematically
- INSIGHT-121: Cross-Domain Portability — a single governance engine can be reused across multiple consumer applications

**Gate B process:** Advisory 004 — Multi-AI Cold Peer Review (Session 093). Four independent AI reviewers from three model families: ChatGPT/Mahdi, Claude (fresh session, cold), Gemini, Perplexity.

**Summary verdicts:**

| Claim | Verdict | Key narrowing |
|-------|---------|---------------|
| INSIGHT-114 | ⚠️ PASS WITH QUALIFICATION | Regime-boundary IS the finding, not a caveat. Useful framing; not mathematically novel. |
| INSIGHT-121 | ⚠️ PASS WITH QUALIFICATION | "Reusability across same-team, same-stack consumers." Not substrate-generality. Full portability pending external builder test. |

**Convergences across all four reviewers:**
- C-A: Tautology concern (system detects contradictions it was designed to detect)
- C-B: Baseline is trivially weak (system with no governance produces no governance events by design)
- C-C: Manual classification is load-bearing (hardest problem is upstream of the substrate)
- C-D: Cross-domain portability overstated — internal consistency, not portability
- C-E: No independent testing
- C-F: No false positive/negative analysis

**Gate B mechanism:** ADR-012 Amendment 1 (Session 095) formalised multi-AI cold peer review as Phase 2 Gate B (Tier 2.5 on the independence ladder). This does not satisfy ADR-012 gate (b) for spec finalisation — that still requires human expert review.

**Gate B verdict:** ✅ PASSED WITH QUALIFICATIONS — Session 092/093

---

## Part 3 — Kill Test Record

Kill Tests were the primary test instrument before the Outcome Test transition. They asked: "Can governance be killed (rendered inoperative) in N attempts?" All attempts failed (governance remained operational).

| Kill Test session | Consumer | Attempts | Governance events | Result |
|-------------------|----------|----------|-------------------|--------|
| 084 (final Kill Test run) | GovernedNotebook | 5 runs | 5 governance events | 0 kills — governance survived all 5 |
| Prior sessions | Various | Multiple | Multiple | All passed |

**Kill Test → Outcome Test transition:** Session 093 (per Advisory 003, ChatGPT). Kill Test answered "Does governance exist?" but cannot answer "Does governance create value?" Outcome Test (ADR-016 C1) replaced it for v1.0 purposes.

**Kill Test record is preserved.** The transition does not invalidate Kill Test results. They remain valid evidence that governance fires consistently. They are insufficient to claim governance creates value — a claim the Outcome Test now provides evidence for.

---

## Part 4 — Outcome Test Record

| Test file | Session | Governed violations | Baseline violations | Result |
|-----------|---------|--------------------|--------------------|--------|
| test_outcome_s095.py | 095 | 0 | 4 | ✅ Governed strictly better |

**Additional outcome findings (test_outcome_s095.py):**
- `test_outcome_governed_zero_violations`: structural guarantee — 0 violations
- `test_outcome_baseline_has_violations`: baseline produces 4 violations on same input
- `test_outcome_governed_strictly_better`: core C1 claim formally tested
- `test_outcome_repair_on_every_conflict`: 4/4 conflicts have RepairSuggestion (I5 ∩ C1)

---

## Part 5 — Peer Review Record

| Advisory | Date | Reviewer | Scope | Verdict |
|----------|------|----------|-------|---------|
| Advisory 001 | 2026-06-19 | Mahdi (ChatGPT) | Session 088 state — consumer transfer significance, persistence gap, substrate-generality challenge | 📋 FINDING — consumer transfer is the important result; substrate-generality not yet demonstrated |
| Advisory 002 | 2026-06-21 | Mahdi (ChatGPT) | Gate B claims — INSIGHT-114 + INSIGHT-121 | ⚠️ PASS WITH NARROWING (both claims) |
| Advisory 003 | 2026-06-21 | ChatGPT | 9 open questions — programme identity, Kill Test sufficiency, completion condition | 📋 FINDING — led to ADR-016 formalisation |
| Advisory 004 | 2026-06-21 | ChatGPT/Mahdi + Claude (fresh) + Gemini + Perplexity | Gate B multi-AI cold peer review | ⚠️ PASS WITH QUALIFICATIONS |
| Advisory 005 | 2026-06-21 | Mahdi (ChatGPT) | Post ADR-016 strategic review + v1.0 advisory | 📋 FINDING — execute S097 as planned; GAP-1 highest priority; external reproduction is next frontier |


---

## Part 6 — Buildability Audit Record

| Audit | Session | Packet | Consumer built | Criteria pass | Gaps found |
|-------|---------|--------|----------------|---------------|------------|
| C3 Cold Build | 096 | BUILDABILITY_PACKET.md | GovernedDecisionLog | 5/5 | 5 (1 BREAKING, 2 HIGH, 1 MEDIUM, 1 LOW) |

**Audit principle:** The gaps are the evidence. Do not clean up the trail. Future researchers should see exactly where builders stumbled. (Advisory 005.)

---

## Part 7 — Known Limitations at v1.0

These are not future work items — they are the honest boundary of what v1.0 claims.

| Limitation | Severity | Standing since |
|------------|----------|---------------|
| Clean-room gap: all testing on controlled inputs, researcher-assigned categories | 🔍 OPEN — highest priority | Advisory 001 (Session 089) |
| Baseline is trivially weak: no-governance produces no events by design | 🔍 OPEN | Advisory 004 convergence C-B |
| Manual classification is load-bearing: semantic categorisation is done by researcher upstream of substrate | 🔍 OPEN | Advisory 004 convergence C-C |
| External builder: all four consumers built by same team | 🔍 OPEN — gates external handoff | Advisory 005; ADR-017 |
| Same-stack consumers: text + categories + SQLite + single process only | 🔍 OPEN | Advisory 002; Advisory 004 |
| Long-term contradiction accumulation: never tested across sessions | 🔍 OPEN | Advisory 001 |
| False positive / false negative analysis: never run | 🔍 OPEN | Advisory 004 convergence C-F |
| GAP-1 naming inversion in spec | ⚠️ BREAKING — gates external handoff | ADR-016 C3 (Session 096) |
| GAP-5 no public read API | ⚠️ HIGH — gates external handoff | ADR-016 C3 (Session 096) |

---

## Part 8 — Test Count at v1.0

| Test file | Session | Tests | Passing |
|-----------|---------|-------|---------|
| test_repair_s094.py | 094 | 6 | 6/6 |
| test_outcome_s095.py | 095 | 6 | 6/6 |
| test_buildability_s096.py | 096 | 5 | 5/5 |
| (prior suite — consumers + primitives) | 080–093 | 5 | 5/5 |
| **Total** | | **22** | **22/22** |

---

## Ledger Maintenance Notes

This ledger is append-only. New evidence rows are added as work continues:
- When a gap is remediated → add a row to Part 6 and update the gap status in Parts 1 and 7
- When an external builder reproduces a consumer → add a row to Part 6
- When a first real-world user is found → add a new Part 9 (Real-World Validation)
- When new kill test or outcome test runs → add rows to Parts 3 and 4

**Do not edit existing entries.** Record corrections as new rows referencing the entry being corrected.
