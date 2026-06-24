"""
GAP-6 Remediation Tests — Session 111
======================================
Tests for the Option B (warning flag) fix for GAP-6:
  remove_category() now emits REPAIR_ONTOLOGY_CONFLICT for each in-flight
  repair referencing the removed category. The repair lifecycle is NOT blocked.

Design rationale (INSIGHT-135, ADR-018):
  Open/closed world vocabulary: "category removal in progress" ≠ "category
  never existed". Option A (strict block) would collapse this ambiguity
  silently. Option B (warning flag) surfaces it as a visible contradiction
  event per I8 (Contradiction Visibility) and I10 (Architectural Honesty).

Governance gate principle (INSIGHT-136):
  Governance gates must fire on context mutation, not only on event admission.
  A repair admitted under ontological context C must generate a visible event
  when C is mutated. This is the first implementation of that principle.

Seven tests:
  1. remove_category() with a PENDING in-flight repair → emits conflict signal
  2. remove_category() with ACKNOWLEDGED in-flight repair → emits conflict signal
  3. remove_category() with EXECUTED in-flight repair → emits conflict signal
  4. remove_category() with NO in-flight repairs → emits NO conflict signal
  5. remove_category() with VERIFIED repair (closed) → emits NO conflict signal
     (verified = lifecycle complete, repair is no longer "in-flight")
  6. Full lifecycle: category removed mid-repair, conflict signaled, repair
     still completes — Option B allows continuation (not a block)
  7. Multiple in-flight repairs: one conflict signal emitted per repair
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from ritam.runtime.v01.substrate import Substrate, SubstrateConfig
from ritam.runtime.v01.types import SignalType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_substrate(tmp_path):
    cfg = SubstrateConfig(
        storage_path=str(tmp_path),
        known_categories=[],
        singular_categories=[],
    )
    return Substrate(cfg)


def _conflict_signals(oc):
    """Drain and return only REPAIR_ONTOLOGY_CONFLICT signals."""
    return [
        sig for sig in oc.drain()
        if sig.signal_type == SignalType.REPAIR_ONTOLOGY_CONFLICT
    ]


# ---------------------------------------------------------------------------
# Test 1 — PENDING repair → conflict signal emitted
# ---------------------------------------------------------------------------

def test_gap6_pending_repair_emits_conflict_signal(tmp_path):
    """
    remove_category() with a PENDING in-flight repair emits
    REPAIR_ONTOLOGY_CONFLICT for that repair.
    """
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    gw.add_category("claim", singular=True)
    gw.propose({"val": "a"}, "claim", "src_a")
    r = gw.propose({"val": "b"}, "claim", "src_b")
    repair_id = r.repair.quarantine_id

    pending = gw.list_repairs(status="pending")
    assert len(pending) == 1

    oc.drain()  # clear prior signals

    gw.remove_category("claim", reason="retiring claim category")

    conflicts = _conflict_signals(oc)
    assert len(conflicts) == 1, (
        "Expected exactly 1 REPAIR_ONTOLOGY_CONFLICT signal for the pending repair"
    )
    c = conflicts[0]
    assert c.payload["repair_id"] == repair_id
    assert c.payload["repair_status"] == "pending"
    assert c.payload["category"] == "claim"
    assert c.payload["conflict_type"] == "ontology_removed_during_active_repair"


# ---------------------------------------------------------------------------
# Test 2 — ACKNOWLEDGED repair → conflict signal emitted
# ---------------------------------------------------------------------------

def test_gap6_acknowledged_repair_emits_conflict_signal(tmp_path):
    """
    remove_category() with an ACKNOWLEDGED in-flight repair emits
    REPAIR_ONTOLOGY_CONFLICT for that repair.
    """
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    gw.add_category("fact", singular=True)
    gw.propose({"val": "x"}, "fact", "src_x")
    r = gw.propose({"val": "y"}, "fact", "src_y")
    repair_id = r.repair.quarantine_id

    gw.acknowledge_repair(repair_id)
    assert gw.list_repairs(status="acknowledged")[0].status == "acknowledged"

    oc.drain()

    gw.remove_category("fact", reason="fact retired")

    conflicts = _conflict_signals(oc)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.payload["repair_id"] == repair_id
    assert c.payload["repair_status"] == "acknowledged"
    assert c.payload["category"] == "fact"


# ---------------------------------------------------------------------------
# Test 3 — EXECUTED repair → conflict signal emitted
# ---------------------------------------------------------------------------

def test_gap6_executed_repair_emits_conflict_signal(tmp_path):
    """
    remove_category() with an EXECUTED (not yet verified) in-flight repair
    emits REPAIR_ONTOLOGY_CONFLICT. EXECUTED is still "in-flight" because
    the lifecycle is not yet closed.
    """
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    gw.add_category("bio", singular=True)
    gw.propose({"val": "1"}, "bio", "src_1")
    r = gw.propose({"val": "2"}, "bio", "src_2")
    repair_id = r.repair.quarantine_id

    gw.acknowledge_repair(repair_id)
    gw.execute_repair(repair_id, pathway_chosen="RETRACT_AND_REPLACE", notes="done")
    assert gw.list_repairs(status="executed")[0].status == "executed"

    oc.drain()

    gw.remove_category("bio", reason="bio category retired")

    conflicts = _conflict_signals(oc)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.payload["repair_id"] == repair_id
    assert c.payload["repair_status"] == "executed"


# ---------------------------------------------------------------------------
# Test 4 — No in-flight repairs → NO conflict signal
# ---------------------------------------------------------------------------

def test_gap6_no_in_flight_repairs_no_conflict_signal(tmp_path):
    """
    remove_category() with NO in-flight repairs emits NO
    REPAIR_ONTOLOGY_CONFLICT signal. Normal removal is unaffected.
    """
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    gw.add_category("event", singular=False)
    gw.propose({"val": "e1"}, "event", "src")

    oc.drain()

    gw.remove_category("event", reason="no repairs pending")

    conflicts = _conflict_signals(oc)
    assert len(conflicts) == 0, (
        "No conflict signal should be emitted when no in-flight repairs exist"
    )


# ---------------------------------------------------------------------------
# Test 5 — VERIFIED repair (closed lifecycle) → NO conflict signal
# ---------------------------------------------------------------------------

def test_gap6_verified_repair_not_in_flight_no_conflict(tmp_path):
    """
    remove_category() with a VERIFIED repair (lifecycle fully closed)
    emits NO REPAIR_ONTOLOGY_CONFLICT. Verified repairs are not in-flight.
    """
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    gw.add_category("note", singular=True)
    gw.propose({"val": "n1"}, "note", "src_a")
    r = gw.propose({"val": "n2"}, "note", "src_b")
    repair_id = r.repair.quarantine_id

    gw.acknowledge_repair(repair_id)
    gw.execute_repair(repair_id)
    gw.verify_repair(repair_id, outcome="contradiction resolved")

    verified = gw.list_repairs(status="verified")
    assert len(verified) == 1

    oc.drain()

    gw.remove_category("note", reason="note category no longer needed")

    conflicts = _conflict_signals(oc)
    assert len(conflicts) == 0, (
        "Verified (closed) repairs are not in-flight — no conflict signal expected"
    )


# ---------------------------------------------------------------------------
# Test 6 — Full lifecycle: conflict signaled, repair still completes (Option B)
# ---------------------------------------------------------------------------

def test_gap6_option_b_repair_completes_after_category_removal(tmp_path):
    """
    Option B (warning flag): after remove_category() emits a conflict signal,
    the repair lifecycle can still complete. The substrate does NOT block the
    repair — it surfaces the contradiction and lets the consumer decide.

    This is the core Option B guarantee: signal-and-continue, not block.
    Justified by I8 (Contradiction Visibility) + open-world semantics.
    """
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    gw.add_category("hyp", singular=True)
    gw.propose({"val": "h1"}, "hyp", "src_a")
    r = gw.propose({"val": "h2"}, "hyp", "src_b")
    repair_id = r.repair.quarantine_id

    # Remove category while repair is pending
    gw.remove_category("hyp", reason="category removed mid-repair")

    # Conflict signal was emitted
    conflicts = _conflict_signals(oc)
    assert len(conflicts) == 1, "Conflict signal must be emitted on category removal"

    # Option B: repair lifecycle still proceeds — not blocked
    ack = gw.acknowledge_repair(repair_id)
    assert ack.status == "acknowledged"

    exe = gw.execute_repair(repair_id, pathway_chosen="ACCEPT_LATEST")
    assert exe.status == "executed"

    ver = gw.verify_repair(repair_id, outcome="repair completed post-category-removal")
    assert ver.status == "verified"

    # Full audit trail exists
    all_repairs = gw.list_repairs()
    assert len(all_repairs) == 1
    assert all_repairs[0].status == "verified"


# ---------------------------------------------------------------------------
# Test 7 — Multiple in-flight repairs: one signal per repair
# ---------------------------------------------------------------------------

def test_gap6_multiple_in_flight_repairs_one_signal_each(tmp_path):
    """
    If multiple repairs are in-flight when a category is removed, each
    receives its own REPAIR_ONTOLOGY_CONFLICT signal. Signals are 1:1 with
    affected repairs — no batching, no deduplication.

    Two categories (alpha, beta) each with one in-flight repair.
    Removing alpha emits 1 conflict signal (for alpha's repair).
    Removing beta emits 1 conflict signal (for beta's repair).
    """
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    # Create two independent singular categories, each with an in-flight repair
    gw.add_category("alpha", singular=True)
    gw.propose({"v": "a1"}, "alpha", "s1")
    r_alpha = gw.propose({"v": "a2"}, "alpha", "s2")
    rid_alpha = r_alpha.repair.quarantine_id

    gw.add_category("beta", singular=True)
    gw.propose({"v": "b1"}, "beta", "s3")
    r_beta = gw.propose({"v": "b2"}, "beta", "s4")
    rid_beta = r_beta.repair.quarantine_id

    # Acknowledge alpha repair so it's in a different status
    gw.acknowledge_repair(rid_alpha)

    oc.drain()

    # Remove alpha category — has 1 ACKNOWLEDGED in-flight repair
    gw.remove_category("alpha", reason="alpha retired")
    alpha_conflicts = _conflict_signals(oc)
    assert len(alpha_conflicts) == 1
    assert alpha_conflicts[0].payload["repair_id"] == rid_alpha
    assert alpha_conflicts[0].payload["repair_status"] == "acknowledged"

    # Remove beta category — has 1 PENDING in-flight repair
    gw.remove_category("beta", reason="beta retired")
    beta_conflicts = _conflict_signals(oc)
    assert len(beta_conflicts) == 1
    assert beta_conflicts[0].payload["repair_id"] == rid_beta
    assert beta_conflicts[0].payload["repair_status"] == "pending"
