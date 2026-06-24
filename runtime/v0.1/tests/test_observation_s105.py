"""
test_observation_s105.py
Proves all 8 executable conditions from WHY_OBSERVATION_EXISTS.md §8.
Session 105 — Observation primitive.

Condition summary:
  1. GapRecord dataclass exists with: gap_id, category, content_type, source, observed_at
  2. When propose() fires OBSERVATION_GAP, a GapRecord is also persisted to ObservationLog
  3. gw.list_gaps() returns list[GapRecord] ordered by observed_at
  4. gw.list_gaps(category=X) filters by unknown category
  5. gw.gap_count(category) returns int — occurrences of that unknown category
  6. Gap records persist across channel.drain() — independent of signal bus
  7. Integration: propose to unknown category → OBSERVATION_GAP emitted AND
     list_gaps() returns record AND item not admitted
  8. Integration: propose same unknown category 3 times → gap_count == 3

Protected distinction (§9): records perceptual limits, not truth judgements.
"""
import dataclasses
import tempfile
from pathlib import Path

import pytest

from ritam.runtime.v01 import Substrate, SubstrateConfig, AdmissionVerdict, GapRecord
from ritam.runtime.v01.types import SignalType


def _make_substrate(tmp_path):
    cfg = SubstrateConfig(
        storage_path=str(tmp_path / "test.db"),
        known_categories=["claim", "evidence"],
        singular_categories=["claim"],
    )
    return Substrate(cfg)


# ---------------------------------------------------------------------------
# Condition 1 — GapRecord dataclass
# ---------------------------------------------------------------------------

def test_condition_1_gap_record_dataclass_fields():
    """GapRecord must have all 5 required fields."""
    fields = {f.name for f in dataclasses.fields(GapRecord)}
    assert "gap_id" in fields
    assert "category" in fields
    assert "content_type" in fields
    assert "source" in fields
    assert "observed_at" in fields


def test_condition_1_gap_record_is_frozen():
    """GapRecord must be immutable (frozen dataclass)."""
    record = GapRecord(
        gap_id="test-id",
        category="unknown-cat",
        content_type="str",
        source="test",
        observed_at="2026-06-22T00:00:00+00:00",
    )
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        record.category = "mutated"  # type: ignore


# ---------------------------------------------------------------------------
# Condition 2 — Gap persisted on OBSERVATION_GAP
# ---------------------------------------------------------------------------

def test_condition_2_gap_persisted_on_unknown_category(tmp_path):
    """Proposing to an unknown category persists a GapRecord."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    result = gw.propose("some content", "unknown-category", "test-source")
    assert result.verdict == AdmissionVerdict.REJECTED

    gaps = gw.list_gaps()
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap.category == "unknown-category"
    assert gap.source == "test-source"
    assert gap.content_type == "str"
    assert gap.observed_at is not None


def test_condition_2_known_category_produces_no_gap(tmp_path):
    """Proposing to a known category does not produce a gap record."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("valid content", "claim", "test-source")
    gaps = gw.list_gaps()
    assert len(gaps) == 0


def test_condition_2_gap_records_content_type_correctly(tmp_path):
    """GapRecord captures the Python type name of the proposed content."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose({"key": "value"}, "unknown-dict-category", "test-source")
    gaps = gw.list_gaps()
    assert len(gaps) == 1
    assert gaps[0].content_type == "dict"


# ---------------------------------------------------------------------------
# Condition 3 — list_gaps() returns all records ordered by observed_at
# ---------------------------------------------------------------------------

def test_condition_3_list_gaps_returns_all_ordered(tmp_path):
    """list_gaps() returns all gap records ordered by observed_at ascending."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("content A", "unknown-alpha", "src")
    gw.propose("content B", "unknown-beta", "src")
    gw.propose("content C", "unknown-gamma", "src")

    gaps = gw.list_gaps()
    assert len(gaps) == 3
    # Ordered ascending by observed_at
    timestamps = [g.observed_at for g in gaps]
    assert timestamps == sorted(timestamps)


def test_condition_3_list_gaps_empty_when_no_gaps(tmp_path):
    """list_gaps() returns empty list when no gaps have been observed."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gaps = gw.list_gaps()
    assert gaps == []


# ---------------------------------------------------------------------------
# Condition 4 — list_gaps(category=X) filters correctly
# ---------------------------------------------------------------------------

def test_condition_4_filter_by_category(tmp_path):
    """list_gaps(category=X) returns only records for that unknown category."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("content", "category-alpha", "src")
    gw.propose("content", "category-beta", "src")
    gw.propose("content", "category-alpha", "src")  # second occurrence

    alpha_gaps = gw.list_gaps(category="category-alpha")
    assert len(alpha_gaps) == 2
    assert all(g.category == "category-alpha" for g in alpha_gaps)

    beta_gaps = gw.list_gaps(category="category-beta")
    assert len(beta_gaps) == 1
    assert beta_gaps[0].category == "category-beta"


def test_condition_4_filter_unknown_category_returns_empty(tmp_path):
    """list_gaps(category=X) returns empty list if that category was never a gap."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("content", "some-unknown", "src")

    result = gw.list_gaps(category="never-seen")
    assert result == []


# ---------------------------------------------------------------------------
# Condition 5 — gap_count() returns recurrence count
# ---------------------------------------------------------------------------

def test_condition_5_gap_count_returns_occurrences(tmp_path):
    """gap_count(category) returns how many times that unknown category was encountered."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("a", "recurring-unknown", "src")
    gw.propose("b", "recurring-unknown", "src")
    gw.propose("c", "recurring-unknown", "src")

    assert gw.gap_count("recurring-unknown") == 3


def test_condition_5_gap_count_zero_for_unseen(tmp_path):
    """gap_count returns 0 for categories never encountered."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    assert gw.gap_count("never-proposed") == 0


def test_condition_5_gap_count_not_affected_by_known_category(tmp_path):
    """Proposals to known categories do not affect gap_count."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("valid", "claim", "src")  # known category
    assert gw.gap_count("claim") == 0


# ---------------------------------------------------------------------------
# Condition 6 — Gap records persist across channel.drain()
# ---------------------------------------------------------------------------

def test_condition_6_gaps_persist_after_drain(tmp_path):
    """Gap records survive channel.drain() — independent of signal bus."""
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    gw.propose("content", "unknown-cat", "src")

    # Drain the channel — signals are gone
    signals = ch.drain()
    gap_signals = [s for s in signals if s.signal_type == SignalType.OBSERVATION_GAP]
    assert len(gap_signals) == 1  # signal was there

    # Drain again — channel is empty
    signals_after = ch.drain()
    assert len(signals_after) == 0

    # But gap record is still in ObservationLog
    gaps = gw.list_gaps()
    assert len(gaps) == 1, "Gap record must persist after channel drain"
    assert gaps[0].category == "unknown-cat"


# ---------------------------------------------------------------------------
# Condition 7 — Full integration: OBSERVATION_GAP emitted AND gap persisted AND not admitted
# ---------------------------------------------------------------------------

def test_condition_7_full_integration_gap_and_signal(tmp_path):
    """
    Propose to unknown category.
    Assert: OBSERVATION_GAP signal emitted.
    Assert: GapRecord persisted to ObservationLog.
    Assert: item NOT admitted.
    Assert: protected distinction — gap record describes perceptual limit, not content validity.
    """
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()
    ch = sub.observation_channel()

    result = gw.propose("proposed content", "completely-unknown", "integration-test")

    # Not admitted
    assert result.verdict == AdmissionVerdict.REJECTED
    assert "unknown category" in result.reason.lower() or "unknown" in result.reason.lower()

    # Signal fired
    signals = ch.drain()
    gap_signals = [s for s in signals if s.signal_type == SignalType.OBSERVATION_GAP]
    assert len(gap_signals) == 1
    payload = gap_signals[0].payload
    assert payload["category"] == "completely-unknown"
    assert payload["source"] == "integration-test"

    # Gap persisted independently
    gaps = gw.list_gaps()
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap.category == "completely-unknown"
    assert gap.source == "integration-test"
    assert gap.content_type == "str"

    # Protected distinction: record describes perceptual limit, not content judgement
    assert "invalid" not in gap.category
    assert "rejected" not in gap.category


# ---------------------------------------------------------------------------
# Condition 8 — Three proposals to same unknown category → gap_count == 3
# ---------------------------------------------------------------------------

def test_condition_8_recurrence_counting(tmp_path):
    """
    Propose same unknown category three times.
    Assert gap_count == 3.
    Assert list_gaps() returns 3 records.
    Assert list_gaps(category=X) returns exactly those 3.
    """
    sub = _make_substrate(tmp_path)
    gw = sub.admission_gateway()

    gw.propose("first", "recurring-gap", "src-a")
    gw.propose("second", "recurring-gap", "src-b")
    gw.propose("third", "recurring-gap", "src-c")

    # Recurrence count
    assert gw.gap_count("recurring-gap") == 3

    # All 3 in list
    all_gaps = gw.list_gaps()
    assert len(all_gaps) == 3

    # Filtered list
    filtered = gw.list_gaps(category="recurring-gap")
    assert len(filtered) == 3
    assert all(g.category == "recurring-gap" for g in filtered)

    # Different sources captured
    sources = {g.source for g in filtered}
    assert sources == {"src-a", "src-b", "src-c"}
