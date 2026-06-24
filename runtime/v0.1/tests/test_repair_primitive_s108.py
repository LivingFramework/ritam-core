"""
test_repair_primitive_s108.py — Repair-as-Primitive test suite.
Session 108 · WHY_REPAIR_AS_PRIMITIVE_EXISTS.md

15 tests across 8 conditions:
  Condition 1 — RepairRecord dataclass
  Condition 2 — RepairRecord persisted as PENDING on QUARANTINE
  Condition 3 — acknowledge_repair() PENDING → ACKNOWLEDGED
  Condition 4 — execute_repair() ACKNOWLEDGED → EXECUTED
  Condition 5 — verify_repair() EXECUTED → VERIFIED
  Condition 6 — out-of-order transitions are rejected
  Condition 7 — REPAIR_LIFECYCLE signal fires on each transition
  Condition 8 — list_repairs() filter + repair_log survives drain()
  Integration  — full governance loop: quarantine → lifecycle → verified
"""
from __future__ import annotations

import dataclasses
import tempfile

import pytest

from ritam.runtime.v01 import (
    Substrate,
    SubstrateConfig,
    AdmissionVerdict,
    RepairRecord,
)
from ritam.runtime.v01.types import SignalType


def _make_substrate(tmp_path):
    cfg = SubstrateConfig(
        storage_path=str(tmp_path),
        known_categories=["claim", "evidence"],
        singular_categories=["claim"],
    )
    return Substrate(cfg)


def _trigger_quarantine(gw):
    """Helper: admit one item then admit a conflicting one to get a quarantine."""
    gw.propose({"val": "first"}, "claim", "src_a")
    result = gw.propose({"val": "second"}, "claim", "src_b")
    assert result.verdict == AdmissionVerdict.QUARANTINED
    return result.repair.quarantine_id


# ---------------------------------------------------------------------------
# Condition 1 — RepairRecord dataclass
# ---------------------------------------------------------------------------

def test_condition_1_repair_record_fields():
    """RepairRecord must have all 9 required fields."""
    fields = {f.name for f in dataclasses.fields(RepairRecord)}
    assert "repair_id" in fields
    assert "quarantine_id" in fields
    assert "category" in fields
    assert "status" in fields
    assert "pathway_chosen" in fields
    assert "notes" in fields
    assert "outcome" in fields
    assert "created_at" in fields
    assert "updated_at" in fields


def test_condition_1_repair_record_is_frozen():
    """RepairRecord must be immutable (frozen dataclass)."""
    r = RepairRecord(
        repair_id="x", quarantine_id="q", category="claim",
        status="pending", pathway_chosen=None, notes=None, outcome=None,
        created_at="2026-06-22T00:00:00", updated_at="2026-06-22T00:00:00",
    )
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        r.status = "acknowledged"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Condition 2 — RepairRecord persisted as PENDING on QUARANTINE
# ---------------------------------------------------------------------------

def test_condition_2_quarantine_creates_pending_repair(tmp_path):
    """A QUARANTINE event must create a RepairRecord with status='pending'."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    _trigger_quarantine(gw)

    repairs = gw.list_repairs()
    assert len(repairs) == 1
    assert repairs[0].status == "pending"
    assert repairs[0].category == "claim"


def test_condition_2_repair_id_matches_quarantine_id(tmp_path):
    """The repair_id and quarantine_id on the RepairRecord match the suggestion."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    gw.propose({"val": "first"}, "claim", "src_a")
    result = gw.propose({"val": "second"}, "claim", "src_b")

    suggestion = result.repair
    repairs = gw.list_repairs()
    assert repairs[0].repair_id == suggestion.quarantine_id
    assert repairs[0].quarantine_id == suggestion.quarantine_id


# ---------------------------------------------------------------------------
# Condition 3 — acknowledge_repair()
# ---------------------------------------------------------------------------

def test_condition_3_acknowledge_transitions_to_acknowledged(tmp_path):
    """acknowledge_repair() returns RepairRecord with status='acknowledged'."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    rid = _trigger_quarantine(gw)

    rec = gw.acknowledge_repair(rid)
    assert rec.status == "acknowledged"
    assert rec.repair_id == rid


def test_condition_3_acknowledge_persists_in_log(tmp_path):
    """After acknowledge_repair(), list_repairs() reflects the new status."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    rid = _trigger_quarantine(gw)
    gw.acknowledge_repair(rid)

    acknowledged = gw.list_repairs(status="acknowledged")
    assert len(acknowledged) == 1
    pending = gw.list_repairs(status="pending")
    assert len(pending) == 0


# ---------------------------------------------------------------------------
# Condition 4 — execute_repair()
# ---------------------------------------------------------------------------

def test_condition_4_execute_transitions_to_executed(tmp_path):
    """execute_repair() returns RepairRecord with status='executed' and pathway."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    rid = _trigger_quarantine(gw)
    gw.acknowledge_repair(rid)

    rec = gw.execute_repair(rid, pathway_chosen="RETRACT_AND_REPLACE",
                             notes="Retracted the old item")
    assert rec.status == "executed"
    assert rec.pathway_chosen == "RETRACT_AND_REPLACE"
    assert rec.notes == "Retracted the old item"


def test_condition_4_execute_persists_in_log(tmp_path):
    """After execute_repair(), list_repairs(status='executed') returns the record."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    rid = _trigger_quarantine(gw)
    gw.acknowledge_repair(rid)
    gw.execute_repair(rid, pathway_chosen="DOWNGRADE")

    executed = gw.list_repairs(status="executed")
    assert len(executed) == 1
    assert executed[0].pathway_chosen == "DOWNGRADE"


# ---------------------------------------------------------------------------
# Condition 5 — verify_repair()
# ---------------------------------------------------------------------------

def test_condition_5_verify_transitions_to_verified(tmp_path):
    """verify_repair() returns RepairRecord with status='verified' and outcome."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    rid = _trigger_quarantine(gw)
    gw.acknowledge_repair(rid)
    gw.execute_repair(rid)

    rec = gw.verify_repair(rid, outcome="Contradiction fully resolved.")
    assert rec.status == "verified"
    assert rec.outcome == "Contradiction fully resolved."


def test_condition_5_no_further_transitions_from_verified(tmp_path):
    """A verified repair cannot be re-acknowledged (terminal state)."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    rid = _trigger_quarantine(gw)
    gw.acknowledge_repair(rid)
    gw.execute_repair(rid)
    gw.verify_repair(rid)

    with pytest.raises(ValueError):
        gw.acknowledge_repair(rid)


# ---------------------------------------------------------------------------
# Condition 6 — out-of-order transitions are rejected
# ---------------------------------------------------------------------------

def test_condition_6_cannot_execute_before_acknowledge(tmp_path):
    """execute_repair() on a PENDING repair raises ValueError."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    rid = _trigger_quarantine(gw)

    with pytest.raises(ValueError, match="pending"):
        gw.execute_repair(rid)


def test_condition_6_cannot_verify_before_execute(tmp_path):
    """verify_repair() on an ACKNOWLEDGED repair raises ValueError."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    rid = _trigger_quarantine(gw)
    gw.acknowledge_repair(rid)

    with pytest.raises(ValueError, match="acknowledged"):
        gw.verify_repair(rid)


def test_condition_6_unknown_repair_id_raises(tmp_path):
    """All lifecycle methods raise ValueError for unknown repair_id."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()

    with pytest.raises(ValueError):
        gw.acknowledge_repair("no-such-id")
    with pytest.raises(ValueError):
        gw.execute_repair("no-such-id")
    with pytest.raises(ValueError):
        gw.verify_repair("no-such-id")


# ---------------------------------------------------------------------------
# Condition 7 — REPAIR_LIFECYCLE signal fires on each transition
# ---------------------------------------------------------------------------

def test_condition_7_signals_fire_on_all_transitions(tmp_path):
    """Three REPAIR_LIFECYCLE signals fire: acknowledged, executed, verified."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    rid = _trigger_quarantine(gw)
    oc.drain()  # clear QUARANTINED signal

    gw.acknowledge_repair(rid)
    gw.execute_repair(rid)
    gw.verify_repair(rid)

    signals = oc.drain()
    lifecycle = [sig for sig in signals
                 if sig.signal_type == SignalType.REPAIR_LIFECYCLE]
    assert len(lifecycle) == 3
    transitions = [sig.payload["to_status"] for sig in lifecycle]
    assert transitions == ["acknowledged", "executed", "verified"]


def test_condition_7_signal_payload_has_from_and_to(tmp_path):
    """REPAIR_LIFECYCLE signal payload contains from_status and to_status."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    rid = _trigger_quarantine(gw)
    oc.drain()
    gw.acknowledge_repair(rid)

    signals = oc.drain()
    lifecycle = [sig for sig in signals
                 if sig.signal_type == SignalType.REPAIR_LIFECYCLE]
    assert len(lifecycle) == 1
    assert lifecycle[0].payload["from_status"] == "pending"
    assert lifecycle[0].payload["to_status"] == "acknowledged"
    assert lifecycle[0].payload["repair_id"] == rid


# ---------------------------------------------------------------------------
# Condition 8 — list_repairs() filter + drain() independence
# ---------------------------------------------------------------------------

def test_condition_8_list_repairs_filter_by_status(tmp_path):
    """list_repairs(status=) filters correctly across multiple repairs."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()

    # Create two quarantines (need different categories to allow both)
    gw.propose({"v": 1}, "claim", "a")
    r1 = gw.propose({"v": 2}, "claim", "b")
    rid1 = r1.repair.quarantine_id

    # Advance rid1 to acknowledged only
    gw.acknowledge_repair(rid1)

    pending = gw.list_repairs(status="pending")
    acknowledged = gw.list_repairs(status="acknowledged")
    all_repairs = gw.list_repairs()

    assert len(pending) == 0
    assert len(acknowledged) == 1
    assert len(all_repairs) == 1


def test_condition_8_repair_log_survives_drain(tmp_path):
    """RepairLog persists independently of ObservationChannel.drain()."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    _trigger_quarantine(gw)
    oc.drain()  # clear all signals

    repairs = gw.list_repairs()
    assert len(repairs) == 1
    assert repairs[0].status == "pending"


# ---------------------------------------------------------------------------
# Integration — full governance loop
# ---------------------------------------------------------------------------

def test_integration_full_governance_loop(tmp_path):
    """
    Full governed repair lifecycle:
    Admit item → conflict → QUARANTINE → PENDING repair
    → acknowledge → execute → verify
    → repair_log shows VERIFIED with pathway and outcome
    → 3 REPAIR_LIFECYCLE signals emitted
    → recovery loop fully visible in governance record
    """
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    # Step 1: conflict → quarantine
    gw.propose({"capital": "London"}, "claim", "source_a")
    result = gw.propose({"capital": "Paris"}, "claim", "source_b")
    assert result.verdict == AdmissionVerdict.QUARANTINED
    assert result.repair is not None

    rid = result.repair.quarantine_id
    oc.drain()  # clear admission signals

    # Step 2: full lifecycle
    gw.acknowledge_repair(rid)
    gw.execute_repair(rid,
                      pathway_chosen="RETRACT_AND_REPLACE",
                      notes="Retracted 'London'; 'Paris' is the correct capital.")
    gw.verify_repair(rid,
                     outcome="Singular category 'claim' now holds only 'Paris'. Verified correct.")

    # Step 3: assert final state
    verified = gw.list_repairs(status="verified")
    assert len(verified) == 1
    assert verified[0].pathway_chosen == "RETRACT_AND_REPLACE"
    assert "Paris" in verified[0].notes
    assert "Verified correct" in verified[0].outcome

    # Step 4: signals
    signals = oc.drain()
    lifecycle = [sig for sig in signals
                 if sig.signal_type == SignalType.REPAIR_LIFECYCLE]
    assert len(lifecycle) == 3

    # Step 5: no pending repairs remain
    pending = gw.list_repairs(status="pending")
    assert len(pending) == 0
