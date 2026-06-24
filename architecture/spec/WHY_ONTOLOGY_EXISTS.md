# WHY_ONTOLOGY_EXISTS.md

**Primitive:** Ontology
**Version:** v1.0.7 (target)
**Author:** Muaddib (Claude), Ritam Session 107
**Status:** DRAFT — awaiting Rishi sign-off

---

## §1 The Concrete Substrate Failure This Primitive Addresses

Today the substrate is conceptually frozen at birth.

When `AdmissionGateway` is initialised it loads `SubstrateConfig.known_categories` into
`self._known_categories: set[str]`. That set never changes at runtime. Every proposal
whose category is absent from the set is REJECTED with an OBSERVATION_GAP signal and
a gap record. The only way to add a new category is to stop the substrate, edit the
config, and restart.

This is not a minor convenience gap. It is a governance failure with a specific shape:

**The substrate can perceive a gap (OBSERVATION_GAP fires, gap is persisted) but it
has no governed pathway to close it.** The only repair is manual config surgery followed
by a restart — neither of which the substrate can observe, audit, or signal. The change
leaves no trace in the governance record.

Consider a concrete scenario: a second consumer type begins proposing items under
category `"weather_forecast"`. The substrate fires OBSERVATION_GAP repeatedly. A human
reads the logs, adds `"weather_forecast"` to the config file, and restarts. The substrate
now accepts the category — but there is no record of when that category was added, by
what authority, or whether it was added in response to the gap. The gap log says
"category was unknown"; the admission log says "items were admitted"; nothing connects
the two. The substrate's conceptual structure mutated silently.

**Ontology exists to make category mutation a governed act with a signal, a record,
and an audit trail.**

---

## §2 Why "Ontology" and Not "Category Registry"

In philosophy, ontology is the study of what kinds of things exist. In a cognitive
substrate, it governs what kinds of content the substrate recognises — what it can
represent, what it considers distinct, and what it treats as equivalent.

The name matters because it signals scope. A category registry is an implementation
detail. An ontology primitive is a governance boundary: nothing enters the substrate's
conceptual vocabulary without passing through it.

The distinction the primitive protects:

> **Category existence ≠ category validity.**

Adding `"weather_forecast"` to the substrate means the substrate can now receive and
govern weather forecasts. It does not mean weather forecasts are reliable, important,
or well-defined knowledge. The Ontology primitive records the *structural* fact
(a category now exists) while explicitly not making the *epistemic* claim
(that its content is trustworthy). That is Epistemic's job.

---

## §3 What Operations Does Ontology Govern (v1 Scope)

Five operations are conceivable: Add, Remove, Rename, Merge, Split.

**v1 implements: Add and Remove only.**

Rationale:

- **Add** is the primary repair pathway for OBSERVATION_GAP. Without it, the gap
  primitive can observe blindness but cannot resolve it through governed means.
  This is the highest-priority gap.

- **Remove** is the necessary complement: a substrate that can only grow its
  vocabulary has no governed way to retire categories that become obsolete,
  erroneous, or misleading. Removal without governance risks silent loss of items
  whose category has been removed.

- **Rename** is syntactic sugar for Remove + Add with lineage. Deferred to v2 —
  it requires migrating existing items, which needs the Repair primitive's
  lifecycle machinery to do properly.

- **Merge** and **Split** are ontological claims about the relationship between
  categories (two things were actually one; one thing was actually two). These
  require semantic reasoning to execute correctly and are explicitly deferred.
  They are not substrate-level decisions in v1.

**v1 scope summary:** `add_category()` + `remove_category()`.

---

## §4 The Category Properties Question (INSIGHT-127)

The memory-api analysis (INSIGHT-127, Session 107 pre-work) raised a design question:
should Ontology govern only category *existence* or also category *properties*?

In the current substrate, two distinct config fields govern categories:
- `SubstrateConfig.known_categories` — which categories exist
- `SubstrateConfig.singular_categories` — which of those categories enforce at-most-one

These are related but separate. Currently, there is no governed relationship between
them. A category can be added to `known_categories` via config edit while
`singular_categories` remains unchanged — and vice versa. Neither change is audited.

**Decision for v1:** Ontology governs both existence AND the singular property
as a single operation.

`add_category(name, singular=False)` registers the category as known and simultaneously
records whether it enforces singular admission. This is architecturally cleaner than
two separate unaudited config fields because:

1. Singularity is a governance-relevant property — it determines whether the
   Coordination primitive fires COORDINATION_CONFLICT for this category.
   It belongs in the governance record alongside the category itself.

2. A category added without specifying singularity will default to plural (False)
   — the safer default. The substrate gets weaker protection but never silent
   unexpected behaviour.

3. The OntologyRecord (§6) captures the singular setting at the time of addition,
   giving auditability: "category X was added as singular at time T, by operation Y."

This does NOT introduce category importance weights (as memory-api has). Weight is
an Epistemic and Temporal concern — how much to trust and retain an item. It is not
an ontological property of what the category *is*. That boundary is held firm.

---

## §5 What Signal Fires

`ONTOLOGY_MUTATION` fires on every governed category change: addition or removal.

The signal payload records:
- `operation`: `"add"` or `"remove"`
- `category`: the category name
- `singular`: the singularity property (for add operations)
- `reason`: optional caller-supplied rationale string

Why a signal rather than silent mutation? Because every change to the substrate's
conceptual vocabulary should be observable by consumers. A consumer that has been
operating under the assumption that category X does not exist needs the ability to
react when X is added. The signal is the governed notification mechanism.

Signal-and-continue: the substrate does not hold pending admissions while ONTOLOGY_MUTATION
is emitted. Like COORDINATION_CONFLICT, it records and continues.

---

## §6 The OntologyRecord and OntologyLog

A new frozen dataclass `OntologyRecord` captures each mutation:

```
OntologyRecord:
  record_id: str          # unique ID
  operation: str          # "add" | "remove"
  category: str           # category name
  singular: bool | None   # None for remove operations
  reason: str | None      # caller-supplied rationale
  mutated_at: str         # ISO timestamp
```

`OntologyLog` is a SQLite table persisting these records. Like `CoordinationLog` and
`ObservationLog`, it is independent of the admission channel — `drain()` does not
clear it. The mutation history survives channel resets.

---

## §7 Protected Distinctions

| This primitive governs | This primitive does NOT govern |
|---|---|
| Whether a category exists in the substrate | Whether items in that category are trustworthy |
| Whether a category enforces singular admission | How many items in the category are retained |
| The audit trail of category changes | The content of those items |
| The signal that a mutation occurred | The consequence of the mutation for existing items |

**The critical one:** removing a category does NOT delete existing items admitted under
it. Those items remain in the admission log. The substrate records that the category
was removed, emits ONTOLOGY_MUTATION, and from that point forward rejects new proposals
in that category (OBSERVATION_GAP). Existing items are untouched. Deletion of existing
items is a Repair operation, not an Ontology operation.

This boundary keeps Ontology clean: it governs the substrate's vocabulary, not the
substrate's history.

---

## §8 Failure Modes and How They Are Governed

**F1 — Adding a category that already exists.**
Result: no-op with a descriptive error. The OntologyLog is not written. No duplicate
record, no duplicate signal.

**F2 — Removing a category that does not exist.**
Result: no-op with a descriptive error. Same principle.

**F3 — Category removed while items still reference it.**
Result: governed. Existing items are preserved; they carry a now-retired category name.
Future proposals to that category get OBSERVATION_GAP (the category is no longer known).
The gap record and the ontology removal record together tell the story: "category was
retired at time T; gaps observed at time T+n are expected consequences."

**F4 — Ontology mutation mid-batch (propose_batch in flight).**
The mutation takes effect immediately on `_known_categories`. Proposals already
processed in the batch are unaffected. Subsequent proposals in the same batch see the
updated vocabulary. Signal-and-continue: no batch is held pending.

---

## §9 API

```python
# Add a category to the substrate's vocabulary
gw.add_category("weather_forecast", singular=False, reason="Gap observed in OBSERVATION_GAP log")
# → emits ONTOLOGY_MUTATION(operation="add", category="weather_forecast", singular=False)
# → writes OntologyRecord to ontology_log
# → subsequent proposals to "weather_forecast" are admitted normally

# Remove a category from the substrate's vocabulary
gw.remove_category("weather_forecast", reason="Consumer retired")
# → emits ONTOLOGY_MUTATION(operation="remove", category="weather_forecast")
# → writes OntologyRecord to ontology_log
# → subsequent proposals to "weather_forecast" get OBSERVATION_GAP

# Query the mutation history
gw.list_ontology_mutations(operation="add")   # filter by operation
gw.list_ontology_mutations()                  # all mutations, ordered by mutated_at
```

---

## §10 What This Unlocks

Once Ontology is in place, the gap-to-resolution pathway is fully governed:

```
OBSERVATION_GAP fires (gap persisted in observation_log)
  → human or agent calls add_category()
  → ONTOLOGY_MUTATION fires (mutation persisted in ontology_log)
  → subsequent proposals now admitted under the new category
```

For the first time, the substrate's response to its own blindness is observable
end-to-end. The gap and the repair are both in the governance record. Nothing
is silent.

This also closes the `singular_categories` audit hole: every change to what categories
enforce singular admission is now a governed ontology event with a timestamp and a record.
Config restarts for category changes become optional rather than mandatory.

---

## §11 Progression Note

After Ontology: **Repair-as-Primitive** — elevating RepairSuggestion from an annotation
on admission results to a governed entity with its own lifecycle (PENDING → ACKNOWLEDGED
→ EXECUTED → VERIFIED). Ontology must precede Repair because Repair's resolution
pathways may include ontology mutations (e.g. "add category X to close this gap").
Repair needs a governed Ontology to call.

Primitive order: Cognition tier complete → **Ontology (Structure)** → Repair-as-Primitive
(Governance Lifecycle).

---

*Awaiting Rishi sign-off before implementation.*
