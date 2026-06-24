"""
test_epistemic_s104.py
Proves all 8 executable conditions from WHY_EPISTEMIC_EXISTS.md §8.
Session 104 — Epistemic primitive.

Condition summary:
  1. AdmissionRecord carries confidence: float | None
  2. gw.propose(..., confidence=0.75) stores declaration; visible in list_admitted()
  3. gw.check_epistemic(category, threshold) returns below-threshold records when
     all tagged items fall below threshold; empty list when any meets threshold
  4. SignalType.EPISTEMIC_ALERT is a member of SignalType enum
  5. check_epistemic() emits EPISTEMIC_ALERT when category is epistemically fragile
  6. No EPISTEMIC_ALERT emitted when >= 1 tagged item meets or exceeds threshold
  7. RepairSuggestion with pathways: RETRACT_AND_REPLACE, DOWNGRADE, REQUEST_EVIDENCE
  8. Integration: admit item with confidence=0.2, check_epistemic(threshold=0.5),
     assert EPISTEMIC_ALERT emitted and item still admitted (no auto-retraction)

Protected distinction (§9): EPISTEMIC_ALERT describes declared confidence, not truth.
"""
import tempfile
from pathlib import Path

import pytest

from ritam.runtime.v01 import Substrate, SubstrateConfig, AdmissionVerdict
from ritam.runtime.v01.types import SignalType, AdmissionRecord


def _make_substrate(tmp_path):
    cfg = SubstrateConfig(
        storage_path=str(tmp_path / "test.db"),
        known_categories=["claim", "evidence", "hypothesis"],
        singular_categories=["claim"],
    )
    return Substrate(cfg)


# ---------------------------------------------------------------------------
# Condition 1 — AdmissionRecord carries confidence field
# ---------------------------------------------------------------------------

def test_condition_1_admission_record_has_confidence_field():
    """AdmissionRecord must have a confidence field typed float | None."""
    import dataclasses
    fields = {f.name: f for f in dataclasses.fields(AdmissionRecord)}
    assert "confidence" in fields, "Missing: confidence field on AdmissionRecord"


# ---------------------------------------------------------------------------
# Condition 2 — propose() stores confidence declaration
# ---------------------------------------------------------------------------

def test_condition_2_propose_stores_confidence(tmp_path):
    """gw.propose(..., confidence=0.8) stores declaration; visible in list_admitted()."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    result = gw.propose("strong claim", "evidence", "test-source", confidence=0.8)
    assert result.verdict == AdmissionVerdict.ADMITTED

    records = gw.list_admitted("evidence")
    assert len(records) == 1
    assert records[0].confidence == 0.8


def test_condition_2_untagged_confidence_is_none(tmp_path):
    """Items proposed without confidence have confidence=None."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("untagged item", "evidence", "test-source")
    records = gw.list_admitted("evidence")
    assert records[0].confidence is None


def test_condition_2_low_confidence_admitted_not_blocked(tmp_path):
    """confidence=0.01 does not block admission — Epistemic tags but does not gate."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    result = gw.propose("very weak claim", "evidence", "test-source", confidence=0.01)
    assert result.verdict == AdmissionVerdict.ADMITTED


# ---------------------------------------------------------------------------
# Condition 3 — check_epistemic trigger logic
# ---------------------------------------------------------------------------

def test_condition_3_returns_below_threshold_when_all_fragile(tmp_path):
    """When all tagged items < threshold, check_epistemic returns them."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("weak evidence A", "evidence", "src", confidence=0.2)
    gw.propose("weak evidence B", "evidence", "src", confidence=0.3)

    fragile = gw.check_epistemic("evidence", threshold=0.5)
    assert len(fragile) == 2


def test_condition_3_suppressed_by_one_strong_item(tmp_path):
    """One item meeting threshold suppresses the alert for the whole category."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("weak A", "evidence", "src", confidence=0.1)
    gw.propose("weak B", "evidence", "src", confidence=0.2)
    gw.propose("strong", "evidence", "src", confidence=0.9)

    fragile = gw.check_epistemic("evidence", threshold=0.5)
    assert fragile == [], "Strong item must suppress alert"


def test_condition_3_untagged_items_excluded_from_fragility(tmp_path):
    """Untagged items (confidence=None) are excluded — fragility applies to tagged items only."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    # All tagged items are below threshold
    gw.propose("weak tagged", "evidence", "src", confidence=0.2)
    # Untagged item does not count toward suppression
    gw.propose("untagged item", "evidence", "src")

    fragile = gw.check_epistemic("evidence", threshold=0.5)
    # Should still alert because the one tagged item is below threshold
    assert len(fragile) == 1
    assert fragile[0].content == "weak tagged"


def test_condition_3_no_tagged_items_not_fragile(tmp_path):
    """Category with only untagged items returns empty (fragility undetectable)."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("untagged A", "evidence", "src")
    gw.propose("untagged B", "evidence", "src")

    fragile = gw.check_epistemic("evidence", threshold=0.5)
    assert fragile == []


def test_condition_3_empty_category_not_fragile(tmp_path):
    """Empty category returns empty — nothing to be fragile about."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    fragile = gw.check_epistemic("evidence", threshold=0.5)
    assert fragile == []


# ---------------------------------------------------------------------------
# Condition 4 — SignalType.EPISTEMIC_ALERT in the enum
# ---------------------------------------------------------------------------

def test_condition_4_epistemic_alert_in_signal_type():
    """SignalType.EPISTEMIC_ALERT must be a valid enum member."""
    assert hasattr(SignalType, "EPISTEMIC_ALERT")
    assert SignalType.EPISTEMIC_ALERT.value == "epistemic_alert"


# ---------------------------------------------------------------------------
# Condition 5 — EPISTEMIC_ALERT emitted when fragile
# ---------------------------------------------------------------------------

def test_condition_5_epistemic_alert_emitted(tmp_path):
    """check_epistemic() emits EPISTEMIC_ALERT when category is fragile."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    gw.propose("fragile claim", "evidence", "src", confidence=0.2)
    gw.check_epistemic("evidence", threshold=0.5)

    signals = ch.drain()
    alert_signals = [s for s in signals if s.signal_type == SignalType.EPISTEMIC_ALERT]
    assert len(alert_signals) == 1


# ---------------------------------------------------------------------------
# Condition 6 — No EPISTEMIC_ALERT when threshold is met
# ---------------------------------------------------------------------------

def test_condition_6_no_alert_when_threshold_met(tmp_path):
    """EPISTEMIC_ALERT NOT emitted when >= 1 tagged item meets threshold."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    gw.propose("weak", "evidence", "src", confidence=0.1)
    gw.propose("strong", "evidence", "src", confidence=0.9)
    gw.check_epistemic("evidence", threshold=0.5)

    signals = ch.drain()
    alert_signals = [s for s in signals if s.signal_type == SignalType.EPISTEMIC_ALERT]
    assert len(alert_signals) == 0


# ---------------------------------------------------------------------------
# Condition 7 — RepairSuggestion with epistemic pathways
# ---------------------------------------------------------------------------

def test_condition_7_repair_pathways_in_signal(tmp_path):
    """EPISTEMIC_ALERT payload contains all 3 epistemic repair pathways."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    gw.propose("speculative evidence", "evidence", "src", confidence=0.15)
    gw.check_epistemic("evidence", threshold=0.5)

    signals = ch.drain()
    alert = next(s for s in signals if s.signal_type == SignalType.EPISTEMIC_ALERT)
    pathways = alert.payload["repair_pathways"]

    assert "RETRACT_AND_REPLACE" in pathways
    assert "DOWNGRADE" in pathways
    assert "REQUEST_EVIDENCE" in pathways


# ---------------------------------------------------------------------------
# Condition 8 — Full integration test
# ---------------------------------------------------------------------------

def test_condition_8_full_integration(tmp_path):
    """
    Admit item with confidence=0.2.
    check_epistemic(threshold=0.5).
    Assert EPISTEMIC_ALERT emitted.
    Assert item still admitted (no auto-retraction).
    Assert protected distinction: payload says 'declared confidence below threshold'.
    """
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    result = gw.propose("borderline hypothesis", "evidence", "integration-test",
                        confidence=0.2)
    assert result.verdict == AdmissionVerdict.ADMITTED
    item_id = result.item_id

    # Above-threshold check — no alert
    fragile = gw.check_epistemic("evidence", threshold=0.1)
    assert fragile == [], "confidence=0.2 meets threshold=0.1, should not alert"
    ch.drain()  # clear

    # Below-threshold check — alert
    fragile = gw.check_epistemic("evidence", threshold=0.5)
    assert len(fragile) == 1
    assert fragile[0].item_id == item_id

    signals = ch.drain()
    alert_signals = [s for s in signals if s.signal_type == SignalType.EPISTEMIC_ALERT]
    assert len(alert_signals) == 1

    # Protected distinction (§9): declared confidence, not truth
    payload = alert_signals[0].payload
    assert payload["message"] == "declared confidence below threshold"
    assert "unreliable item" not in str(payload)
    assert "false claim" not in str(payload)

    # No auto-retraction: item remains admitted
    still_admitted = gw.list_admitted("evidence")
    assert any(r.item_id == item_id for r in still_admitted), \
        "Epistemic alert must NOT auto-retract — substrate signals, consumer decides"


# ---------------------------------------------------------------------------
# Bonus: the 0.95 / 0.10 / 0.10 / 0.10 / 0.10 case (Rishi's design example)
# ---------------------------------------------------------------------------

def test_design_note_one_strong_suppresses_four_weak(tmp_path):
    """
    Design note from §3 B3 sign-off:
    [0.95, 0.10, 0.10, 0.10, 0.10] — one strong item suppresses alert.
    This is the known limitation of all-below-threshold trigger.
    The proportion-based direction would alert here.
    Test documents current behaviour, not ideal behaviour.
    """
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    gw.propose("strong anchor", "evidence", "src", confidence=0.95)
    gw.propose("weak B", "evidence", "src", confidence=0.10)
    gw.propose("weak C", "evidence", "src", confidence=0.10)
    gw.propose("weak D", "evidence", "src", confidence=0.10)
    gw.propose("weak E", "evidence", "src", confidence=0.10)

    fragile = gw.check_epistemic("evidence", threshold=0.5)
    assert fragile == [], (
        "Current all-below-threshold trigger: one strong item suppresses alert. "
        "Known limitation — proportion-based trigger is the forward direction."
    )

    signals = ch.drain()
    alert_signals = [s for s in signals if s.signal_type == SignalType.EPISTEMIC_ALERT]
    assert len(alert_signals) == 0
