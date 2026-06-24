"""
test_temporal_s103.py
Proves all 8 executable conditions from WHY_TEMPORAL_EXISTS.md §8.
Session 103 — Temporal primitive.

Condition summary:
  1. AdmissionRecord carries expires_after_seconds and expired_at
  2. gw.propose(..., expires_after_seconds=N) stores the contract
  3. gw.age_of(item_id) -> float returns seconds since admitted_at
  4. gw.check_expired() -> list[AdmissionRecord] returns items past expiry
  5. SignalType.TEMPORAL_ALERT is a member of SignalType enum
  6. ObservationChannel emits TEMPORAL_ALERT when check_expired() finds expired items
  7. RepairSuggestion produced with pathways: RETRACT_AND_REPLACE, EXTEND, HOLD_AS_STALE
  8. Integration: admit with expires_after_seconds=1, wait 2s, check_expired(),
     assert TEMPORAL_ALERT emitted

Protected distinction (§9): TEMPORAL_ALERT describes item age, never truth.
"""
import time
import sqlite3
import tempfile
from pathlib import Path

import pytest

from ritam.runtime.v01 import Substrate, SubstrateConfig, AdmissionVerdict
from ritam.runtime.v01.types import SignalType, AdmissionRecord


def _make_substrate(tmp_path):
    cfg = SubstrateConfig(
        storage_path=str(tmp_path / "test.db"),
        known_categories=["observation", "claim"],
        singular_categories=["claim"],
    )
    return Substrate(cfg)


# ---------------------------------------------------------------------------
# Condition 1 — AdmissionRecord carries temporal fields
# ---------------------------------------------------------------------------

def test_condition_1_admission_record_has_temporal_fields():
    """AdmissionRecord dataclass must have expires_after_seconds and expired_at."""
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(AdmissionRecord)}
    assert "expires_after_seconds" in field_names, "Missing: expires_after_seconds"
    assert "expired_at" in field_names, "Missing: expired_at"


# ---------------------------------------------------------------------------
# Condition 2 — propose() stores the expiry contract
# ---------------------------------------------------------------------------

def test_condition_2_propose_stores_expiry_contract(tmp_path):
    """gw.propose(..., expires_after_seconds=N) stores contract; visible in list_admitted."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    result = gw.propose("some observation", "observation", "test-source",
                        expires_after_seconds=300)
    assert result.verdict == AdmissionVerdict.ADMITTED

    records = gw.list_admitted("observation")
    assert len(records) == 1
    rec = records[0]
    assert rec.expires_after_seconds == 300
    assert rec.expired_at is not None, "expired_at must be set when contract is declared"


def test_condition_2_no_contract_leaves_fields_none(tmp_path):
    """Items without an expiry contract have both temporal fields as None."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("no contract item", "observation", "test-source")
    records = gw.list_admitted("observation")
    assert records[0].expires_after_seconds is None
    assert records[0].expired_at is None


# ---------------------------------------------------------------------------
# Condition 3 — age_of() returns seconds since admitted_at
# ---------------------------------------------------------------------------

def test_condition_3_age_of_returns_float(tmp_path):
    """gw.age_of(item_id) returns a non-negative float."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    result = gw.propose("test item", "observation", "test-source")
    item_id = result.item_id

    age = gw.age_of(item_id)
    assert isinstance(age, float)
    assert age >= 0.0


def test_condition_3_age_increases_over_time(tmp_path):
    """age_of() grows with real elapsed time."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    result = gw.propose("ageing item", "observation", "test-source")
    item_id = result.item_id

    age1 = gw.age_of(item_id)
    time.sleep(0.1)
    age2 = gw.age_of(item_id)
    assert age2 > age1


def test_condition_3_age_of_missing_item_raises(tmp_path):
    """age_of() raises KeyError for unknown item_id."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    with pytest.raises(KeyError):
        gw.age_of("does-not-exist")


# ---------------------------------------------------------------------------
# Condition 4 — check_expired() returns expired items
# ---------------------------------------------------------------------------

def test_condition_4_check_expired_returns_expired_items(tmp_path):
    """Items past their expiry contract appear in check_expired()."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("short-lived item", "observation", "test-source",
               expires_after_seconds=1)
    time.sleep(1.1)

    expired = gw.check_expired()
    assert len(expired) == 1
    assert expired[0].content == "short-lived item"


def test_condition_4_unexpired_items_not_returned(tmp_path):
    """Items within their expiry window do not appear in check_expired()."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("long-lived item", "observation", "test-source",
               expires_after_seconds=9999)

    expired = gw.check_expired()
    assert len(expired) == 0


def test_condition_4_no_contract_never_expires(tmp_path):
    """Items without an expiry contract never appear in check_expired()."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("no contract", "observation", "test-source")
    time.sleep(0.05)
    expired = gw.check_expired()
    assert len(expired) == 0


# ---------------------------------------------------------------------------
# Condition 5 — SignalType.TEMPORAL_ALERT is in the enum
# ---------------------------------------------------------------------------

def test_condition_5_temporal_alert_in_signal_type():
    """SignalType.TEMPORAL_ALERT must be a valid enum member."""
    assert hasattr(SignalType, "TEMPORAL_ALERT")
    assert SignalType.TEMPORAL_ALERT.value == "temporal_alert"


# ---------------------------------------------------------------------------
# Condition 6 — TEMPORAL_ALERT emitted by ObservationChannel
# ---------------------------------------------------------------------------

def test_condition_6_temporal_alert_emitted(tmp_path):
    """check_expired() causes ObservationChannel to emit TEMPORAL_ALERT for each expired item."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    gw.propose("expiring item", "observation", "test-source",
               expires_after_seconds=1)
    time.sleep(1.1)

    gw.check_expired()

    signals = ch.drain()
    alert_signals = [s for s in signals if s.signal_type == SignalType.TEMPORAL_ALERT]
    assert len(alert_signals) == 1, f"Expected 1 TEMPORAL_ALERT, got {len(alert_signals)}"


def test_condition_6_no_alert_before_expiry(tmp_path):
    """TEMPORAL_ALERT is NOT emitted when no items have expired."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    gw.propose("long-lived", "observation", "test-source", expires_after_seconds=9999)
    gw.check_expired()

    signals = ch.drain()
    alert_signals = [s for s in signals if s.signal_type == SignalType.TEMPORAL_ALERT]
    assert len(alert_signals) == 0


# ---------------------------------------------------------------------------
# Condition 7 — RepairSuggestion with temporal pathways
# ---------------------------------------------------------------------------

def test_condition_7_repair_suggestion_produced(tmp_path):
    """check_expired() produces RepairSuggestion with all 3 temporal pathways."""
    from ritam.runtime.v01.types import RepairSuggestion
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    gw.propose("temporary claim", "observation", "test-source",
               expires_after_seconds=1)
    time.sleep(1.1)

    gw.check_expired()

    signals = ch.drain()
    alert_signals = [s for s in signals if s.signal_type == SignalType.TEMPORAL_ALERT]
    assert len(alert_signals) == 1

    payload = alert_signals[0].payload
    assert "repair_pathways" in payload
    pathways = payload["repair_pathways"]
    assert "RETRACT_AND_REPLACE" in pathways
    assert "EXTEND" in pathways
    assert "HOLD_AS_STALE" in pathways


# ---------------------------------------------------------------------------
# Condition 8 — Full integration test (the core proof)
# ---------------------------------------------------------------------------

def test_condition_8_full_integration(tmp_path):
    """
    Admit item with expires_after_seconds=1.
    Wait 2 seconds.
    Call check_expired().
    Assert TEMPORAL_ALERT emitted.
    Assert item still admitted (no auto-retraction).
    """
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    result = gw.propose("integration test item", "observation", "integration-test",
                        expires_after_seconds=1)
    assert result.verdict == AdmissionVerdict.ADMITTED
    item_id = result.item_id

    # Item is admitted and still within window immediately
    assert len(gw.check_expired()) == 0, "Should not expire immediately"

    time.sleep(2.0)

    expired = gw.check_expired()
    assert len(expired) == 1
    assert expired[0].item_id == item_id

    signals = ch.drain()
    alert_signals = [s for s in signals if s.signal_type == SignalType.TEMPORAL_ALERT]
    assert len(alert_signals) == 1, "TEMPORAL_ALERT must be emitted"

    # Protected distinction (§9): signal describes age, not truth
    payload = alert_signals[0].payload
    assert "item age exceeds declared contract" == payload["message"]
    assert "expired claim" not in str(payload)
    assert "invalid item" not in str(payload)

    # No auto-retraction: item remains in list_admitted
    still_admitted = gw.list_admitted("observation")
    assert any(r.item_id == item_id for r in still_admitted), \
        "Expired items must NOT be auto-retracted — substrate signals, consumer decides"


# ---------------------------------------------------------------------------
# Bonus: multiple expired items
# ---------------------------------------------------------------------------

def test_multiple_expired_items(tmp_path):
    """check_expired() handles multiple expired items; one TEMPORAL_ALERT per item."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    gw.propose("obs A", "observation", "src", expires_after_seconds=1)
    gw.propose("obs B", "observation", "src", expires_after_seconds=1)
    gw.propose("obs C forever", "observation", "src", expires_after_seconds=9999)

    time.sleep(1.1)
    expired = gw.check_expired()

    assert len(expired) == 2

    signals = ch.drain()
    alert_signals = [s for s in signals if s.signal_type == SignalType.TEMPORAL_ALERT]
    assert len(alert_signals) == 2
