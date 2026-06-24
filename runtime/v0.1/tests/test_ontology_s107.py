"""
test_ontology_s107.py — Ontology primitive test suite.
Session 107 · WHY_ONTOLOGY_EXISTS.md

15 tests across 8 conditions:
  Condition 1 — OntologyRecord dataclass
  Condition 2 — add_category() basic behaviour
  Condition 3 — add_category() duplicate is a no-op
  Condition 4 — remove_category() basic behaviour
  Condition 5 — remove_category() nonexistent is a no-op
  Condition 6 — singular property is governed by Ontology
  Condition 7 — ONTOLOGY_MUTATION signal fires on add and remove
  Condition 8 — list_ontology_mutations() filter + drain() independence
  Integration  — gap-to-resolution pathway + existing items survive removal
"""
from __future__ import annotations

import dataclasses
import tempfile

import pytest

from ritam.runtime.v01 import (
    Substrate,
    SubstrateConfig,
    AdmissionVerdict,
    OntologyRecord,
)
from ritam.runtime.v01.types import SignalType


def _make_substrate(tmp_path, extra_categories=None, singular=None):
    cats = ["fact", "claim"] + (extra_categories or [])
    cfg = SubstrateConfig(
        storage_path=str(tmp_path),
        known_categories=cats,
        singular_categories=singular or ["claim"],
    )
    return Substrate(cfg)


# ---------------------------------------------------------------------------
# Condition 1 — OntologyRecord dataclass
# ---------------------------------------------------------------------------

def test_condition_1_ontology_record_fields():
    """OntologyRecord must have all 6 required fields."""
    fields = {f.name for f in dataclasses.fields(OntologyRecord)}
    assert "record_id" in fields
    assert "operation" in fields
    assert "category" in fields
    assert "singular" in fields
    assert "reason" in fields
    assert "mutated_at" in fields


def test_condition_1_ontology_record_is_frozen():
    """OntologyRecord must be immutable (frozen dataclass)."""
    r = OntologyRecord(
        record_id="x", operation="add", category="test",
        singular=False, reason=None, mutated_at="2026-06-22T00:00:00"
    )
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        r.category = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Condition 2 — add_category() basic behaviour
# ---------------------------------------------------------------------------

def test_condition_2_add_category_returns_record(tmp_path):
    """add_category() returns an OntologyRecord on success."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    rec = gw.add_category("biology", singular=False, reason="test add")
    assert isinstance(rec, OntologyRecord)
    assert rec.operation == "add"
    assert rec.category == "biology"
    assert rec.singular is False
    assert rec.reason == "test add"
    assert rec.record_id


def test_condition_2_add_category_enables_admission(tmp_path):
    """After add_category(), proposals to that category are admitted."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()

    # Before: unknown category → rejected
    result_before = gw.propose({"x": 1}, "new_cat", "src")
    assert result_before.verdict == AdmissionVerdict.REJECTED

    # Add category
    gw.add_category("new_cat", singular=False)

    # After: same category → admitted
    result_after = gw.propose({"x": 1}, "new_cat", "src")
    assert result_after.verdict == AdmissionVerdict.ADMITTED


# ---------------------------------------------------------------------------
# Condition 3 — add_category() duplicate is a no-op
# ---------------------------------------------------------------------------

def test_condition_3_duplicate_add_returns_none(tmp_path):
    """Adding an already-known category returns None and writes no record."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    gw.add_category("biology")
    result = gw.add_category("biology")  # duplicate
    assert result is None


def test_condition_3_duplicate_add_no_extra_record(tmp_path):
    """Duplicate add_category() does not write a second OntologyRecord."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    gw.add_category("biology")
    gw.add_category("biology")  # duplicate
    mutations = gw.list_ontology_mutations(operation="add")
    biology_records = [m for m in mutations if m.category == "biology"]
    assert len(biology_records) == 1


# ---------------------------------------------------------------------------
# Condition 4 — remove_category() basic behaviour
# ---------------------------------------------------------------------------

def test_condition_4_remove_category_returns_record(tmp_path):
    """remove_category() returns an OntologyRecord with operation='remove'."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    rec = gw.remove_category("fact", reason="retiring fact category")
    assert isinstance(rec, OntologyRecord)
    assert rec.operation == "remove"
    assert rec.category == "fact"
    assert rec.singular is None  # singular property is gone on removal
    assert rec.reason == "retiring fact category"


def test_condition_4_remove_category_blocks_admission(tmp_path):
    """After remove_category(), proposals to that category are rejected."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()

    # Before: known category → admitted
    result_before = gw.propose({"data": "x"}, "fact", "src")
    assert result_before.verdict == AdmissionVerdict.ADMITTED

    # Remove
    gw.remove_category("fact")

    # After: now unknown → rejected
    result_after = gw.propose({"data": "y"}, "fact", "src")
    assert result_after.verdict == AdmissionVerdict.REJECTED


# ---------------------------------------------------------------------------
# Condition 5 — remove_category() nonexistent is a no-op
# ---------------------------------------------------------------------------

def test_condition_5_remove_nonexistent_returns_none(tmp_path):
    """Removing a category that does not exist returns None."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    result = gw.remove_category("does_not_exist")
    assert result is None


def test_condition_5_remove_nonexistent_no_record(tmp_path):
    """Removing a nonexistent category writes no OntologyRecord."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    gw.remove_category("does_not_exist")
    mutations = gw.list_ontology_mutations()
    assert len(mutations) == 0


# ---------------------------------------------------------------------------
# Condition 6 — singular property is governed by Ontology
# ---------------------------------------------------------------------------

def test_condition_6_add_singular_category_enforces_at_most_one(tmp_path):
    """A category added with singular=True enforces singular admission rules."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    gw.add_category("capital_city", singular=True)

    r1 = gw.propose({"name": "Paris"}, "capital_city", "geo")
    r2 = gw.propose({"name": "Lyon"}, "capital_city", "geo")

    assert r1.verdict == AdmissionVerdict.ADMITTED
    # Second distinct item to singular category must be quarantined
    assert r2.verdict == AdmissionVerdict.QUARANTINED


def test_condition_6_add_plural_category_allows_multiple(tmp_path):
    """A category added with singular=False (default) allows multiple items."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    gw.add_category("observation", singular=False)

    r1 = gw.propose({"obs": "A"}, "observation", "sensor")
    r2 = gw.propose({"obs": "B"}, "observation", "sensor")

    assert r1.verdict == AdmissionVerdict.ADMITTED
    assert r2.verdict == AdmissionVerdict.ADMITTED


# ---------------------------------------------------------------------------
# Condition 7 — ONTOLOGY_MUTATION signal fires
# ---------------------------------------------------------------------------

def test_condition_7_signal_fires_on_add(tmp_path):
    """add_category() emits ONTOLOGY_MUTATION signal with correct payload."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    gw.add_category("biology", singular=False, reason="new domain")
    signals = oc.drain()
    ontology_signals = [sig for sig in signals
                        if sig.signal_type == SignalType.ONTOLOGY_MUTATION]
    assert len(ontology_signals) == 1
    assert ontology_signals[0].payload["operation"] == "add"
    assert ontology_signals[0].payload["category"] == "biology"
    assert ontology_signals[0].payload["singular"] is False
    assert ontology_signals[0].payload["reason"] == "new domain"


def test_condition_7_signal_fires_on_remove(tmp_path):
    """remove_category() emits ONTOLOGY_MUTATION signal with operation='remove'."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    gw.remove_category("fact", reason="retiring")
    signals = oc.drain()
    ontology_signals = [sig for sig in signals
                        if sig.signal_type == SignalType.ONTOLOGY_MUTATION]
    assert len(ontology_signals) == 1
    assert ontology_signals[0].payload["operation"] == "remove"
    assert ontology_signals[0].payload["category"] == "fact"


# ---------------------------------------------------------------------------
# Condition 8 — list_ontology_mutations() + drain() independence
# ---------------------------------------------------------------------------

def test_condition_8_list_filter_by_operation(tmp_path):
    """list_ontology_mutations(operation=) filters correctly."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()

    gw.add_category("bio")
    gw.add_category("chem")
    gw.remove_category("bio")

    adds = gw.list_ontology_mutations(operation="add")
    removes = gw.list_ontology_mutations(operation="remove")
    all_mutations = gw.list_ontology_mutations()

    assert len(adds) == 2
    assert len(removes) == 1
    assert len(all_mutations) == 3


def test_condition_8_ontology_log_survives_drain(tmp_path):
    """OntologyLog persists independently of ObservationChannel.drain()."""
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    gw.add_category("physics", reason="new subject")
    oc.drain()  # clear the channel

    # Record must still be in the log
    mutations = gw.list_ontology_mutations()
    assert len(mutations) == 1
    assert mutations[0].category == "physics"
    assert mutations[0].reason == "new subject"


# ---------------------------------------------------------------------------
# Integration — gap-to-resolution pathway + existing items survive removal
# ---------------------------------------------------------------------------

def test_integration_gap_to_resolution_pathway(tmp_path):
    """
    Full governed pathway:
    OBSERVATION_GAP fires → add_category() → ONTOLOGY_MUTATION fires
    → subsequent proposal admitted.
    Both gap record and ontology record exist in their respective logs.
    """
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()
    oc = s.observation_channel()

    # Step 1: unknown category → OBSERVATION_GAP
    r1 = gw.propose({"forecast": "sunny"}, "weather", "sensor")
    assert r1.verdict == AdmissionVerdict.REJECTED
    signals_after_gap = oc.drain()
    gap_signals = [sig for sig in signals_after_gap
                   if sig.signal_type == SignalType.OBSERVATION_GAP]
    assert len(gap_signals) == 1

    # Gap record persists
    gaps = gw.list_gaps(category="weather")
    assert len(gaps) == 1

    # Step 2: governed repair — add the category
    rec = gw.add_category("weather", singular=False,
                           reason="Observed gap in weather category")
    assert rec is not None
    signals_after_add = oc.drain()
    mutation_signals = [sig for sig in signals_after_add
                        if sig.signal_type == SignalType.ONTOLOGY_MUTATION]
    assert len(mutation_signals) == 1

    # OntologyRecord exists
    mutations = gw.list_ontology_mutations()
    assert any(m.category == "weather" and m.operation == "add"
               for m in mutations)

    # Step 3: now admitted
    r2 = gw.propose({"forecast": "sunny"}, "weather", "sensor")
    assert r2.verdict == AdmissionVerdict.ADMITTED


def test_integration_existing_items_survive_removal(tmp_path):
    """
    Removing a category does not delete previously admitted items.
    Existing items remain in the admission log.
    Future proposals to the removed category get OBSERVATION_GAP.
    """
    s = _make_substrate(tmp_path)
    gw = s.admission_gateway()

    # Admit some items under 'fact'
    gw.propose({"val": 1}, "fact", "src")
    gw.propose({"val": 2}, "fact", "src")

    admitted_before = gw.list_admitted(category="fact")
    fact_items_before = admitted_before
    assert len(fact_items_before) == 2

    # Remove the category
    gw.remove_category("fact", reason="fact category retired")

    # Existing items still in admission log
    admitted_after = gw.list_admitted(category="fact")
    fact_items_after = admitted_after
    assert len(fact_items_after) == 2  # unchanged

    # New proposals → rejected (OBSERVATION_GAP)
    r = gw.propose({"val": 3}, "fact", "src")
    assert r.verdict == AdmissionVerdict.REJECTED
