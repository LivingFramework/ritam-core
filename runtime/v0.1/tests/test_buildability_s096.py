"""
test_buildability_s096.py — C3 Buildability Test (Session 096, ADR-016 C3)

ADR-016 C3: "A third party can build a governed consumer from the substrate,
following only API_SPEC.md and the runtime source, without prior knowledge of RITAM."

This test verifies that GovernedDecisionLog — built from BUILDABILITY_PACKET.md
alone — obeys the same structural guarantees as GovernedNotebook and
GovernedTaskPlanner (the two established consumers).

Success criteria (from the buildability packet):
1. set_decision() with conflicting decision → status="conflict" (governance fires)
2. Conflict result carries a RepairSuggestion with >= 1 resolution pathway
3. After retraction, re-calling set_decision() → status="admitted"
4. add_rationale() always returns status="admitted"
5. list_conflicts() returns the quarantined conflict

Additionally records the C3 gaps found during the build (see governed_decision_log.py).
"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from decision_log.governed_decision_log import GovernedDecisionLog


def test_c3_criterion_1_governance_fires_on_conflict():
    """
    Criterion 1: set_decision() with a conflicting decision → status="conflict".
    The consumer — built from the packet — correctly uses the singular-category
    enforcement provided by the substrate.
    """
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedDecisionLog(storage_path=tmp)

        # First decision admitted
        r1 = log.set_decision(
            "Use symbolic governance layer for contradiction detection.",
            "team-architect"
        )
        assert r1.status == "admitted", f"Expected admitted, got {r1.status}"
        assert r1.item_id is not None

        # Conflicting decision → governance fires
        r2 = log.set_decision(
            "Use neural embeddings for contradiction detection.",
            "team-ml"
        )
        assert r2.status == "conflict", (
            f"Expected conflict, got {r2.status}. "
            f"Governance did not fire on conflicting decision."
        )
        assert len(r2.conflict_with) >= 1, "conflict_with must identify the existing item"

    print("PASS: test_c3_criterion_1_governance_fires_on_conflict")


def test_c3_criterion_2_repair_suggestion_present():
    """
    Criterion 2: Conflict result carries a RepairSuggestion with >= 1 pathway.
    I5 (Observable Repair Loops) is confirmed in the new consumer context.
    """
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedDecisionLog(storage_path=tmp)

        log.set_decision("Decision A: ship incrementally.", "pm")
        r2 = log.set_decision("Decision B: rewrite first, then ship.", "cto")

        assert r2.status == "conflict"
        assert r2.repair is not None, (
            "RepairSuggestion must be present on conflict. "
            "C2 (Repair) is not surfacing through this consumer."
        )
        assert len(r2.repair.resolution_pathways) >= 1, (
            f"Expected >= 1 pathway, got {len(r2.repair.resolution_pathways)}"
        )
        pathway_ids = {p.pathway_id for p in r2.repair.resolution_pathways}
        assert "RETRACT_EXISTING" in pathway_ids, "RETRACT_EXISTING pathway must be present"

        print(f"  Repair: {len(r2.repair.resolution_pathways)} pathways, "
              f"ids={sorted(pathway_ids)}")

    print("PASS: test_c3_criterion_2_repair_suggestion_present")


def test_c3_criterion_3_retract_and_readmit():
    """
    Criterion 3: After retracting the existing decision, re-proposing returns admitted.
    The RETRACT_EXISTING pathway is executable through this consumer.
    """
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedDecisionLog(storage_path=tmp)

        r1 = log.set_decision("Initial decision: build MVP first.", "founder")
        r2 = log.set_decision("Competing decision: write spec first.", "advisor")

        assert r1.status == "admitted"
        assert r2.status == "conflict"

        # Execute RETRACT_EXISTING: retract the initial decision
        retract = log.retract_decision(
            r1.item_id, "founder",
            "RETRACT_EXISTING: advisor's framing is more rigorous — spec first."
        )
        assert retract.status == "admitted", (
            f"Retraction failed: {retract.status} — {retract.message}"
        )

        # Re-admit the competing decision
        r3 = log.set_decision("Competing decision: write spec first.", "advisor")
        assert r3.status == "admitted", (
            f"Re-admitted decision should be ADMITTED after retraction, "
            f"got {r3.status}"
        )

        # Current decision should now be the re-admitted one
        current = log.current_decision()
        assert current is not None
        assert "spec first" in current["content"]

    print("PASS: test_c3_criterion_3_retract_and_readmit")


def test_c3_criterion_4_rationale_always_admitted():
    """
    Criterion 4: add_rationale() always returns admitted regardless of existing rationale.
    Plural categories coexist — no false governance firings.
    """
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedDecisionLog(storage_path=tmp)

        r1 = log.add_rationale("Symbolic governance is interpretable.", "claude")
        r2 = log.add_rationale("Neural approaches have better recall on ambiguous text.", "mahdi")
        r3 = log.add_rationale("Hybrid approaches exist but add complexity.", "gemini")

        assert r1.status == "admitted"
        assert r2.status == "admitted"
        assert r3.status == "admitted"

        rationale = log.list_rationale()
        assert len(rationale) == 3, f"Expected 3 rationale items, got {len(rationale)}"

    print("PASS: test_c3_criterion_4_rationale_always_admitted")


def test_c3_criterion_5_list_conflicts():
    """
    Criterion 5: list_conflicts() returns the quarantined conflict after a governance event.
    """
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedDecisionLog(storage_path=tmp)

        log.set_decision("Focus on substrate buildability (C3).", "session-096")
        log.set_decision("Focus on substrate repair (C2).", "alternative")

        conflicts = log.list_conflicts()
        assert len(conflicts) == 1, f"Expected 1 conflict, got {len(conflicts)}"
        conflict = conflicts[0]
        assert conflict["quarantine_id"] is not None
        assert len(conflict["conflicting_items"]) == 2
        assert conflict["repair"] is not None

    print("PASS: test_c3_criterion_5_list_conflicts")


def print_c3_verdict(gaps):
    print()
    print("C3 Buildability Verdict:")
    print(f"  All 5 success criteria: PASS")
    print(f"  Gaps found during build: {len(gaps)}")
    for g in gaps:
        print(f"    {g}")
    print()
    print("C3 Assessment: SUPPORTED WITH GAPS")
    print("  The substrate IS buildable from the packet — all criteria pass.")
    print("  But 5 gaps required looking beyond the spec:")
    print("    - GAP-1 (BREAKING): singular_categories vs plural_categories mismatch [FIXED S098]")
    print("    - GAP-3 (HIGH): default behaviour of plural_categories undocumented [FIXED S098]")
    print("    - GAP-5 (HIGH): no public read API for admitted items")
    print("    - GAP-2 (MEDIUM): get_repair/mark_resolved not in base ContradictionStore spec")
    print("    - GAP-4 (LOW): RepairSuggestion import path undocumented")
    print()
    print("C3 Action Items for API_SPEC update:")
    print("  1. Fix singular_categories / plural_categories naming [DONE S098]")
    print("  2. Add get_repair() and mark_resolved() to ContradictionStore spec")
    print("  3. Add read-by-category method to AdmissionGateway (or document DB access pattern)")


if __name__ == "__main__":
    print("=" * 60)
    print("Session 096 — C3 Buildability Test (ADR-016 C3)")
    print("=" * 60)

    test_c3_criterion_1_governance_fires_on_conflict()
    test_c3_criterion_2_repair_suggestion_present()
    test_c3_criterion_3_retract_and_readmit()
    test_c3_criterion_4_rationale_always_admitted()
    test_c3_criterion_5_list_conflicts()

    gaps = [
        "GAP-1 (BREAKING): singular_categories in spec ≠ plural_categories in impl [FIXED S098]",
        "GAP-2 (MEDIUM): get_repair/mark_resolved absent from ContradictionStore spec",
        "GAP-3 (HIGH): plural_categories default behaviour inverted vs documented [FIXED S098]",
        "GAP-4 (LOW): RepairSuggestion import path undocumented",
        "GAP-5 (HIGH): no public read-by-category API; forced _db access",
    ]
    print_c3_verdict(gaps)

    print("=" * 60)
    print("ALL BUILDABILITY TESTS PASSED")
    print("ADR-016 C3: SUPPORTED WITH GAPS (5 spec gaps identified)")
    print("=" * 60)
