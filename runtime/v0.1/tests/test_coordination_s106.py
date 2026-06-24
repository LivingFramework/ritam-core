"""
test_coordination_s106.py
Proves all 8 executable conditions from WHY_COORDINATION_EXISTS.md §8.
Session 106 — Coordination primitive.

Condition summary:
  1. BatchProposal dataclass exists with: content, category, source, confidence, expires_after_seconds
  2. BatchResult dataclass exists with: batch_id, results, coordination_conflicts
  3. gw.propose_batch(proposals) processes all proposals and returns BatchResult
  4. Clean batch (no singular conflicts) → coordination_conflicts empty; proposals processed normally
  5. Intra-batch singular conflict → COORDINATION_CONFLICT emitted with batch_id + conflicting indices
  6. Conflicting batch still processed in full (signal-and-continue; batch coherence NOT guaranteed)
  7. CoordinationRecord persisted on conflict; list_coordination_conflicts() returns it; survives drain()
  8. Integration: 3-proposal batch where [0,2] conflict; P1 admitted; P0 admitted; P2 quarantined;
     CoordinationRecord persisted; list_coordination_conflicts() returns 1 record

Protected distinction (§9): admission order ≠ cognitive priority.
"""
import dataclasses
import json
import tempfile
from pathlib import Path

import pytest

from ritam.runtime.v01 import (
    Substrate,
    SubstrateConfig,
    AdmissionVerdict,
    BatchProposal,
    BatchResult,
    CoordinationRecord,
)
from ritam.runtime.v01.types import SignalType


def _make_substrate(tmp_path):
    cfg = SubstrateConfig(
        storage_path=str(tmp_path / "test.db"),
        known_categories=["claim", "evidence", "hypothesis"],
        singular_categories=["claim", "hypothesis"],
    )
    return Substrate(cfg)


# ---------------------------------------------------------------------------
# Condition 1 — BatchProposal dataclass
# ---------------------------------------------------------------------------

def test_condition_1_batch_proposal_fields():
    """BatchProposal must have all 5 required fields."""
    fields = {f.name for f in dataclasses.fields(BatchProposal)}
    assert "content" in fields
    assert "category" in fields
    assert "source" in fields
    assert "confidence" in fields
    assert "expires_after_seconds" in fields


def test_condition_1_batch_proposal_optional_defaults():
    """BatchProposal optional fields default to None."""
    p = BatchProposal(content="x", category="claim", source="s")
    assert p.confidence is None
    assert p.expires_after_seconds is None


# ---------------------------------------------------------------------------
# Condition 2 — BatchResult dataclass
# ---------------------------------------------------------------------------

def test_condition_2_batch_result_fields():
    """BatchResult must have batch_id, results, coordination_conflicts."""
    fields = {f.name for f in dataclasses.fields(BatchResult)}
    assert "batch_id" in fields
    assert "results" in fields
    assert "coordination_conflicts" in fields


def test_condition_2_batch_result_is_frozen():
    """BatchResult must be immutable."""
    br = BatchResult(batch_id="id", results=[], coordination_conflicts=[])
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        br.batch_id = "mutated"  # type: ignore


# ---------------------------------------------------------------------------
# Condition 3 — propose_batch() returns BatchResult with one result per proposal
# ---------------------------------------------------------------------------

def test_condition_3_propose_batch_returns_batch_result(tmp_path):
    """propose_batch() returns a BatchResult with one AdmissionResult per proposal."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    proposals = [
        BatchProposal(content="claim A", category="claim", source="s"),
        BatchProposal(content="evidence B", category="evidence", source="s"),
    ]
    result = gw.propose_batch(proposals)

    assert isinstance(result, BatchResult)
    assert result.batch_id is not None
    assert len(result.results) == 2


def test_condition_3_batch_id_is_stable_per_batch(tmp_path):
    """All results in a batch share the same batch_id."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    proposals = [
        BatchProposal(content="A", category="evidence", source="s"),
        BatchProposal(content="B", category="evidence", source="s"),
    ]
    result = gw.propose_batch(proposals)
    assert result.batch_id is not None and len(result.batch_id) > 0

    # Two separate batches get different batch_ids
    result2 = gw.propose_batch([BatchProposal(content="C", category="evidence", source="s")])
    assert result.batch_id != result2.batch_id


# ---------------------------------------------------------------------------
# Condition 4 — Clean batch: no coordination_conflicts; proposals admitted normally
# ---------------------------------------------------------------------------

def test_condition_4_clean_batch_no_conflicts(tmp_path):
    """A batch with no singular-category conflicts has empty coordination_conflicts."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    proposals = [
        BatchProposal(content="claim X", category="claim", source="s"),
        BatchProposal(content="evidence Y", category="evidence", source="s"),
    ]
    result = gw.propose_batch(proposals)
    assert result.coordination_conflicts == []
    assert result.results[0].verdict == AdmissionVerdict.ADMITTED
    assert result.results[1].verdict == AdmissionVerdict.ADMITTED


def test_condition_4_plural_category_same_batch_not_a_conflict(tmp_path):
    """Multiple proposals to a plural category in same batch are not a conflict."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    proposals = [
        BatchProposal(content="evidence 1", category="evidence", source="s"),
        BatchProposal(content="evidence 2", category="evidence", source="s"),
    ]
    result = gw.propose_batch(proposals)
    assert result.coordination_conflicts == []
    assert all(r.verdict == AdmissionVerdict.ADMITTED for r in result.results)


def test_condition_4_batch_id_on_admitted_items(tmp_path):
    """Admitted items from a batch carry the batch_id (coordination lineage)."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    proposals = [BatchProposal(content="claim Q", category="claim", source="s")]
    result = gw.propose_batch(proposals)
    batch_id = result.batch_id

    admitted = gw.list_admitted("claim")
    assert len(admitted) == 1
    assert admitted[0].batch_id == batch_id


# ---------------------------------------------------------------------------
# Condition 5 — Intra-batch singular conflict → COORDINATION_CONFLICT signal
# ---------------------------------------------------------------------------

def test_condition_5_coordination_conflict_signal_emitted(tmp_path):
    """Two conflicting singular-category proposals in same batch → COORDINATION_CONFLICT."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    proposals = [
        BatchProposal(content="claim version A", category="claim", source="src-a"),
        BatchProposal(content="claim version B", category="claim", source="src-b"),
    ]
    result = gw.propose_batch(proposals)

    signals = ch.drain()
    coord_signals = [s for s in signals if s.signal_type == SignalType.COORDINATION_CONFLICT]
    assert len(coord_signals) == 1
    sig = coord_signals[0]
    assert sig.payload["batch_id"] == result.batch_id
    assert sig.payload["conflicting_indices"] == [0, 1]
    assert sig.payload["category"] == "claim"


def test_condition_5_conflict_recorded_in_batch_result(tmp_path):
    """coordination_conflicts in BatchResult records conflicting pair."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    proposals = [
        BatchProposal(content="hypothesis A", category="hypothesis", source="s"),
        BatchProposal(content="hypothesis B", category="hypothesis", source="s"),
    ]
    result = gw.propose_batch(proposals)

    assert len(result.coordination_conflicts) == 1
    conflict = result.coordination_conflicts[0]
    assert conflict["indices"] == [0, 1]
    assert conflict["category"] == "hypothesis"


# ---------------------------------------------------------------------------
# Condition 6 — Signal-and-continue: batch processed in full despite conflict
# ---------------------------------------------------------------------------

def test_condition_6_signal_and_continue_all_results_returned(tmp_path):
    """Even when conflict detected, all proposals receive an AdmissionResult."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    proposals = [
        BatchProposal(content="claim v1", category="claim", source="s"),
        BatchProposal(content="evidence E", category="evidence", source="s"),
        BatchProposal(content="claim v2", category="claim", source="s"),
    ]
    result = gw.propose_batch(proposals)

    assert len(result.results) == 3  # All proposals get a result

    # Protected distinction: P0 admitted first (index artifact, not priority claim)
    assert result.results[0].verdict == AdmissionVerdict.ADMITTED
    # P1 (evidence, plural) admitted normally
    assert result.results[1].verdict == AdmissionVerdict.ADMITTED
    # P2 quarantined (contradiction with P0 — processing artifact)
    assert result.results[2].verdict in (
        AdmissionVerdict.QUARANTINED, AdmissionVerdict.REJECTED
    )


def test_condition_6_batch_coherence_not_guaranteed(tmp_path):
    """
    Protected distinction: admission order ≠ cognitive priority.
    P0 wins because it is at index 0, not because it is more valid.
    Both proposals receive explicit AdmissionResult entries.
    """
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    proposals = [
        BatchProposal(content="first-in-batch", category="hypothesis", source="src-a"),
        BatchProposal(content="second-in-batch", category="hypothesis", source="src-b"),
    ]
    result = gw.propose_batch(proposals)

    # P0 admitted (index 0 = first processed)
    assert result.results[0].verdict == AdmissionVerdict.ADMITTED
    # P1 not admitted (contradiction with P0)
    assert result.results[1].verdict != AdmissionVerdict.ADMITTED
    # Conflict is visible
    assert len(result.coordination_conflicts) == 1


# ---------------------------------------------------------------------------
# Condition 7 — CoordinationRecord persisted; survives drain()
# ---------------------------------------------------------------------------

def test_condition_7_coordination_record_persisted(tmp_path):
    """COORDINATION_CONFLICT persists a CoordinationRecord to CoordinationLog."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    proposals = [
        BatchProposal(content="claim alpha", category="claim", source="s"),
        BatchProposal(content="claim beta", category="claim", source="s"),
    ]
    result = gw.propose_batch(proposals)

    records = gw.list_coordination_conflicts()
    assert len(records) == 1
    rec = records[0]
    assert rec.batch_id == result.batch_id
    assert rec.category == "claim"
    assert json.loads(rec.indices) == [0, 1]


def test_condition_7_record_survives_drain(tmp_path):
    """CoordinationRecord persists after channel drain — independent of signal bus."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    proposals = [
        BatchProposal(content="hyp X", category="hypothesis", source="s"),
        BatchProposal(content="hyp Y", category="hypothesis", source="s"),
    ]
    gw.propose_batch(proposals)

    # Drain the channel
    ch.drain()
    ch.drain()  # Second drain — channel empty

    # Record still in CoordinationLog
    records = gw.list_coordination_conflicts()
    assert len(records) == 1, "CoordinationRecord must persist after drain"


def test_condition_7_clean_batch_no_record(tmp_path):
    """Clean batches leave no CoordinationLog entry (conflict-only persistence)."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    proposals = [
        BatchProposal(content="only claim", category="claim", source="s"),
        BatchProposal(content="evidence", category="evidence", source="s"),
    ]
    gw.propose_batch(proposals)

    records = gw.list_coordination_conflicts()
    assert records == []


# ---------------------------------------------------------------------------
# Condition 8 — Full integration test
# ---------------------------------------------------------------------------

def test_condition_8_full_integration(tmp_path):
    """
    3-proposal batch: P0 (claim A), P1 (evidence E), P2 (claim B).
    P0 and P2 conflict on singular category "claim".

    Assert: COORDINATION_CONFLICT emitted with indices [0, 2].
    Assert: P1 (plural evidence) admitted.
    Assert: P0 admitted (first to singular category).
    Assert: P2 quarantined or rejected (contradiction with P0).
    Assert: CoordinationRecord persisted.
    Assert: list_coordination_conflicts() returns 1 record with correct category.
    Assert: admitted items from batch carry batch_id (lineage preserved).
    Assert: admission order ≠ cognitive priority (documented, not resolved).
    """
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    proposals = [
        BatchProposal(content="claim version A", category="claim", source="src-claim-a"),
        BatchProposal(content="evidence E", category="evidence", source="src-evidence"),
        BatchProposal(content="claim version B", category="claim", source="src-claim-b"),
    ]
    result = gw.propose_batch(proposals)
    batch_id = result.batch_id

    # COORDINATION_CONFLICT signal emitted before admission
    signals = ch.drain()
    coord_signals = [s for s in signals if s.signal_type == SignalType.COORDINATION_CONFLICT]
    assert len(coord_signals) == 1
    assert coord_signals[0].payload["conflicting_indices"] == [0, 2]
    assert coord_signals[0].payload["category"] == "claim"

    # P1 (evidence, plural) admitted
    assert result.results[1].verdict == AdmissionVerdict.ADMITTED

    # P0 (claim A, index 0) admitted
    assert result.results[0].verdict == AdmissionVerdict.ADMITTED

    # P2 (claim B, index 2) not admitted (coordination artifact — not priority judgement)
    assert result.results[2].verdict != AdmissionVerdict.ADMITTED

    # CoordinationRecord persisted
    coord_records = gw.list_coordination_conflicts()
    assert len(coord_records) == 1
    assert coord_records[0].batch_id == batch_id
    assert coord_records[0].category == "claim"
    assert json.loads(coord_records[0].indices) == [0, 2]

    # Batch lineage preserved on admitted items
    admitted_claims = gw.list_admitted("claim")
    assert len(admitted_claims) == 1
    assert admitted_claims[0].batch_id == batch_id

    admitted_evidence = gw.list_admitted("evidence")
    assert len(admitted_evidence) == 1
    assert admitted_evidence[0].batch_id == batch_id
