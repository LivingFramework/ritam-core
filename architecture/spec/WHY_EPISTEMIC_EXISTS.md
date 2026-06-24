# Why Epistemic Exists

*Session 104 · Pre-implementation behavioural definition*
*Format follows WHY_TEMPORAL_EXISTS.md — problem → behaviour → failure → repair → executable form*

---

## §1 The Problem

The substrate currently treats all admitted items as epistemically identical. Once admitted, an item carries no record of how confident the proposer was when proposing it. This creates three concrete substrate failures.

**Failure 1 — Undifferentiated admission.** When two items contradict and one is quarantined, the governance layer has no way to know whether the conflict is between two high-confidence claims or between a strong claim and a speculative one. The QUARANTINED signal fires identically in both cases. A consumer trying to resolve the contradiction has no epistemic ground to stand on.

**Failure 2 — No signal for epistemic fragility.** A consumer may operate for an extended period with only low-confidence or speculative items admitted in a category. The substrate has no mechanism to surface this. The consumer proceeds as if it has firm ground when it has none.

**Failure 3 — Confidence invisible to provenance.** The ProvenanceRecord captures who proposed an item and when. It does not capture how confident they were. Auditing the epistemic history of a decision is impossible — all you know is that something was admitted.

---

## §2 What Epistemic Governs

Epistemic governs the **confidence declarations** associated with admitted items.

Three governing mechanisms:

1. **Confidence tagging at admission.** A proposer may declare a confidence level at proposal time. The substrate records what was declared; it does not compute or infer confidence.

2. **Epistemic fragility detection.** When all non-retracted items in a category fall below a declared threshold, the substrate surfaces this as an observable signal. It does not remove items.

3. **Confidence visible in provenance.** The AdmissionRecord carries the declared confidence, making it auditable by consumers and humans.

**Protected distinction:** Confidence is a **declaration**, not a measurement. The substrate records what the proposer claimed to believe. It has no mechanism for computing truth likelihood, semantic credibility, or empirical support. Those are epistemic judgements made outside the substrate; the substrate records and surfaces them — it does not make them.

---

## §3 Observable Behaviour

**B1 — Confidence tagging.** `gw.propose(content, category, source, confidence=0.75)` stores the confidence declaration alongside the item. Items proposed without a confidence argument have `confidence = None` (untagged, not assumed certain).

**B2 — Confidence in AdmissionRecord.** `AdmissionRecord.confidence: float | None` is populated from the stored value. Consumers calling `list_admitted(category)` receive items with their declared confidence visible.

**B3 — Fragility detection.** `gw.check_epistemic(category, threshold=0.5)` returns the list of tagged admitted items in a category that fall below the threshold. An alert fires when **all** tagged items fall below the threshold — one item meeting or exceeding the threshold suppresses the alert.

*Trigger design note (Session 104):* Two alternatives were considered — average confidence and proportion-based detection. Average confidence was rejected because it produces false reassurance: in a category with items at [0.95, 0.10, 0.10, 0.10, 0.10], the average may exceed the threshold while four of five items are fragile. Average answers "what is the center?" — Epistemic governance should answer "how robust is the structure?" The all-below-threshold trigger was chosen as the conservative default. The proportion-based trigger (alert when ≥X% of tagged items fall below threshold) is the identified forward direction — it correctly surfaces [0.95, 0.10, 0.10, 0.10, 0.10] as fragile while correctly not alerting on [0.95, 0.95, 0.95, 0.10]. This remains an open design question (OQ) to resolve when the proportion parameter is calibrated by domain evidence.*

**B4 — EPISTEMIC_ALERT signal.** When `check_epistemic()` finds a category with no item meeting the threshold, it emits `SignalType.EPISTEMIC_ALERT` on the ObservationChannel. One alert per fragile category per call. Does not retract any item.

**B5 — Repair suggestion.** Each EPISTEMIC_ALERT produces a RepairSuggestion with three pathways: `RETRACT_AND_REPLACE` (remove low-confidence item, propose stronger evidence), `DOWNGRADE` (mark item as speculative via retract-and-repropropose at explicit low confidence), `REQUEST_EVIDENCE` (hold item, seek higher-confidence proposition before deciding).

---

## §4 Failure Modes

**F1 — Confidence inflation.** A proposer declares `confidence=0.99` on a speculative claim. The substrate cannot detect this — it records what was declared. Epistemic governance depends on proposer honesty or external calibration. The substrate's role is to make declarations auditable, not to validate them.

**F2 — Threshold sensitivity.** `check_epistemic()` uses a caller-supplied threshold. Different thresholds produce different alert conditions for the same items. The substrate does not enforce a canonical threshold — that is a consumer or domain decision.

**F3 — Untagged items and mixed categories.** A category may contain both tagged and untagged (`confidence=None`) items. `check_epistemic()` must have a defined policy for untagged items. Policy: untagged items are treated as non-fragile for the purpose of alert suppression (they are not counted as low-confidence, but their confidence is not available for audit).

**F4 — Confidence on retracted items.** When an item is retracted, its confidence declaration is preserved in the historical record (I3 — Explicit State, immutable audit). Retracted items do not count toward fragility detection.

---

## §5 Repair Modes

Three pathways on every EPISTEMIC_ALERT RepairSuggestion:

**RETRACT_AND_REPLACE** — Retract the low-confidence item. Propose fresh content with higher confidence or with stronger evidential basis. Use when better information is available now.

**DOWNGRADE** — Retract the item. Repropropose the same content with an explicit low-confidence tag and updated source note. Use when the proposer wants to keep the item but make its epistemic status explicit and visible rather than implicit.

**REQUEST_EVIDENCE** — Take no substrate action. Record the decision to hold pending evidence. Use when the consumer knows higher-confidence information may arrive and chooses to wait rather than act on fragile ground.

---

## §6 Relationship to Temporal and State

Epistemic and Temporal are orthogonal. Temporal asks: *how old is this item's admission?* Epistemic asks: *how confident was the proposer?* An item can be newly admitted with low confidence, or old with high confidence. These are independent properties; both are visible on AdmissionRecord.

State (singular/plural enforcement) is also orthogonal. A singular category can have one high-confidence item or one low-confidence item. Epistemic does not change admission rules — it adds a visible property to what gets admitted.

Repair is shared infrastructure. Temporal uses RepairSuggestion with temporal pathways; Epistemic uses RepairSuggestion with epistemic pathways. The structure is the same; the pathways are domain-specific.

---

## §7 What Epistemic Does NOT Do

- **Does not compute confidence.** No LLM, no semantic similarity, no external calibration. The substrate records declarations.
- **Does not block admission.** An item with `confidence=0.01` is admitted if it passes governance checks. Epistemic tags but does not gate.
- **Does not auto-retract.** EPISTEMIC_ALERT fires; the consumer decides. Same principle as TEMPORAL_ALERT.
- **Does not aggregate.** The substrate does not average, weight-sum, or propagate confidence across items. Each item's confidence is its own declared value.
- **Does not validate declarations.** The substrate cannot determine whether `confidence=0.9` is epistemically justified. That is the proposer's responsibility.
- **Does not infer confidence for untagged items.** A missing confidence tag is not treated as high or low confidence — it is recorded as untagged.

---

## §8 Executable Form

Epistemic exists when all of the following are true and tested:

1. `AdmissionRecord` carries `confidence: float | None` — `None` for untagged items.
2. `gw.propose(..., confidence=0.75)` stores the confidence declaration; value visible in `list_admitted()`.
3. `gw.check_epistemic(category, threshold=0.5)` returns `list[AdmissionRecord]` — all non-retracted, tagged, below-threshold items in the category — when no tagged item meets or exceeds threshold; empty list otherwise.
4. `SignalType.EPISTEMIC_ALERT` is a member of the `SignalType` enum.
5. `check_epistemic()` emits `SignalType.EPISTEMIC_ALERT` when the category is epistemically fragile (all tagged items below threshold).
6. No `EPISTEMIC_ALERT` is emitted when at least one tagged item meets or exceeds the threshold.
7. `RepairSuggestion` produced for each alert with pathways: `RETRACT_AND_REPLACE`, `DOWNGRADE`, `REQUEST_EVIDENCE`.
8. Test: admit item with `confidence=0.2`, call `check_epistemic(category, threshold=0.5)`, assert `EPISTEMIC_ALERT` emitted and item still admitted (no auto-retraction).

---

## §9 Protected Distinction

**Declared confidence is not validated truth.**

The substrate records what proposers claim to believe about their own certainty. It does not determine whether those claims are accurate, whether the evidence is sufficient, or whether the confidence is calibrated. EPISTEMIC_ALERT signal payloads must never say "unreliable item" or "false claim" — only "declared confidence below threshold."

This distinction matters for trustworthy AI: a substrate that flags *its own epistemic fragility* without claiming to know what is true is fundamentally different from one that silently treats all items as equally credible or, worse, secretly adjusts what it surfaces based on inferred reliability. Transparency about uncertainty is the epistemic equivalent of observable repair loops.

---

*Awaiting sign-off before implementation.*

---

## §10 Design Sign-Off — Session 104

**Rishi's review (verbatim reasoning, 2026-06-22):**

On the trigger question — average vs. all-below-threshold vs. proportion:

"The reason I dislike averages is that they create fake certainty. Averages answer: What is the center? Epistemic governance should answer: How robust is the structure? Those are different questions."

"Governance ≠ optimization. Governance = surface meaningful risk. Averages are optimization-style thinking. Fragility is governance-style thinking."

Decision for v1.0.3 implementation: **all-below-threshold** (conservative; avoids false reassurance). Forward direction: **proportion-based fragility detection** — alert when ≥X% of tagged items fall below threshold. Neither pure average nor pure all-below; the proportion trigger correctly handles the [0.95, 0.10, 0.10, 0.10, 0.10] case that all-below misses.

Sign-off: ✅ Proceed to implementation.
