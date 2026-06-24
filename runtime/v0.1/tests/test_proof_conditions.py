"""
Proof-condition tests for Runtime v0.1.
Consumer perspective: imports ONLY from the public ritam.runtime.v01 API.
No internal module imports (Appendix C of API_SPEC.md).

Tests A and B: implemented this session.
Test C: requires full ObservationChannel (Session 080). Stub assertion included.
"""
import sys
import os
import tempfile

# Add the runtime/v0.1 directory to path so we can import ritam
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ritam.runtime.v01 import (
    Substrate,
    SubstrateConfig,
    AdmissionVerdict,
    SignalType,
)


def make_substrate(tmp_path: str) -> Substrate:
    config = SubstrateConfig(
        storage_path=tmp_path,
        known_categories=["claim", "evidence", "question"],
        singular_categories=["claim"],  # claim: at-most-one; evidence+question: plural
    )
    return Substrate(config)


# ---------------------------------------------------------------------------
# TEST A — Compliant admission
# ---------------------------------------------------------------------------
def test_a_compliant_admission():
    with tempfile.TemporaryDirectory() as tmp:
        substrate = make_substrate(tmp)
        gw = substrate.admission_gateway()
        oc = substrate.observation_channel()

        result = gw.propose(content="The sky is blue", category="claim", source="test")

        assert result.verdict == AdmissionVerdict.ADMITTED, \
            f"Expected ADMITTED, got {result.verdict}: {result.reason}"
        assert result.provenance is not None, "Provenance must be set on ADMITTED"
        assert result.provenance.item_id == result.item_id, \
            "Provenance item_id must match result item_id"
        assert result.item_id is not None, "item_id must be set on ADMITTED"
        assert result.conflict_ids == [], "No conflicts expected"

        # Signal check
        signals = oc.drain()
        admitted_signals = [s for s in signals if s.signal_type == SignalType.ADMITTED]
        assert len(admitted_signals) == 1, f"Expected 1 ADMITTED signal, got {len(admitted_signals)}"
        assert admitted_signals[0].item_id == result.item_id

        print("TEST A PASSED — compliant admission")


# ---------------------------------------------------------------------------
# TEST B — Contradiction quarantine (both items preserved)
# ---------------------------------------------------------------------------
def test_b_contradiction_quarantine():
    with tempfile.TemporaryDirectory() as tmp:
        substrate = make_substrate(tmp)
        gw = substrate.admission_gateway()
        cs = substrate.contradiction_store()
        oc = substrate.observation_channel()

        r1 = gw.propose(content="The meeting is on Tuesday", category="claim", source="alice")
        r2 = gw.propose(content="The meeting is on Wednesday", category="claim", source="bob")

        assert r1.verdict == AdmissionVerdict.ADMITTED, \
            f"First item should be ADMITTED, got {r1.verdict}"
        assert r2.verdict == AdmissionVerdict.QUARANTINED, \
            f"Conflicting item should be QUARANTINED, got {r2.verdict}"
        assert len(r2.conflict_ids) >= 1, "conflict_ids must be non-empty on QUARANTINED"
        assert r1.item_id in r2.conflict_ids, "Original item must appear in conflict_ids"

        # Both items preserved in ContradictionStore
        records = cs.list_by_category("claim")
        assert len(records) >= 1, "At least one contradiction record expected"

        all_item_ids = [iid for rec in records for iid in rec.item_ids]
        assert r1.item_id in all_item_ids, "Original item must be in quarantine record"
        assert r2.item_id in all_item_ids, "Conflicting item must be in quarantine record"

        # ContradictionStore.count()
        assert cs.count() >= 1

        # list_involving
        involving = cs.list_involving(r1.item_id)
        assert len(involving) >= 1

        # Signal check
        signals = oc.drain()
        quarantined_signals = [s for s in signals if s.signal_type == SignalType.QUARANTINED]
        assert len(quarantined_signals) >= 1, "QUARANTINED signal expected"

        print("TEST B PASSED — contradiction quarantine, both items preserved")


# ---------------------------------------------------------------------------
# TEST C — ObservationGap (unknown category → typed signal, not silence)
# STUB: Signal assertion deferred to Session 080 (full ObservationChannel).
# Verdict and item_id assertions run now.
# ---------------------------------------------------------------------------
def test_c_observation_gap():
    with tempfile.TemporaryDirectory() as tmp:
        substrate = make_substrate(tmp)
        gw = substrate.admission_gateway()
        oc = substrate.observation_channel()

        result = gw.propose(
            content="Something unknowable",
            category="UNKNOWN_CATEGORY_XYZ",
            source="test",
        )

        assert result.verdict == AdmissionVerdict.REJECTED, \
            f"Unknown category must be REJECTED, got {result.verdict}"
        assert result.item_id is None, \
            "No item_id must be assigned for unknown category"

        # Signal check (wired already in stub)
        signals = oc.drain()
        gap_signals = [s for s in signals if s.signal_type == SignalType.OBSERVATION_GAP]
        assert len(gap_signals) >= 1, \
            f"OBSERVATION_GAP signal expected, got signals: {[s.signal_type for s in signals]}"
        assert gap_signals[0].category == "UNKNOWN_CATEGORY_XYZ", \
            f"Gap signal must carry the unknown category"

        print("TEST C PASSED — ObservationGap signal emitted for unknown category")


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_a_compliant_admission()
    test_b_contradiction_quarantine()
    test_c_observation_gap()
    print("\nAll proof-condition tests PASSED.")
