# ObservationGap — Formal Definition
**Session 079 · pre-implementation · answers ChatGPT advisory point 3 (2026-06-18)**
*This page must be read before implementing ObservationChannel. It defines what an ObservationGap is, how it differs from adjacent concepts, and what observable behaviour proves it exists.*

---

## 1. What condition creates an ObservationGap?

An ObservationGap occurs when a caller proposes knowledge in a **category the substrate has no representation for** — i.e., a category not in `SubstrateConfig.known_categories`.

The substrate cannot evaluate the item's coherence, check it for contradictions, or apply governance rules to it — not because the item is wrong, but because the substrate has **no ontological basis** to process it at all.

This is a **second-order blindness**: the substrate does not merely lack the item; it lacks the capacity to even *classify* the gap as a gap without this signal.

```
known_categories = ["claim", "evidence", "question"]

propose(content="...", category="protocol", source="alice")
→ OBSERVATION_GAP signal + REJECTED result
```

---

## 2. How is it distinguished from missing data?

| | Missing Data | ObservationGap |
|---|---|---|
| **Definition** | The substrate knows a category exists but holds no items matching a query | The substrate has no representation for the category itself |
| **Who knows about the gap** | The caller (they asked for something and got nothing) | Neither the caller nor the substrate — without the signal, the absence is completely invisible |
| **Substrate response** | Returns empty result set — this is normal, expected behaviour | Emits OBSERVATION_GAP signal — this is an anomaly that must be surfaced |
| **Governance implication** | No governance failure | Governance failure: item cannot be admitted, governed, or tracked |
| **Example** | `list_by_category("claim")` returns `[]` — no claims held yet | `propose(category="protocol")` where "protocol" is not a known category |

Missing data is an empty result. ObservationGap is the substrate's representation boundary being crossed.

---

## 3. How is it distinguished from contradiction?

| | Contradiction | ObservationGap |
|---|---|---|
| **What the substrate has** | Two or more items it *can* represent, which conflict | Zero items it *can* represent in this category |
| **Items preserved** | Both conflicting items quarantined and retrievable | No item stored (REJECTED) |
| **Signal type** | `SignalType.QUARANTINED` | `SignalType.OBSERVATION_GAP` |
| **Governance response** | Both items preserved; caller informed of conflict | Item rejected; caller informed the category is unknown |
| **Resolution path** | Contradiction may eventually be resolved (v0.2+) | Resolution = add the category to `known_categories` (config change) |

A contradiction means the substrate has too much (conflicting knowledge). An ObservationGap means the substrate has no frame for the knowledge at all.

---

## 4. What behaviour proves ObservationGap exists?

Three observable tests (from API_SPEC.md §5, Test C):

**Test C1 — signal is emitted:**
```python
gw.propose(content="anything", category="UNKNOWN_XYZ", source="test")
signals = oc.drain()
assert any(s.signal_type == SignalType.OBSERVATION_GAP for s in signals)
```

**Test C2 — signal carries the category:**
```python
gap = next(s for s in signals if s.signal_type == SignalType.OBSERVATION_GAP)
assert gap.category == "UNKNOWN_XYZ"
```

**Test C3 — item is not stored (absence is clean):**
```python
result = gw.propose(content="anything", category="UNKNOWN_XYZ", source="test")
assert result.verdict == AdmissionVerdict.REJECTED
# No item_id assigned; nothing in storage
assert result.item_id is None
```

If all three pass, ObservationGap exists as an observable substrate behaviour — not a placeholder.

---

## 5. Implementation note for Session 079

In v0.1, ObservationGap detection is straightforward: if `category not in self._known_categories`, emit `OBSERVATION_GAP` signal and return `REJECTED`. No semantic inference. No fuzzy matching.

The signal `payload` must include at minimum:
```python
{"category": category, "content_type": type(content).__name__}
```

The `source_operation` field must be `"AdmissionGateway.propose"`.

This is not a placeholder — it is a precisely defined, testable behaviour. The generalisation question (what if a category is *partially* known?) is deferred to v0.2 under `REPRESENTATION_LIMIT`.

---

## 6. Precision amendment — what ObservationGap does and does not detect
**Session 081 · ChatGPT advisory point 2 (2026-06-18)**

### What it detects
ObservationGap detects **schema limitations** — specifically, that a caller attempted to file knowledge in a category the substrate has no representation for.

This is a structural check, not a semantic one:
- It fires when `category not in SubstrateConfig.known_categories`.
- It does not inspect the *content* of the item.
- It does not reason about whether the category *should* exist.
- It does not detect that the substrate is blind to a phenomenon — only that it lacks a named slot for a category.

### What it does NOT detect
| Claim | Correct? |
|---|---|
| "ObservationGap detects that the substrate is epistemically blind to X" | **No** — it detects that the substrate has no schema entry for category X |
| "ObservationGap surfaces unknown unknowns" | **No** — it surfaces *named unknowns*: the caller knew what category they wanted; the substrate did not have it |
| "ObservationGap is a universal blindness detector" | **No** — it is a category-validation gate |
| "ObservationGap means the substrate cannot govern this content" | **Yes** — this is the precise and honest claim |

### The honest claim
> ObservationGap signals that a piece of knowledge was proposed in a category the substrate cannot govern, because that category is outside its defined ontology. The substrate surfaces this rather than silently dropping the item.

This is genuinely useful — silence would be worse. But it is a narrower claim than "epistemic blindness detection." The distinction matters for what Research on ObservationGap can and cannot prove.

### What would genuine epistemic blindness detection require?
Detecting that the substrate is blind to a *phenomenon* (not just a category name) would require:
- Semantic understanding of content — prohibited by anti-framework rules (Appendix B)
- Or a human-in-the-loop to observe the gap between what was attempted and what the substrate understood

That is a v0.2+ question, not a v0.1 claim. Log under OQ-030 (blindness detection mechanism).
