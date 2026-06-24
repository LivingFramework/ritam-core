# Runtime v0.1 — API Specification
**Phase 2 · Interface-First · Session 078**  
*v0.2 amendments: Session 085 — `canonical-claim` singular category, `empirical-finding` plural enforcement, content validation at admission boundary.*
*Subordinate to `/NORTH_STAR.md` + `/SUBSTRATE_DEFINITION.md`. No implementation code in this file. This contract defines what callers can do and what the substrate guarantees.*

---

## Overview

Runtime v0.1 exposes **three interfaces**. Together they fulfil the Capability Statement:

> *"A caller can propose knowledge for admission; the substrate either admits it with provenance, quarantines it as a contradiction with reasons, or rejects it — and representational gaps that would produce silence are surfaced as typed observable signals, not silently dropped."*

All interfaces use Python 3.10+ type annotations. Implementations import from `ritam.runtime.v01`.

---

## 0. Public Types — Import Paths (GAP-4 fix — Session 099)

All public types are importable from two locations. Use whichever is cleaner for your code:

```python
# Primary types — available directly from the package
from ritam.runtime.v01 import (
    Substrate,
    SubstrateConfig,
    AdmissionVerdict,
    AdmissionRecord,   # GAP-5 fix — Session 100: read admitted items by category
    GapRecord,         # Session 105: Observation primitive — persistent perceptual limit record
    SignalType,
)

# Repair types — from types module
from ritam.runtime.v01.types import (
    RepairSuggestion,      # Structured repair output on every QUARANTINED event
    ResolutionPathway,     # One of three resolution options within a RepairSuggestion
    ContradictionRecord,   # Record stored per contradiction in ContradictionStore
    AdmissionResult,       # Return type of AdmissionGateway.propose() and .retract()
    SubstrateSignal,       # Signal emitted on the ObservationChannel
    Provenance,            # Attached to every admitted item
)
```

If you only need the repair types (e.g., when processing quarantine results):
```python
from ritam.runtime.v01.types import RepairSuggestion, ResolutionPathway
```

---

## 1. AdmissionGateway

The single entry point for all knowledge entering the substrate. Constitutive, fail-closed (A-list #1, #2, #5). Every item that enters the substrate passes through this gateway; nothing is written directly to storage.

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any
from datetime import datetime


class AdmissionVerdict(Enum):
    ADMITTED    = "admitted"     # Accepted; provenance record created
    QUARANTINED = "quarantined"  # Contradiction detected; item preserved alongside conflict
    REJECTED    = "rejected"     # Fails governance rule; not stored


@dataclass(frozen=True)
class ProvenanceRecord:
    item_id: str              # Stable identifier for this knowledge item
    source: str               # Who/what proposed it (caller identity)
    admitted_at: datetime     # Timestamp of admission decision
    basis: str                # Why it was admitted (rule name or "no conflict detected")


@dataclass(frozen=True)
class AdmissionResult:
    verdict: AdmissionVerdict
    item_id: str | None          # Set on ADMITTED and QUARANTINED; None on REJECTED
    provenance: ProvenanceRecord | None  # Set on ADMITTED only
    reason: str                  # Human-readable explanation for any verdict
    conflict_ids: list[str]      # Item IDs already held that conflict (non-empty on QUARANTINED)


class AdmissionGateway:
    """
    Propose a knowledge item for admission into the substrate.

    Invariants (must hold in any conforming implementation):
    - I1 (Governance Before Autonomy): the governance checkpoint runs before any write.
      A runtime error during the checkpoint MUST result in REJECTED, never a silent write.
    - I3 (Explicit State): the caller always receives a typed AdmissionResult; no silent paths.
    - I7 (No Hidden Persistence): the gateway is the ONLY path by which items enter storage.
    - A-list #1 (Constitutive enforcement): governance is fail-closed; network/storage errors → REJECTED.
    - A-list #3 (Contradiction containment): on conflict, BOTH items are preserved; neither is overwritten.
    - A-list #5 (Write-time gating): for instantaneous or time-sensitive items, the gateway
      evaluates temporal coherence before admission (not deferred to read time).
    """

    def propose(
        self,
        content: Any,
        category: str,
        source: str,
        *,
        temporal_context: datetime | None = None,
        expires_after_seconds: int | None = None,
    ) -> AdmissionResult:
        """
        Propose a knowledge item for admission.

        Args:
            content:          The item to admit (any serialisable value).
                              Must not be None, empty string, or whitespace-only; violating
                              items are REJECTED at Step 0 (content validation) before any
                              category or contradiction check is performed (OQ-056).
            category:         Ontology category the item belongs to (must be a known category;
                              unknown category → ObservationGap signal emitted + REJECTED).
                              Categories are either SINGULAR or PLURAL (see §4.1).
            source:           Identity of the proposing caller.
            temporal_context: Optional timestamp the item refers to (enables write-time
                              temporal coherence check; A-list #5).

        Returns:
            AdmissionResult with verdict, item_id (if stored), provenance (if admitted),
            reason, and conflict_ids (if quarantined).

        Raises:
            RuntimeError: only if the substrate itself is in an unrecoverable state.
                          Callers MUST treat an unexpected exception as equivalent to REJECTED.
        """
        ...

    def retract(self, item_id: str, source: str, reason: str) -> AdmissionResult:
        """
        Retract a previously admitted item.
        Retraction is itself a governed operation — it is logged with provenance.
        Does not delete; marks the item as retracted (immutable audit trail, I3/I7).

        Returns AdmissionResult with verdict ADMITTED (retraction accepted) or REJECTED.
        """
        ...

    def list_admitted(self, category: str) -> list[AdmissionRecord]:
        """
        Return all currently admitted (non-retracted) items in a category.

        GAP-5 fix (Session 100, ADR-017). Closes the public read-by-category gap.
        Previously, consumers that needed to read current state had to access
        self._substrate._db directly — a private attribute. This method is the
        correct public API; direct DB access is not part of the contract.

        Returns items ordered by admitted_at ascending.
        Returns an empty list if the category is unknown or has no admitted items.
        """
        ...

    def age_of(self, item_id: str) -> float:
        """
        Return the age of an item in seconds since its admitted_at timestamp.
        Session 103 — Temporal primitive (WHY_TEMPORAL_EXISTS.md §8 Condition 3).

        Raises KeyError if item_id is not found.
        Does not check retracted status — age is a fact about admission, not currency.
        """
        ...

    def check_expired(self) -> list[AdmissionRecord]:
        """
        Find all non-retracted items whose expiry contract (expires_after_seconds) has elapsed.
        Session 103 — Temporal primitive (WHY_TEMPORAL_EXISTS.md §8 Conditions 4–7).

        For each expired item:
          - Emits SignalType.TEMPORAL_ALERT on ObservationChannel.
          - Produces RepairSuggestion with pathways: RETRACT_AND_REPLACE, EXTEND, HOLD_AS_STALE.

        Returns list of expired AdmissionRecords. Empty list if none.

        Protected distinction (§9): does NOT retract any item. The substrate signals;
        the consumer decides. Signal payload: "item age exceeds declared contract" —
        never "expired claim" or "invalid item".
        """
        ...


@dataclass(frozen=True)
class AdmissionRecord:
    """
    A single admitted (non-retracted) item returned by list_admitted().
    Import path: from ritam.runtime.v01.types import AdmissionRecord
    (also available via: from ritam.runtime.v01 import AdmissionRecord)
    """
    item_id: str       # Stable ID assigned at admission
    category: str      # Ontology category
    content: Any       # The admitted content value
    source: str        # Source identifier who proposed this item
    admitted_at: str               # ISO-format datetime string; parse with datetime.fromisoformat()
    expires_after_seconds: int | None = None  # None = no expiry contract (Session 103)
    expired_at: str | None = None             # ISO-format expiry time; None if no contract
```

---

## 2. ContradictionStore

Query interface for all quarantined contradictions. Items quarantined by AdmissionGateway are never overwritten or deleted — they live here, accessible and auditable (A-list #3, invariant I8).

`get_repair()` and `mark_resolved()` are the only write operations — a narrow exception to the read-only design, required by ADR-016 C2 (Repair) and Invariant I5 (Observable Repair Loops). [GAP-2 fix — Session 098]

```python
from dataclasses import dataclass
from typing import Any
from datetime import datetime


@dataclass(frozen=True)
class ContradictionRecord:
    quarantine_id: str           # Stable ID for this contradiction pair/group
    item_ids: list[str]          # All item IDs involved in the contradiction
    contents: list[Any]          # The conflicting content values (same order as item_ids)
    categories: list[str]        # Ontology categories of each item
    sources: list[str]           # Who proposed each item
    quarantined_at: datetime     # When the contradiction was first detected
    reason: str                  # Why these items conflict (governance rule name)
    resolved: bool               # True once mark_resolved() is called
    resolution_note: str | None  # Human decision note, set by mark_resolved()


class ContradictionStore:
    """
    Primary access to all preserved contradictions, with repair retrieval and resolution.

    Invariants:
    - I8 (Contradiction Visibility): contradictions are surfaced, never hidden or silently deleted.
    - I5 (Observable Repair Loops): every quarantine produces a repair; every repair is closeable.
    - I3 (Explicit State): all held contradictions are inspectable by callers.
    - A-list #3: the retrieval pool is protected; contradictions are never overwritten.

    Write operations: ONLY get_repair (read) and mark_resolved (narrow write).
    Contradictions themselves are written exclusively by AdmissionGateway.
    """

    def get(self, quarantine_id: str) -> ContradictionRecord | None:
        """Return a specific contradiction record by ID, or None if not found."""
        ...

    def list_all(self) -> list[ContradictionRecord]:
        """Return all preserved contradictions, ordered by quarantined_at ascending."""
        ...

    def list_by_category(self, category: str) -> list[ContradictionRecord]:
        """Return all contradictions involving items in the given ontology category."""
        ...

    def list_involving(self, item_id: str) -> list[ContradictionRecord]:
        """Return all contradictions that involve the given item_id."""
        ...

    def count(self) -> int:
        """Return total number of preserved contradiction records."""
        ...

    def get_repair(self, quarantine_id: str) -> RepairSuggestion | None:
        """
        Return the RepairSuggestion generated when this contradiction was quarantined.
        Returns None if the quarantine_id is not found or has no repair record.
        Every QUARANTINED AdmissionResult produces a RepairSuggestion automatically.
        """
        ...

    def mark_resolved(self, quarantine_id: str, resolution_note: str) -> bool:
        """
        Record a human or agent decision closing the repair loop (Invariant I5).
        Sets resolved=True and stores resolution_note on the ContradictionRecord.
        Does NOT delete the contradiction — original conflict content is always preserved (I8).
        Returns True on success, False if quarantine_id not found.
        This is the ONLY write operation on ContradictionStore.
        """
        ...


@dataclass
class RepairSuggestion:
    """
    Structured repair output produced on every QUARANTINED event (ADR-016 C2).
    Import path: from ritam.runtime.v01.types import RepairSuggestion
    """
    quarantine_id: str                       # Links to the ContradictionRecord
    category: str                            # Category where the conflict occurred
    incoming_content: Any                    # Content that was blocked
    incoming_source: str                     # Who proposed the blocked content
    existing_items: list[dict]               # [{item_id, content, source}] — the current holder(s)
    rule_triggered: str                      # Human-readable rule description
    resolution_pathways: list[ResolutionPathway]  # Always 3 pathways
    generated_at: datetime


@dataclass
class ResolutionPathway:
    """One of three structured resolution options in a RepairSuggestion."""
    pathway_id: str        # "RETRACT_EXISTING" | "KEEP_EXISTING" | "HOLD_AS_CONTRADICTION"
    description: str       # Plain-language description of what this pathway means
    action_required: str   # What the caller must do to execute this pathway
```

---

## 2b. AdmissionGateway — Observation Primitive (Session 105)

    def list_gaps(self, category: str | None = None) -> list[GapRecord]:
        """
        Return all persisted gap records from ObservationLog.
        WHY_OBSERVATION_EXISTS.md §8 Conditions 3–4.

        Gap records persist independently of ObservationChannel.drain().
        Draining the signal bus does not remove gap records.

        Args:
            category: if provided, filter to gaps for this specific unknown category.
                      If None, return all gap records ordered by observed_at ascending.

        Returns empty list if no gaps have been observed.

        Protected distinction: gap records describe perceptual limits — never the
        validity or importance of what was proposed.
        """

    def gap_count(self, category: str) -> int:
        """
        Return how many times an unknown category has been encountered.
        WHY_OBSERVATION_EXISTS.md §8 Condition 5.

        Returns 0 if the category has never been encountered as a gap.
        This is the signal for deciding whether to expand known_categories.
        """


@dataclass(frozen=True)
class GapRecord:
    """
    A persistent record of a substrate perceptual limit.
    Session 105 — Observation primitive (WHY_OBSERVATION_EXISTS.md §8).

    Written to ObservationLog when SignalType.OBSERVATION_GAP fires.
    Persists across ObservationChannel.drain().

    Import path: from ritam.runtime.v01.types import GapRecord
    (also available via: from ritam.runtime.v01 import GapRecord)

    Protected distinction: records that a category was unknown at observation time.
    Makes no claim about whether the proposed content was valid.
    """
    gap_id: str           # Stable UUID assigned at observation time
    category: str         # The unknown category that was proposed
    content_type: str     # Python type name of proposed content (e.g., "str", "dict")
    source: str           # Source identifier who proposed to the unknown category
    observed_at: str      # ISO-format datetime string of observation

    # Design note: No status field in v1.0. Future: OPEN/RESOLVED/ACKNOWLEDGED lifecycle.
    # gap_id is stable UUID — status column can be added without schema migration.


## 3. ObservationChannel

The substrate's outbound signal bus. Every governance decision, gap detection, and repair event emits a typed signal here. Callers subscribe to stay informed without polling internal state (A-list #7, invariants I5/I8).

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from datetime import datetime


class SignalType(Enum):
    # Admission signals
    ADMITTED          = "admitted"           # Item admitted; carries ProvenanceRecord
    QUARANTINED       = "quarantined"        # Contradiction detected and quarantined
    REJECTED          = "rejected"           # Item rejected by governance
    RETRACTED         = "retracted"          # Item retracted by caller

    # Gap / blindness signals  (A-list #7 — the critical new component for v0.1)
    OBSERVATION_GAP   = "observation_gap"    # Unknown category proposed; substrate has no
                                             # representation for it → this signal, not silence
    REPRESENTATION_LIMIT = "representation_limit"  # Known category but item exceeds the
                                                    # substrate's current representational capacity

    # Repair signals  (A-list #4)
    DECAY_APPLIED     = "decay_applied"      # Item weight reduced by decay mechanism
    QUARANTINE_PURGED = "quarantine_purged"  # Contradiction resolved and purged (future)
    REPAIR_TRIGGERED  = "repair_triggered"   # Explicit repair pathway activated

    # Temporal signals  (Session 103 — Temporal primitive)
    TEMPORAL_ALERT    = "temporal_alert"     # Item age exceeds declared expiry contract;
                                             # does NOT auto-retract — consumer decides

    # Epistemic signals  (Session 104 — Epistemic primitive)
    EPISTEMIC_ALERT   = "epistemic_alert"   # All confidence-tagged items in category are
                                             # below threshold; does NOT auto-retract

    # Note: OBSERVATION_GAP already defined above — Session 105 Observation primitive
    # persists gap records to ObservationLog independently of channel drain.


@dataclass(frozen=True)
class SubstrateSignal:
    signal_type: SignalType
    emitted_at: datetime
    item_id: str | None          # Relevant item, if applicable
    category: str | None         # Relevant category, if applicable
    payload: dict[str, Any]      # Signal-specific detail (structured, not free text)
    source_operation: str        # Which gateway operation triggered this signal


# Type alias for subscriber callbacks
SignalHandler = Callable[[SubstrateSignal], None]


class ObservationChannel:
    """
    Subscribe to typed signals emitted by the substrate.

    Invariants:
    - I5 (Observable Repair Loops): all repair and decay events emit signals.
    - I8 (Contradiction Visibility): all quarantine events emit signals.
    - A-list #7 (Blindness must be observable): unknown/unrepresentable categories MUST emit
      OBSERVATION_GAP or REPRESENTATION_LIMIT — never fall through silently.
    - Signals are ordered (FIFO per emission). Subscribers receive all signals emitted
      after subscription; no backfill of prior signals in v0.1.
    - Subscriber errors MUST NOT suppress signal emission to other subscribers.
    """

    def subscribe(self, handler: SignalHandler) -> str:
        """
        Register a handler to receive all future signals.
        Returns a subscription_id for later unsubscription.
        """
        ...

    def unsubscribe(self, subscription_id: str) -> None:
        """Remove a previously registered handler."""
        ...

    def drain(self) -> list[SubstrateSignal]:
        """
        Pull all buffered signals synchronously (alternative to push subscription).
        Useful for tests and for callers that prefer polling.
        Clears the buffer after return.
        """
        ...
```

### 3.1 Signal Type Reference (GAP-5 fix — Session 100)

Complete list of `SignalType` enum members, their payloads, and implementation status.
A cold builder subscribing to signals must know which types can arrive and what `payload` keys each carries.

| SignalType | emitted by | `item_id` | `category` | `payload` keys | v0.1 status |
|---|---|---|---|---|---|
| `ADMITTED` | `propose()` | ✅ set | ✅ set | `source`, `basis` | ✅ Implemented |
| `QUARANTINED` | `propose()` | ✅ set (incoming item) | ✅ set | `quarantine_id`, `conflict_ids`, `source`, `repair_pathways` | ✅ Implemented |
| `REJECTED` | `propose()` | `None` | ✅ set | `reason`, `source` | ✅ Implemented |
| `RETRACTED` | `retract()` | ✅ set | `None` | `source`, `reason` | ✅ Implemented |
| `OBSERVATION_GAP` | `propose()` | `None` | ✅ set (unknown category) | `category`, `content_type`, `source` | ✅ Implemented |
| `REPRESENTATION_LIMIT` | — | `None` | ✅ set | `category`, `source`, `reason` | 🔲 Reserved (not yet emitted) |
| `DECAY_APPLIED` | decay pass | ✅ set | ✅ set | `old_weight`, `new_weight`, `reason` | 🔲 Reserved (not yet emitted) |
| `QUARANTINE_PURGED` | repair close | ✅ set | ✅ set | `quarantine_id`, `resolution_note` | 🔲 Reserved (not yet emitted) |
| `REPAIR_TRIGGERED` | explicit repair | ✅ set | ✅ set | `repair_id`, `pathway_id` | 🔲 Reserved (not yet emitted) |
| `TEMPORAL_ALERT` | `check_expired()` | ✅ set | ✅ set | `message`, `expires_after_seconds`, `expired_at`, `admitted_at`, `source`, `repair_pathways` | ✅ Implemented (Session 103) |

**Payload key notes:**
- `basis`: string — reason for admission (`"new_item"`, `"idempotent_readmit"`)
- `repair_pathways`: list of pathway_id strings from the generated RepairSuggestion (always 3 in v0.1)
- `content_type`: Python type name of the proposed content (e.g., `"str"`, `"dict"`)
- Reserved signals (`REPRESENTATION_LIMIT`, `DECAY_APPLIED`, `QUARANTINE_PURGED`, `REPAIR_TRIGGERED`) are defined in `SignalType` for forward compatibility but are not emitted in the current implementation. Subscribers will never receive them from v0.1 code.
- `TEMPORAL_ALERT`: emitted by `check_expired()` when item age exceeds declared expiry contract. Protected distinction (§9 WHY_TEMPORAL_EXISTS.md): payload describes age of admission, not validity of content. Message is always "item age exceeds declared contract" — never "expired claim" or "invalid item".

**Subscribing to a specific signal type:**
```python
def on_quarantine(signal: SubstrateSignal) -> None:
    if signal.signal_type != SignalType.QUARANTINED:
        return
    qid = signal.payload["quarantine_id"]
    repair = contradiction_store.get_repair(qid)
    # ... handle repair

channel.subscribe(on_quarantine)
```

---

## 4. Substrate Initialisation

The three interfaces are obtained from a single `Substrate` factory. Callers never instantiate the interfaces directly.

```python
from dataclasses import dataclass


@dataclass
class SubstrateConfig:
    storage_path: str            # Path to the substrate's persistent storage directory
    known_categories: list[str]  # Ontology categories the substrate can represent in v0.1.
                                 # Items in unknown categories → OBSERVATION_GAP signal + REJECTED.
                                 # Each category is either PLURAL or SINGULAR (see §4.1).
    singular_categories: list[str] | None = None
                                 # OPTIONAL. Categories that enforce at-most-one-canonical-content.
                                 # DEFAULT: None → treated as [] → ALL categories are PLURAL.
                                 # Permissive by design: constraints are opt-in, not opt-out.
                                 # Pass only the categories you want to restrict:
                                 #   singular_categories=["active-decision"]
                                 #   → "active-decision" is SINGULAR; everything else is PLURAL.
                                 # WARNING: singular_categories=[] also means all-PLURAL (empty list
                                 # = no singular constraints). Do not confuse with "all singular."
    decay_enabled: bool = True   # Whether decay-as-repair runs on stored items
    decay_interval_seconds: int = 3600  # How often the decay pass runs


class Substrate:
    """
    Entry point. Construct once; share the three interface instances throughout the application.

    Usage:
        substrate = Substrate(SubstrateConfig(
    storage_path="./data",
    known_categories=["claim", "evidence", "question", "canonical-claim"],
    singular_categories=["canonical-claim"],  # at-most-one enforced
))
        gw = substrate.admission_gateway()
        cs = substrate.contradiction_store()
        oc = substrate.observation_channel()
    """

    def __init__(self, config: SubstrateConfig) -> None: ...

    def admission_gateway(self) -> AdmissionGateway: ...
    def contradiction_store(self) -> ContradictionStore: ...
    def observation_channel(self) -> ObservationChannel: ...
```

---

## 4.1 Category Enforcement Modes (v0.2)

All known categories are either **PLURAL** or **SINGULAR**. The enforcement mode determines how the AdmissionGateway handles multiple items in the same category.

| Mode | Behaviour | Default | Use for |
|---|---|---|---|
| **PLURAL** | Multiple items coexist. No conflict detection between items in this category. | Yes — all categories not listed in `singular_categories` | Empirical findings, hypotheses, questions, observations that accumulate |
| **SINGULAR** | At-most-one canonical-content enforced. A new item with different content is QUARANTINED as a contradiction. | No — must be explicitly listed | Canonical claims, authoritative assertions, definitive positions |

**Default enforcement mode:** PLURAL. A category is SINGULAR only if explicitly listed in `singular_categories`. Omitting `singular_categories` (or passing `None` or `[]`) means all categories are PLURAL. This is the permissive default — governance constraints are opt-in. [GAP-3 fix — Session 099]

**Common mistake:** Passing `singular_categories=[]` and expecting all categories to be singular. An empty list means zero singular constraints — all categories remain plural. You must name each singular category explicitly.

**v0.2 category assignments (GovernedNotebook consumer):**

| Category | Mode | Reason |
|---|---|---|
| `empirical-finding` | PLURAL | Multiple non-contradictory findings coexist — different phenomena, different experiments |
| `hypothesis` | PLURAL | Multiple competing hypotheses are expected |
| `question` | PLURAL | Multiple open questions accumulate |
| `method-note` | PLURAL | Multiple method notes coexist |
| `canonical-claim` | SINGULAR | Only one authoritative governing assertion allowed; divergence forces resolution (INSIGHT-116) |

**Governance contract for SINGULAR categories:**
- If the store holds zero items in the category → new item ADMITTED.
- If the store holds one item with *identical* content → new item ADMITTED (idempotent).
- If the store holds one item with *different* content → new item QUARANTINED; both items preserved; `conflict_ids` populated; QUARANTINED signal emitted.

**Why canonical-claim matters (INSIGHT-116):** Making the programme's governing assertion a first-class governed object means the substrate *cannot* silently hold two contradictory foundational claims. Any divergence is surfaced immediately, not discovered retrospectively. This is the governance instrument that INSIGHT-114/115 called for.

---

## 5. Proof-Condition Tests (Outline)

These three tests define what it means for v0.1 to *exist*. All three must pass before v0.1 is declared complete. They call only the public API above — no imports of internal modules.

```python
# TEST A — Compliant admission
result = gw.propose(content="The sky is blue", category="claim", source="test")
assert result.verdict == AdmissionVerdict.ADMITTED
assert result.provenance is not None
assert result.provenance.item_id == result.item_id

# TEST B — Contradiction quarantine (both items preserved)
r1 = gw.propose(content="The meeting is on Tuesday", category="claim", source="alice")
r2 = gw.propose(content="The meeting is on Wednesday", category="claim", source="bob")
assert r1.verdict == AdmissionVerdict.ADMITTED
assert r2.verdict == AdmissionVerdict.QUARANTINED
assert len(r2.conflict_ids) >= 1
records = cs.list_by_category("claim")
assert any(r1.item_id in rec.item_ids for rec in records)  # original preserved
assert any(r2.item_id in rec.item_ids for rec in records)  # conflict preserved

# TEST C — Observation gap (unknown category → typed signal, not silence)
r3 = gw.propose(content="Something unknowable", category="UNKNOWN_CATEGORY_XYZ", source="test")
assert r3.verdict == AdmissionVerdict.REJECTED
signals = oc.drain()
gap_signals = [s for s in signals if s.signal_type == SignalType.OBSERVATION_GAP]
assert len(gap_signals) >= 1
assert gap_signals[0].category == "UNKNOWN_CATEGORY_XYZ"
```

```python
# TEST D — Content validation (v0.2 · OQ-056)
r_none = gw.propose(content=None, category="claim", source="test")
assert r_none.verdict == AdmissionVerdict.REJECTED
assert "content" in r_none.reason.lower()

r_empty = gw.propose(content="   ", category="claim", source="test")
assert r_empty.verdict == AdmissionVerdict.REJECTED
assert "empty" in r_empty.reason.lower() or "whitespace" in r_empty.reason.lower()

# TEST E — canonical-claim singular enforcement (v0.2 · OQ-057)
# Substrate must be initialised with canonical-claim as a singular category.
r_cc1 = gw.propose(content="Governance precedes autonomy.", category="canonical-claim", source="test")
assert r_cc1.verdict == AdmissionVerdict.ADMITTED

r_cc2 = gw.propose(content="Reliability precedes governance.", category="canonical-claim", source="test")
assert r_cc2.verdict == AdmissionVerdict.QUARANTINED
assert r_cc1.item_id in r_cc2.conflict_ids

# Both items must be preserved in the contradiction store.
records = cs.list_by_category("canonical-claim")
assert any(r_cc1.item_id in rec.item_ids for rec in records)
assert any(r_cc2.item_id in rec.item_ids for rec in records)
```

---

## 6. Non-Goals for v0.1

These are explicitly out of scope. Do not implement or design for them.

- **Resolution of contradictions.** Contradictions are preserved, not resolved. `resolved=False` always.
- **Multi-node or distributed operation.** Single-process, single-machine only.
- **Authentication or authorisation.** `source` is a string label, not a verified identity.
- **Query language or search.** No keyword search or semantic retrieval. Category-scoped lookups only.
- **Schema validation of `content`.** Content is `Any`; validation is the caller's responsibility.
- **Streaming or async interfaces.** All methods are synchronous in v0.1.
- **The Temporal primitive as a full component.** Write-time temporal coherence is supported via `temporal_context` on `propose()`; the full TemporalGovernanceLayer is v0.2.
- **Ontology mutation detection.** Known categories are set at initialisation. Category *enforcement mode* (plural vs singular) is configured at initialisation via `singular_categories` and is not mutable at runtime. Adding or removing categories requires a new substrate instance.

---

## 7. Kill Test Baseline (from PHASE1_VIABILITY.md §F)

Alongside v0.1, a **baseline implementation** must be built:
- `ritam.baseline.notebook` — a plain Python dict + SQLite implementation of the Research Notebook with **no AdmissionGateway, no ContradictionStore, no ObservationChannel**.
- The baseline must expose the same notebook-level operations (add observation, query, correct) as the governed version.
- After 4 weeks of real use by Rishi, if behaviour is indistinguishable: the substrate has failed its claim. The kill test must be designed to be honest.

The baseline spec is defined in `runtime/v0.1/BASELINE_SPEC.md` (to be written in Session 079 alongside the first implementation).


---

## Appendix A: Two-Consumer Test (ChatGPT advisory, 2026-06-18)

For each interface, verify it is domain-agnostic — i.e., usable unchanged by at least two different application types. If a method only makes sense for notebooks, the application logic has leaked into the substrate.

| Interface / Method | Governed Research Notebook | Governed Agent | Governed Personal Knowledge Base | Verdict |
|---|---|---|---|---|
| `AdmissionGateway.propose(content, category, source)` | Add a claim/evidence/question | Store an observation or plan step | Add a note or fact | ✅ General — content and category are caller-defined |
| `AdmissionGateway.retract(item_id, source, reason)` | Correct/supersede a claim | Cancel a plan step | Remove a note | ✅ General |
| `ContradictionStore.list_by_category(category)` | List conflicting claims | List conflicting plans | List conflicting facts | ✅ General |
| `ContradictionStore.list_involving(item_id)` | Find all conflicts for an item | Same | Same | ✅ General |
| `ObservationChannel.subscribe(handler)` | Get notified of admission events | Same | Same | ✅ General |
| `SubstrateConfig.known_categories` | ["claim", "evidence", "question"] | ["observation", "plan", "action"] | ["note", "contact", "task"] | ✅ General — caller-defined ontology |
| `SignalType.OBSERVATION_GAP` | Unknown category proposed | Agent proposes unknown action type | Unknown note type | ✅ General |

**Result:** No notebook-specific logic detected in the spec. The substrate is domain-agnostic; the category vocabulary is the only caller-defined coupling, and it is correctly passed at initialisation.

**Boundary rule (to hold throughout implementation):**
> Every feature must answer: "Would a different application (agent, CRM, planner) reuse this unchanged?" If not, it belongs in the notebook application, not in `ritam.runtime.v01`.

---

## Appendix B: Anti-Framework Rules (ChatGPT advisory, 2026-06-18)

Runtime v0.1 is constrained to the following implementation profile. These are not preferences — they are scope guards that keep the implementation focused on proving the epistemic contract rather than building infrastructure.

- **Single-process only.** No multiprocessing, no network calls, no inter-process communication.
- **SQLite for persistence.** No external database, no Redis, no document store.
- **Synchronous only.** No async/await, no threading, no background workers (except the decay pass, which runs synchronously on demand or on a timer trigger — never a daemon thread in v0.1).
- **No agents.** The substrate does not plan, decide, or act autonomously.
- **No embeddings.** Contradiction detection uses exact-match / hash comparison within a category. Semantic similarity is explicitly out of scope.
- **No LLM dependency.** The substrate must function with zero LLM calls. LLMs may sit *above* it; they are not *in* it.
- **No semantic similarity.** Content comparison is structural, not semantic.

Violation of any of these rules in `runtime/v0.1/` requires an explicit ADR.

---

## Appendix C: True Acceptance Criterion (ChatGPT advisory, 2026-06-18)

The milestone for Sessions 079–081 is NOT "AdmissionGateway returns the correct verdict."

The milestone is:

> **"A consumer application can obtain governed admission, contradiction preservation, and blindness surfacing without implementing those behaviours itself."**

This means the proof-condition tests (§5) must be written as a *consumer* script — one that imports only from the public `ritam.runtime.v01` interface, calls the three interfaces, and observes the results. If the test requires importing internal modules, the substrate boundary has been violated.

The Kill Test (§7) runs in parallel: build the baseline alongside v0.1. For every new substrate capability, ask: "Could the dict+SQLite baseline implement this trivially?" If yes, the capability may not belong in the substrate.
