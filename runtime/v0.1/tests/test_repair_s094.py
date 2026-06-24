"""
test_repair_s094.py — Repair primitive test (Session 094, ADR-016 C2)

Proves that:
1. When a governance event fires (QUARANTINED), the AdmissionResult contains
   a RepairSuggestion with both sides of the conflict.
2. The RepairSuggestion names the rule that triggered.
3. Three resolution pathways are present, each with pathway_id, description,
   and action_required.
4. The repair suggestion is retrievable from ContradictionStore.get_repair().
5. A human can pick a pathway and close the loop with mark_resolved().
6. mark_resolved() records the resolution note and marks the record resolved.

This test proves C2 (Repair) of ADR-016 is operational.
I5 (Observable Repair Loops) is now implemented.
"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ritam.runtime.v01 import (
    Substrate,
    SubstrateConfig,
    AdmissionVerdict,
)


def make_substrate(tmp_path, categories, singular=None):
    config = SubstrateConfig(
        storage_path=tmp_path,
        known_categories=categories,
        singular_categories=singular or [],
    )
    s = Substrate(config)
    return s.admission_gateway(), s.contradiction_store(), s.observation_channel()


def test_repair_suggestion_on_quarantine():
    """
    Core test: governance fires → RepairSuggestion is attached to AdmissionResult.
    Verifies all required fields are present and non-empty.
    """
    with tempfile.TemporaryDirectory() as tmp:
        gateway, store, _ = make_substrate(tmp, ["canonical-claim"], singular=["canonical-claim"])

        # Admit the first item
        r1 = gateway.propose(
            "Governance-layer substrate can be built from first principles.",
            "canonical-claim", "session-083"
        )
        assert r1.verdict == AdmissionVerdict.ADMITTED, f"Expected ADMITTED, got {r1.verdict}"
        assert r1.repair is None, "No repair on ADMITTED"

        # Propose a conflicting item — should trigger quarantine + repair
        r2 = gateway.propose(
            "Complete brain understanding is required before substrate design.",
            "canonical-claim", "session-challenge"
        )
        assert r2.verdict == AdmissionVerdict.QUARANTINED, f"Expected QUARANTINED, got {r2.verdict}"
        assert r2.repair is not None, "RepairSuggestion must be present on QUARANTINED"

        repair = r2.repair

        # --- C2 requirement: both sides present ---
        assert repair.incoming_content == "Complete brain understanding is required before substrate design."
        assert repair.incoming_source == "session-challenge"
        assert len(repair.existing_items) == 1, "One existing item should be present"
        existing = repair.existing_items[0]
        assert existing["content"] == "Governance-layer substrate can be built from first principles."
        assert existing["source"] == "session-083"
        assert existing["item_id"] == r1.item_id

        # --- C2 requirement: rule named ---
        assert "canonical-claim" in repair.rule_triggered
        assert ("singular" in repair.rule_triggered.lower() or
                "at most one" in repair.rule_triggered.lower())

        # --- C2 requirement: resolution pathways present ---
        assert len(repair.resolution_pathways) == 3,             f"Expected 3 pathways, got {len(repair.resolution_pathways)}"
        pathway_ids = {p.pathway_id for p in repair.resolution_pathways}
        assert "RETRACT_EXISTING" in pathway_ids
        assert "KEEP_EXISTING" in pathway_ids
        assert "HOLD_AS_CONTRADICTION" in pathway_ids

        for pathway in repair.resolution_pathways:
            assert pathway.description, f"Pathway {pathway.pathway_id} has empty description"
            assert pathway.action_required, f"Pathway {pathway.pathway_id} has empty action_required"

        # --- quarantine_id present ---
        assert repair.quarantine_id, "quarantine_id must be present"

        print("PASS: test_repair_suggestion_on_quarantine")
        return repair.quarantine_id, r1.item_id


def test_repair_retrievable_from_store():
    """
    Repair suggestion stored in DB is retrievable via ContradictionStore.get_repair().
    """
    with tempfile.TemporaryDirectory() as tmp:
        gateway, store, _ = make_substrate(tmp, ["hypothesis"], singular=["hypothesis"])

        gateway.propose("Hypothesis A: governance prevents drift.",
                        "hypothesis", "source-A")
        r = gateway.propose("Hypothesis B: governance is insufficient alone.",
                            "hypothesis", "source-B")

        assert r.verdict == AdmissionVerdict.QUARANTINED
        qid = r.repair.quarantine_id

        # Retrieve from store
        stored_repair = store.get_repair(qid)
        assert stored_repair is not None, "get_repair() must return a RepairSuggestion"
        assert stored_repair.quarantine_id == qid
        assert stored_repair.category == "hypothesis"
        assert len(stored_repair.resolution_pathways) == 3
        assert stored_repair.incoming_content == "Hypothesis B: governance is insufficient alone."
        assert len(stored_repair.existing_items) == 1
        assert stored_repair.existing_items[0]["content"] == "Hypothesis A: governance prevents drift."

        print("PASS: test_repair_retrievable_from_store")
        return qid, store, tmp


def test_mark_resolved_closes_loop():
    """
    Human picks HOLD_AS_CONTRADICTION pathway and calls mark_resolved().
    Verifies the loop closes: record marked resolved, note stored, original preserved.
    """
    with tempfile.TemporaryDirectory() as tmp:
        gateway, store, _ = make_substrate(tmp, ["hypothesis"], singular=["hypothesis"])

        gateway.propose("Hypothesis A: governance prevents drift.",
                        "hypothesis", "source-A")
        r = gateway.propose("Hypothesis B: governance is insufficient alone.",
                            "hypothesis", "source-B")
        qid = r.repair.quarantine_id

        # Before resolution
        record_before = store.get(qid)
        assert record_before.resolved == False
        assert record_before.resolution_note is None

        # Human decision: hold both as an open contradiction
        resolution = ("HOLD_AS_CONTRADICTION: Both hypotheses are under active investigation. "
                      "Neither is falsified yet.")
        success = store.mark_resolved(qid, resolution)
        assert success, "mark_resolved() must return True"

        # After resolution
        record_after = store.get(qid)
        assert record_after.resolved == True
        assert record_after.resolution_note == resolution

        # Original conflict content PRESERVED (I8 — Contradiction Visibility)
        assert len(record_after.contents) == 2, "Both items must still be preserved"

        # Repair suggestion still retrievable
        repair = store.get_repair(qid)
        assert repair is not None, "RepairSuggestion still accessible after resolution"

        print("PASS: test_mark_resolved_closes_loop")


def test_retract_existing_pathway_in_practice():
    """
    Simulates a human choosing RETRACT_EXISTING:
    - Admit item A (current-task)
    - Conflict with item B → QUARANTINED + RepairSuggestion
    - Human picks RETRACT_EXISTING: retracts A, re-submits B
    - B is now admitted; A is retracted; contradiction marked resolved
    """
    with tempfile.TemporaryDirectory() as tmp:
        gateway, store, _ = make_substrate(tmp, ["current-task"], singular=["current-task"])

        # Admit task A
        r_a = gateway.propose("Implement AdmissionGateway repair output",
                               "current-task", "session-094-start")
        assert r_a.verdict == AdmissionVerdict.ADMITTED
        item_a_id = r_a.item_id

        # Propose conflicting task B
        r_b = gateway.propose("Write test_repair_s094.py",
                               "current-task", "session-094-mid")
        assert r_b.verdict == AdmissionVerdict.QUARANTINED
        repair = r_b.repair
        assert repair is not None

        # Human reads repair and picks RETRACT_EXISTING
        retract_pathway = next(
            p for p in repair.resolution_pathways if p.pathway_id == "RETRACT_EXISTING"
        )
        assert retract_pathway is not None

        # Execute: retract A, re-submit B
        retract_result = gateway.retract(
            item_a_id, "human-reviewer",
            "Task superseded: writing the test is now the active task."
        )
        assert retract_result.verdict == AdmissionVerdict.ADMITTED  # retraction accepted

        # Re-submit B — should now be admitted (A is retracted, no conflict)
        r_b2 = gateway.propose("Write test_repair_s094.py",
                                "current-task", "session-094-mid")
        assert r_b2.verdict == AdmissionVerdict.ADMITTED, (
            f"Re-submitted item should be ADMITTED after retraction, got {r_b2.verdict}"
        )

        # Close the loop
        store.mark_resolved(
            repair.quarantine_id,
            "RETRACT_EXISTING: Task A superseded by Task B. A retracted, B re-admitted."
        )

        record = store.get(repair.quarantine_id)
        assert record.resolved == True
        assert "RETRACT_EXISTING" in record.resolution_note

        print("PASS: test_retract_existing_pathway_in_practice")


def test_no_repair_on_admitted():
    """repair field is None for non-quarantine results."""
    with tempfile.TemporaryDirectory() as tmp:
        gateway, store, _ = make_substrate(tmp, ["observation"])
        r = gateway.propose("Governance fires on abrupt shifts.", "observation", "test")
        assert r.verdict == AdmissionVerdict.ADMITTED
        assert r.repair is None
        print("PASS: test_no_repair_on_admitted")


def test_no_repair_on_rejected():
    """repair field is None for rejected items (category unknown)."""
    with tempfile.TemporaryDirectory() as tmp:
        gateway, store, _ = make_substrate(tmp, ["canonical-claim"], singular=["canonical-claim"])
        r = gateway.propose("Some content", "unknown-category", "test")
        assert r.verdict == AdmissionVerdict.REJECTED
        assert r.repair is None
        print("PASS: test_no_repair_on_rejected")


if __name__ == "__main__":
    print("=" * 60)
    print("Session 094 — Repair Primitive Test (ADR-016 C2)")
    print("=" * 60)

    test_repair_suggestion_on_quarantine()
    test_repair_retrievable_from_store()
    test_mark_resolved_closes_loop()
    test_retract_existing_pathway_in_practice()
    test_no_repair_on_admitted()
    test_no_repair_on_rejected()

    print()
    print("=" * 60)
    print("ALL TESTS PASSED")
    print()
    print("C2 (Repair) is operational:")
    print("  - Every QUARANTINED event produces a RepairSuggestion")
    print("  - Both sides of the conflict are present")
    print("  - The rule that triggered is named")
    print("  - Three resolution pathways are attached")
    print("  - Repair is retrievable from ContradictionStore")
    print("  - mark_resolved() closes the loop (I5 implemented)")
    print("=" * 60)
