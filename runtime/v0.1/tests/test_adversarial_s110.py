"""
test_adversarial_s110.py — Adversarial Audit of the Repair lifecycle.
Session 110 · Phase 5B · WHY_INTEGRATION_TEST_EXISTS.md §7

Six attacks on the Repair lifecycle and cross-primitive interactions.
Each test records whether the substrate's behaviour is:
  CORRECT   — substrate defends the invariant
  ACCEPTABLE — documented limitation consistent with design principles
  GAP        — failure mode not governed; recorded for Phase 5C remediation

Results summary (Session 110):
  Attack 1 — CORRECT:     Loop-back from VERIFIED blocked by ValueError
  Attack 2 — CORRECT:     False verification (skip EXECUTED) blocked by ValueError
  Attack 3 — ACCEPTABLE:  Abandoned repair is visible; I1 preserved
  Attack 4 — GAP:         Orphaned repair after category removal not blocked
  Attack 5 — CORRECT:     Multiple simultaneous repairs governed independently
  Attack 6 — CORRECT:     Temporal expiry does not corrupt in-flight repair
"""
from __future__ import annotations

import tempfile
import time

import pytest

from ritam.runtime.v01 import Substrate, SubstrateConfig, AdmissionVerdict
from ritam.runtime.v01.types import SignalType


def _make_substrate(tmp_path, singular=None):
    cfg = SubstrateConfig(
        storage_path=str(tmp_path),
        known_categories=["claim"],
        singular_categories=singular if singular is not None else ["claim"],
    )
    return Substrate(cfg)


def _seed_conflict(gw):
    """Admit one item then conflict it; return the repair_id."""
    gw.propose({"val": "first"}, "claim", "src_a")
    r = gw.propose({"val": "second"}, "claim", "src_b")
    assert r.verdict == AdmissionVerdict.QUARANTINED
    return r.repair.quarantine_id


# ---------------------------------------------------------------------------
# Attack 1 — Loop-back from VERIFIED (CORRECT)
# ---------------------------------------------------------------------------

def test_attack_1_no_loop_back_from_verified(tmp_path):
    """
    CORRECT: Once a RepairRecord reaches VERIFIED, no transition is permitted.
    Re-acknowledging a verified repair raises ValueError.
    Protected invariant: VERIFIED is a terminal state — the governance loop
    is closed and cannot be re-opened.
    """
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()

    rid = _seed_conflict(gw)
    gw.acknowledge_repair(rid)
    gw.execute_repair(rid)
    gw.verify_repair(rid)

    # Attack: attempt to loop back
    with pytest.raises(ValueError, match="verified"):
        gw.acknowledge_repair(rid)

    # Also cannot execute or verify again
    with pytest.raises(ValueError):
        gw.execute_repair(rid)

    with pytest.raises(ValueError):
        gw.verify_repair(rid)


# ---------------------------------------------------------------------------
# Attack 2 — False verification: skip EXECUTED (CORRECT)
# ---------------------------------------------------------------------------

def test_attack_2_cannot_verify_without_executing(tmp_path):
    """
    CORRECT: verify_repair() requires status=EXECUTED. Calling it from
    ACKNOWLEDGED raises ValueError.
    Protected invariant: execution must be declared before verification.
    The substrate cannot be fooled into closing a repair loop that was
    never acted upon.
    """
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()

    rid = _seed_conflict(gw)
    gw.acknowledge_repair(rid)

    with pytest.raises(ValueError, match="acknowledged"):
        gw.verify_repair(rid, outcome="Fake — repair was never executed")

    # Status must still be acknowledged, not corrupted
    repairs = gw.list_repairs()
    assert repairs[0].status == "acknowledged", \
        "Failed verify attempt must not corrupt repair status"


def test_attack_2_cannot_verify_from_pending(tmp_path):
    """
    CORRECT: verify_repair() from PENDING (skipping both ACKNOWLEDGED and EXECUTED)
    is also rejected.
    """
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()

    rid = _seed_conflict(gw)

    with pytest.raises(ValueError, match="pending"):
        gw.verify_repair(rid, outcome="Skipping two steps")


# ---------------------------------------------------------------------------
# Attack 3 — Abandoned repair: never acknowledged (ACCEPTABLE)
# ---------------------------------------------------------------------------

def test_attack_3_abandoned_repair_is_visible(tmp_path):
    """
    ACCEPTABLE: An abandoned repair (PENDING, never acted on) persists
    visibly in the repair log.

    Design rationale: forcing acknowledgement would violate I1
    (Governance Before Autonomy) — the substrate governs, it does not act.
    The correct governance response is to make neglect visible, not to
    force action. list_repairs(status='pending') exposes all abandoned repairs.

    This is an ACCEPTABLE limitation, not a gap. Audit tools can surface
    abandoned repairs; humans decide what to do about them.
    """
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()

    _seed_conflict(gw)
    # Deliberately never acknowledge, execute, or verify

    pending = gw.list_repairs(status="pending")
    assert len(pending) == 1, \
        "Abandoned repair must be visible via list_repairs(status='pending')"
    assert pending[0].status == "pending"
    assert pending[0].acknowledged_at if hasattr(pending[0], "acknowledged_at") else True

    all_repairs = gw.list_repairs()
    assert len(all_repairs) == 1, \
        "Abandoned repair must appear in full repair log"


# ---------------------------------------------------------------------------
# Attack 4 — Orphaned repair after category removal (GAP)
# ---------------------------------------------------------------------------

def test_attack_4_gap_orphaned_repair_after_category_removal(tmp_path):
    """
    FIXED (Option B — Session 111, ADR-018, INSIGHT-135).

    Previously documented as GAP-6: remove_category() did not check for
    in-flight repairs, allowing orphaned RepairRecords to proceed without
    any governance signal.

    Fix applied: remove_category() now queries repair_log for PENDING,
    ACKNOWLEDGED, and EXECUTED repairs in the removed category and emits
    REPAIR_ONTOLOGY_CONFLICT for each — before completing the removal.

    Option B (warning flag) semantics:
    - The repair lifecycle is NOT blocked (open-world: removal in progress
      ≠ category never existed).
    - The contradiction IS surfaced as a visible REPAIR_ONTOLOGY_CONFLICT
      signal per I8 (Contradiction Visibility) and I10 (Architectural Honesty).
    - The consumer decides how to handle the orphaned repair context.

    This test now asserts the CORRECT (fixed) behaviour:
    1. remove_category() emits REPAIR_ONTOLOGY_CONFLICT for the in-flight repair
    2. acknowledge_repair() still succeeds (Option B — not blocked)
    3. The conflict signal payload correctly identifies the repair and category
    """
    cfg = SubstrateConfig(
        storage_path=str(tmp_path),
        known_categories=[],
        singular_categories=[],
    )
    s = Substrate(cfg)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    # Set up conflict and repair
    gw.add_category("claim", singular=True, reason="Test category")
    gw.propose({"val": "first"}, "claim", "src_a")
    r = gw.propose({"val": "second"}, "claim", "src_b")
    rid = r.repair.quarantine_id

    pending_before = gw.list_repairs(status="pending")
    assert len(pending_before) == 1

    oc.drain()  # clear prior signals

    # Remove the category while repair is PENDING
    gw.remove_category("claim", reason="Removing category with in-flight repair")

    # FIXED: REPAIR_ONTOLOGY_CONFLICT signal must be emitted (Option B)
    all_signals = oc.drain()
    conflict_signals = [
        sig for sig in all_signals
        if sig.signal_type == SignalType.REPAIR_ONTOLOGY_CONFLICT
    ]
    assert len(conflict_signals) == 1, (
        "FIXED (Option B): remove_category() must emit REPAIR_ONTOLOGY_CONFLICT "
        "for each in-flight repair. Signal not found — GAP-6 fix may be broken."
    )
    c = conflict_signals[0]
    assert c.payload["repair_id"] == rid
    assert c.payload["category"] == "claim"
    assert c.payload["repair_status"] == "pending"
    assert c.payload["conflict_type"] == "ontology_removed_during_active_repair"

    # Option B: repair lifecycle still proceeds (not blocked)
    try:
        gw.acknowledge_repair(rid)
        ack_repairs = gw.list_repairs(status="acknowledged")
        assert len(ack_repairs) == 1
        assert ack_repairs[0].category == "claim"
        lifecycle_unblocked = True
    except ValueError:
        lifecycle_unblocked = False

    assert lifecycle_unblocked, (
        "Option B: acknowledge_repair() must succeed after category removal. "
        "The repair is orphaned but the lifecycle is not blocked — "
        "the conflict was surfaced via REPAIR_ONTOLOGY_CONFLICT signal."
    )


# ---------------------------------------------------------------------------
# Attack 5 — Multiple simultaneous repairs governed independently (CORRECT)
# ---------------------------------------------------------------------------

def test_attack_5_multiple_repairs_governed_independently(tmp_path):
    """
    CORRECT: Multiple simultaneous RepairRecords (from different categories)
    can each be governed through the full lifecycle independently.
    The repair_id is the correct isolation boundary — repairs do not interfere.
    """
    cfg = SubstrateConfig(
        storage_path=str(tmp_path),
        known_categories=[],
        singular_categories=[],
    )
    s = Substrate(cfg)
    gw = s.admission_gateway()

    gw.add_category("conclusion", singular=True)
    gw.add_category("verdict", singular=True)

    # Seed + conflict each category
    gw.propose({"c": "first conclusion"}, "conclusion", "src")
    gw.propose({"v": "first verdict"}, "verdict", "src")
    r1 = gw.propose({"c": "second conclusion"}, "conclusion", "src2")
    r2 = gw.propose({"v": "second verdict"}, "verdict", "src2")

    rid1 = r1.repair.quarantine_id
    rid2 = r2.repair.quarantine_id
    assert rid1 != rid2, "Each conflict must produce a distinct repair_id"

    pending = gw.list_repairs(status="pending")
    assert len(pending) == 2

    # Govern each independently — different pathways, different outcomes
    gw.acknowledge_repair(rid1)
    gw.execute_repair(rid1, pathway_chosen="RETRACT_AND_REPLACE",
                      notes="Conclusion 1 replaced")
    gw.verify_repair(rid1, outcome="Conclusion resolved")

    gw.acknowledge_repair(rid2)
    gw.execute_repair(rid2, pathway_chosen="DOWNGRADE",
                      notes="Verdict 1 downgraded")
    gw.verify_repair(rid2, outcome="Verdict resolved")

    verified = gw.list_repairs(status="verified")
    assert len(verified) == 2

    # Pathways are independently tracked
    pathways = {r.repair_id: r.pathway_chosen for r in verified}
    assert pathways[rid1] == "RETRACT_AND_REPLACE"
    assert pathways[rid2] == "DOWNGRADE"


# ---------------------------------------------------------------------------
# Attack 6 — Temporal expiry does not corrupt in-flight repair (CORRECT)
# ---------------------------------------------------------------------------

def test_attack_6_temporal_expiry_does_not_affect_repair(tmp_path):
    """
    CORRECT: Temporal expiry of a quarantined item does not affect the
    RepairRecord lifecycle. Temporal and Repair are independent governance
    concerns with separate persistence layers (temporal_log vs repair_log).

    A repair can be completed even after the item that triggered it has expired.
    This is correct behaviour: the governance obligation to repair a contradiction
    is not cancelled by the passage of time.
    """
    cfg = SubstrateConfig(
        storage_path=str(tmp_path),
        known_categories=["claim"],
        singular_categories=["claim"],
    )
    s = Substrate(cfg)
    gw = s.admission_gateway()

    # First item expires immediately
    gw.propose({"val": "first"}, "claim", "src_a", expires_after_seconds=0)
    r = gw.propose({"val": "second"}, "claim", "src_b")
    rid = r.repair.quarantine_id

    # Expire the source item while repair is PENDING
    time.sleep(0.05)
    expired = gw.check_expired()
    assert len(expired) >= 1, "First item must expire"

    # Repair must survive the expiry
    pending = gw.list_repairs(status="pending")
    assert len(pending) == 1, \
        "RepairRecord must persist after source item expires"

    # Full lifecycle must complete
    gw.acknowledge_repair(rid)
    gw.execute_repair(rid, pathway_chosen="RETRACT_AND_REPLACE")
    gw.verify_repair(rid, outcome="Resolved despite source item temporal expiry")

    verified = gw.list_repairs(status="verified")
    assert len(verified) == 1
    assert "temporal expiry" in verified[0].outcome
