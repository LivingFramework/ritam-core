"""
ritam.runtime.v01.types
Public types shared across all v0.1 interfaces.
Session 079. No LLM, no embeddings, no async, no agents (Appendix B).
Session 094: Added RepairSuggestion, ResolutionPathway (C2 Repair — ADR-016).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# AdmissionGateway types
# ---------------------------------------------------------------------------

class AdmissionVerdict(Enum):
    ADMITTED    = "admitted"
    QUARANTINED = "quarantined"
    REJECTED    = "rejected"


@dataclass(frozen=True)
class ProvenanceRecord:
    item_id: str
    source: str
    admitted_at: datetime
    basis: str


@dataclass(frozen=True)
class ResolutionPathway:
    """
    A named, actionable resolution for a governance conflict.
    Session 094 — C2 Repair (ADR-016).

    pathway_id:       machine-readable identifier for the pathway
    description:      plain-language: what this pathway does and when to use it
    action_required:  concrete steps the consumer/human must take to execute it
    """
    pathway_id: str
    description: str
    action_required: str


@dataclass(frozen=True)
class RepairSuggestion:
    """
    Structured repair output produced by AdmissionGateway on every QUARANTINED event.
    Session 094 — C2 Repair (ADR-016). Implements I5 (Observable Repair Loops).

    The substrate proposes; the human/consumer decides.
    No automated resolution is performed.

    Fields:
        quarantine_id:        links this suggestion to its ContradictionStore record
        category:             the singular category that generated the conflict
        rule_triggered:       human-readable description of which governance rule fired
        incoming_content:     the content that was just rejected (new, quarantined item)
        incoming_source:      source identifier of the incoming item
        existing_items:       list of dicts — each has item_id, content, source for
                              every admitted item that conflicts with the incoming item
        resolution_pathways:  ordered list of actionable options; pick one and execute
        generated_at:         timestamp when this suggestion was produced
    """
    quarantine_id: str
    category: str
    rule_triggered: str
    incoming_content: Any
    incoming_source: str
    existing_items: list[dict]
    resolution_pathways: list[ResolutionPathway]
    generated_at: datetime


@dataclass(frozen=True)
class AdmissionResult:
    verdict: AdmissionVerdict
    item_id: str | None
    provenance: ProvenanceRecord | None
    reason: str
    conflict_ids: list[str]
    repair: RepairSuggestion | None = None
    # repair is populated when verdict == QUARANTINED (Session 094, ADR-016 C2)


@dataclass(frozen=True)
class AdmissionRecord:
    """
    A single admitted (non-retracted) item returned by AdmissionGateway.list_admitted().
    Session 100 — GAP-5 fix (ADR-017). Closes the public read-by-category gap.
    Session 103 — Temporal fields added (expires_after_seconds, expired_at).

    Fields:
        item_id:               stable identifier assigned at admission
        category:              ontology category of this item
        content:               the admitted content value
        source:                source identifier who proposed this item
        admitted_at:           ISO-format datetime string of admission
        expires_after_seconds: optional expiry contract declared at proposal time
        expired_at:            ISO-format datetime when this item expires (admitted_at + contract)
    """
    item_id: str
    category: str
    content: Any
    source: str
    admitted_at: str               # ISO format — use datetime.fromisoformat() to parse
    expires_after_seconds: int | None = None   # None = no expiry contract
    expired_at: str | None = None              # None = no expiry contract
    confidence: float | None = None            # None = untagged (Session 104 — Epistemic primitive)
                                               # Range: 0.0–1.0; declared by proposer, not computed
    batch_id: str | None = None                # None = admitted via plain propose() (Session 106)
                                               # Non-None = admitted as part of a propose_batch() call
                                               # Coordination lineage: preserves arrival-togetherness



@dataclass(frozen=True)
class GapRecord:
    """
    A persistent record of a substrate perceptual limit.
    Session 105 — Observation primitive (WHY_OBSERVATION_EXISTS.md §8).

    Written to ObservationLog when SignalType.OBSERVATION_GAP fires.
    Persists across ObservationChannel.drain() — draining the signal bus
    does not remove gap records from the substrate.

    Protected distinction: records that a category was unknown at a given
    time. Makes no claim about whether the proposed content was valid or
    whether the category should exist.

    Fields:
        gap_id:       stable identifier assigned at observation time
        category:     the unknown category that was proposed
        content_type: Python type name of the proposed content (e.g., "str")
        source:       source identifier who proposed to the unknown category
        observed_at:  ISO-format datetime string of observation
    """
    gap_id: str
    category: str
    content_type: str
    source: str
    observed_at: str  # ISO format



# ---------------------------------------------------------------------------
# Coordination primitive types (Session 106)
# WHY_COORDINATION_EXISTS.md §8
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BatchProposal:
    """
    A single proposal within a propose_batch() call.
    Session 106 — Coordination primitive.

    Mirrors the parameters of propose() but carries no batch_id itself —
    the batch_id is assigned by propose_batch() and written to the resulting
    AdmissionRecord.

    Fields:
        content:               proposed content value
        category:              ontology category to admit into
        source:                source identifier proposing this item
        confidence:            optional epistemic confidence (0.0–1.0)
        expires_after_seconds: optional temporal expiry contract
    """
    content: Any
    category: str
    source: str
    confidence: float | None = None
    expires_after_seconds: int | None = None


@dataclass(frozen=True)
class BatchResult:
    """
    Result of a propose_batch() call.
    Session 106 — Coordination primitive.

    Fields:
        batch_id:               stable UUID for this batch
        results:                one AdmissionResult per BatchProposal (same order)
        coordination_conflicts: list of conflict descriptors; empty if no intra-batch
                                conflicts detected. Each entry: {"indices": [i, j], "category": str}
                                where i < j are the conflicting proposal indices.
    """
    batch_id: str
    results: list  # list[AdmissionResult] — avoid circular import
    coordination_conflicts: list  # list[dict] with keys "indices" and "category"


@dataclass(frozen=True)
class CoordinationRecord:
    """
    A persistent record of a governance-significant coordination event.
    Session 106 — Coordination primitive (WHY_COORDINATION_EXISTS.md §7).

    Written to CoordinationLog ONLY when COORDINATION_CONFLICT fires.
    Clean batches leave no trace.

    Persists independently of ObservationChannel.drain().

    Design decision (v1.0.6): batch coherence is NOT guaranteed. Signal-and-continue
    is used. This record documents that a conflict was detected and governance
    visibility was provided; it does not document resolution.

    Fields:
        record_id:   stable UUID for this coordination record
        batch_id:    the batch in which the conflict occurred
        category:    the singular category where the intra-batch conflict was detected
        indices:     JSON-encoded list [i, j] of conflicting proposal positions
        observed_at: ISO-format datetime string
    """
    record_id: str
    batch_id: str
    category: str
    indices: str   # JSON-encoded e.g. "[0, 2]" — use json.loads() to parse
    observed_at: str  # ISO format


@dataclass(frozen=True)
class OntologyRecord:
    """
    A persistent record of a governed category mutation.
    Session 107 — Ontology primitive (WHY_ONTOLOGY_EXISTS.md §6).

    Written to OntologyLog on every add_category() or remove_category() call.
    Persists independently of ObservationChannel.drain().

    Protected distinction: category existence != category validity.
    Adding a category means the substrate can now receive and govern items
    of that kind. It makes no claim about the reliability or importance of
    those items. That is Epistemic's and Temporal's concern.

    Fields:
        record_id:   stable UUID for this ontology record
        operation:   "add" or "remove"
        category:    the category name being added or removed
        singular:    True if the category enforces at-most-one admission;
                     None for remove operations (property no longer applies)
        reason:      optional caller-supplied provenance string — answers
                     "why was this category added/removed?"
        mutated_at:  ISO-format datetime string
    """
    record_id: str
    operation: str    # "add" | "remove"
    category: str
    singular: "bool | None"   # None for remove operations
    reason: "str | None"      # optional provenance string
    mutated_at: str           # ISO format


# ---------------------------------------------------------------------------
# ObservationChannel types
# ---------------------------------------------------------------------------

class SignalType(Enum):
    ADMITTED             = "admitted"
    QUARANTINED          = "quarantined"
    REJECTED             = "rejected"
    RETRACTED            = "retracted"
    OBSERVATION_GAP      = "observation_gap"
    REPRESENTATION_LIMIT = "representation_limit"
    DECAY_APPLIED        = "decay_applied"
    QUARANTINE_PURGED    = "quarantine_purged"
    REPAIR_TRIGGERED     = "repair_triggered"
    TEMPORAL_ALERT       = "temporal_alert"
    # Session 103 — Temporal primitive. Emitted when an item's age exceeds
    # its declared expiry contract. Does NOT trigger retraction — the substrate
    # signals; the consumer decides.
    EPISTEMIC_ALERT      = "epistemic_alert"
    # Session 104 — Epistemic primitive. Emitted when all tagged items in a
    # category fall below the declared confidence threshold. Does NOT retract.
    # Protected distinction: describes declared confidence, not truth or validity.
    COORDINATION_CONFLICT = "coordination_conflict"
    # Session 106 — Coordination primitive. Emitted when two proposals in the
    # same propose_batch() call conflict on a singular category. Signal-and-
    # continue: batch is not atomic; admission order != cognitive priority.
    ONTOLOGY_MUTATION     = "ontology_mutation"
    # Session 107 — Ontology primitive. Emitted when a category is added to or
    # removed from the substrate's known vocabulary. Signal-and-continue:
    # pending admissions are not held. Protected distinction: category existence
    # != category validity. Provenance recorded in OntologyRecord.
    REPAIR_LIFECYCLE      = "repair_lifecycle"
    # Session 108 — Repair-as-Primitive. Emitted on every RepairRecord state
    # transition: PENDING→ACKNOWLEDGED, ACKNOWLEDGED→EXECUTED, EXECUTED→VERIFIED.
    # Protected distinction: generating a repair ≠ acknowledging it ≠ executing
    # it ≠ verifying the outcome. Each transition is a distinct governance event.
    # REPAIR_TRIGGERED (existing) fires on creation; REPAIR_LIFECYCLE fires on
    # all subsequent transitions.
    REPAIR_ONTOLOGY_CONFLICT = "repair_ontology_conflict"
    # Session 111 — GAP-6 remediation (Option B, ADR-018, INSIGHT-135).
    # Emitted by remove_category() for each in-flight repair (PENDING, ACKNOWLEDGED,
    # or EXECUTED) whose category is being removed. Signal-and-continue: the repair
    # lifecycle is NOT blocked. The ambiguity is surfaced as a visible event per
    # I8 (Contradiction Visibility) and I10 (Architectural Honesty).
    # Open-world semantics: "category removal in progress" ≠ "category never existed".
    # Protected distinction: ontology mutation ≠ repair invalidation.
    # The consumer decides how to handle the orphaned repair context.


@dataclass(frozen=True)
class RepairRecord:
    """
    A governed lifecycle entity tracking the state of a repair suggestion.
    Session 108 — Repair-as-Primitive (WHY_REPAIR_AS_PRIMITIVE_EXISTS.md §6).

    Persisted to repair_log when a RepairSuggestion is generated (status=PENDING).
    Updated in-place on each lifecycle transition; one row per repair.

    Protected distinction: RepairSuggestion = the structured proposal (what is wrong,
    what the options are). RepairRecord = the governance entity (what lifecycle state
    the repair is in, what was done about it).

    Lifecycle: PENDING → ACKNOWLEDGED → EXECUTED → VERIFIED (strict order).
    Transitions are declarations, not automated actions. The substrate records
    what the caller claims to have done; it does not act autonomously (I1).

    Fields:
        repair_id:       stable UUID — links to the originating RepairSuggestion
        quarantine_id:   links to ContradictionStore record
        category:        singular category that triggered the repair
        status:          current lifecycle state (pending|acknowledged|executed|verified)
        pathway_chosen:  pathway_id from ResolutionPathway — set on execute_repair()
        notes:           caller-supplied context — set on execute_repair()
        outcome:         caller-supplied outcome description — set on verify_repair()
        created_at:      ISO timestamp — when the repair was generated
        updated_at:      ISO timestamp — last lifecycle transition
    """
    repair_id: str
    quarantine_id: str
    category: str
    status: str           # "pending" | "acknowledged" | "executed" | "verified"
    pathway_chosen: "str | None"
    notes: "str | None"
    outcome: "str | None"
    created_at: str       # ISO format
    updated_at: str       # ISO format


@dataclass(frozen=True)
class SubstrateSignal:
    signal_type: SignalType
    emitted_at: datetime
    item_id: str | None
    category: str | None
    payload: dict[str, Any]
    source_operation: str


# ---------------------------------------------------------------------------
# ContradictionStore types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ContradictionRecord:
    quarantine_id: str
    item_ids: list[str]
    contents: list[Any]
    categories: list[str]
    sources: list[str]
    quarantined_at: datetime
    reason: str
    resolved: bool = False
    resolution_note: str | None = None
    # resolution_note populated when mark_resolved() is called (Session 094)


# ---------------------------------------------------------------------------
# SubstrateConfig
# ---------------------------------------------------------------------------

@dataclass
class SubstrateConfig:
    storage_path: str
    known_categories: list[str]
    decay_enabled: bool = True
    decay_interval_seconds: int = 3600
    singular_categories: list[str] = None  # type: ignore[assignment]
    # Categories listed here enforce at-most-one: a second admission attempt
    # in the same category triggers QUARANTINE + RepairSuggestion.
    # Categories NOT listed here are plural: multiple entries coexist freely.
    # Examples of singular: "canonical-claim", "current-goal", "active-decision".
    # Examples of plural:   "hypothesis", "observation", "evidence".
    # Default None = empty list (all categories are plural by default).

    def __post_init__(self) -> None:
        if self.singular_categories is None:
            self.singular_categories = []
