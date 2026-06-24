"""
test_singular_categories_s098.py — GAP-1 Regression Test (Session 098)

Proves that singular_categories in SubstrateConfig correctly enforces at-most-one
semantics after the GAP-1 rename from plural_categories.

GAP-1 was BREAKING: BUILDABILITY_PACKET.md used singular_categories but the
implementation used plural_categories with inverted logic. A cold builder would
silently misconfigure governance. Fixed Session 098.

These tests prove:
  1. singular_categories=["X"] → second X admission is QUARANTINED
  2. Category NOT in singular_categories → multiple entries ADMITTED (plural default)
  3. singular_categories=[] (default) → all categories plural (permissive default)
  4. singular_categories=["X","Y"] → both X and Y enforce at-most-one independently
  5. singular_categories does not affect categories not listed (plural coexistence intact)
"""
from __future__ import annotations

import tempfile

from ritam.runtime.v01 import (
    AdmissionVerdict,
    Substrate,
    SubstrateConfig,
)


def make_substrate(tmp_path: str, categories: list, singular: list | None = None) -> tuple:
    config = SubstrateConfig(
        storage_path=tmp_path,
        known_categories=categories,
        singular_categories=singular or [],
    )
    s = Substrate(config)
    return s.admission_gateway(), s.contradiction_store()


# ---------------------------------------------------------------------------
# Test 1: singular_categories=["X"] quarantines second X admission
# ---------------------------------------------------------------------------
def test_singular_quarantines_second_entry():
    """
    Core GAP-1 regression: passing singular_categories=["active-decision"]
    must enforce at-most-one for active-decision.
    This is the exact usage pattern a cold builder would use from the spec.
    """
    with tempfile.TemporaryDirectory() as tmp:
        gw, store = make_substrate(
            tmp,
            categories=["active-decision", "decision-rationale"],
            singular=["active-decision"],
        )

        r1 = gw.propose("Adopt microservices architecture.", "active-decision", "cto")
        assert r1.verdict == AdmissionVerdict.ADMITTED, \
            f"First active-decision must be ADMITTED, got {r1.verdict}"

        r2 = gw.propose("Adopt monolith architecture.", "active-decision", "board")
        assert r2.verdict == AdmissionVerdict.QUARANTINED, \
            f"Second active-decision must be QUARANTINED (singular), got {r2.verdict}"

        assert r2.repair is not None, "Quarantined entry must have a RepairSuggestion"
        assert r2.repair.category == "active-decision"
        assert len(r2.repair.resolution_pathways) == 3

        print("PASS: test_singular_quarantines_second_entry")


# ---------------------------------------------------------------------------
# Test 2: plural default — category NOT in singular_categories → multiple admitted
# ---------------------------------------------------------------------------
def test_plural_default_admits_multiple():
    """
    Categories not listed in singular_categories must be plural by default.
    Multiple entries in the same plural category must ALL be ADMITTED.
    This is the inverted half of the GAP-1 fix: the default must be permissive.
    """
    with tempfile.TemporaryDirectory() as tmp:
        gw, _ = make_substrate(
            tmp,
            categories=["decision-rationale", "active-decision"],
            singular=["active-decision"],  # only active-decision is singular
        )

        r1 = gw.propose("Reduces coupling.", "decision-rationale", "engineer-a")
        r2 = gw.propose("Enables independent scaling.", "decision-rationale", "engineer-b")
        r3 = gw.propose("Matches team expertise.", "decision-rationale", "engineer-c")

        assert r1.verdict == AdmissionVerdict.ADMITTED, f"Rationale 1: {r1.verdict}"
        assert r2.verdict == AdmissionVerdict.ADMITTED, f"Rationale 2: {r2.verdict}"
        assert r3.verdict == AdmissionVerdict.ADMITTED, f"Rationale 3: {r3.verdict}"

        print("PASS: test_plural_default_admits_multiple")


# ---------------------------------------------------------------------------
# Test 3: singular_categories=[] (default) → all plural, nothing quarantined
# ---------------------------------------------------------------------------
def test_empty_singular_all_plural():
    """
    singular_categories=[] (the default when None is passed) means all categories
    are plural. No entry should ever be quarantined, even in the same category.
    This was the pre-GAP-1-fix default for plural_categories=[] too — but with
    inverted semantics: empty plural_categories meant ALL SINGULAR. Now empty
    singular_categories means ALL PLURAL (permissive default).
    """
    with tempfile.TemporaryDirectory() as tmp:
        gw, store = make_substrate(
            tmp,
            categories=["claim"],
            singular=[],  # explicit empty — all plural
        )

        r1 = gw.propose("Claim A", "claim", "src-1")
        r2 = gw.propose("Claim B", "claim", "src-2")
        r3 = gw.propose("Claim C", "claim", "src-3")

        assert r1.verdict == AdmissionVerdict.ADMITTED
        assert r2.verdict == AdmissionVerdict.ADMITTED
        assert r3.verdict == AdmissionVerdict.ADMITTED
        assert store.count() == 0, "No contradictions: all categories are plural"

        print("PASS: test_empty_singular_all_plural")


# ---------------------------------------------------------------------------
# Test 4: multiple independent singular categories enforced simultaneously
# ---------------------------------------------------------------------------
def test_multiple_singular_categories_independent():
    """
    singular_categories=["plan-goal", "current-task"] must enforce at-most-one
    on BOTH independently. This matches GovernedTaskPlanner's configuration.
    Conflict on plan-goal must not affect current-task enforcement and vice versa.
    """
    with tempfile.TemporaryDirectory() as tmp:
        gw, _ = make_substrate(
            tmp,
            categories=["plan-goal", "current-task", "pending-task"],
            singular=["plan-goal", "current-task"],
        )

        # First entries — both admitted
        gw.propose("Build governed substrate.", "plan-goal", "session-001")
        gw.propose("Implement AdmissionGateway.", "current-task", "session-079")

        # Second goal — quarantined
        r_goal = gw.propose("Build consumer applications.", "plan-goal", "session-002")
        assert r_goal.verdict == AdmissionVerdict.QUARANTINED, \
            f"Second plan-goal must be QUARANTINED, got {r_goal.verdict}"

        # Second task — quarantined
        r_task = gw.propose("Implement ContradictionStore.", "current-task", "session-080")
        assert r_task.verdict == AdmissionVerdict.QUARANTINED, \
            f"Second current-task must be QUARANTINED, got {r_task.verdict}"

        # Plural category — all admitted
        r_p1 = gw.propose("Pending: write tests.", "pending-task", "session-080")
        r_p2 = gw.propose("Pending: write docs.", "pending-task", "session-080")
        assert r_p1.verdict == AdmissionVerdict.ADMITTED
        assert r_p2.verdict == AdmissionVerdict.ADMITTED

        print("PASS: test_multiple_singular_categories_independent")


# ---------------------------------------------------------------------------
# Test 5: retract singular + re-admit proves singular slot is released
# ---------------------------------------------------------------------------
def test_singular_slot_released_after_retract():
    """
    After retracting the current holder of a singular category, a new entry
    must be ADMITTED (not quarantined). The singular slot is freed by retraction.
    """
    with tempfile.TemporaryDirectory() as tmp:
        gw, _ = make_substrate(
            tmp,
            categories=["active-decision"],
            singular=["active-decision"],
        )

        r1 = gw.propose("Decision A: use PostgreSQL.", "active-decision", "dba")
        assert r1.verdict == AdmissionVerdict.ADMITTED

        # Retract the existing decision
        retract_result = gw.retract(r1.item_id, source="dba", reason="reconsidering stack")
        assert retract_result.verdict == AdmissionVerdict.ADMITTED,             f"retract() must return ADMITTED on success, got {retract_result.verdict}"

        # Now a new decision must be admitted (slot is free)
        r2 = gw.propose("Decision B: use SQLite for prototyping.", "active-decision", "dev")
        assert r2.verdict == AdmissionVerdict.ADMITTED, \
            f"After retract, new singular entry must be ADMITTED, got {r2.verdict}"

        print("PASS: test_singular_slot_released_after_retract")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_singular_quarantines_second_entry()
    test_plural_default_admits_multiple()
    test_empty_singular_all_plural()
    test_multiple_singular_categories_independent()
    test_singular_slot_released_after_retract()
    print("\nAll GAP-1 regression tests PASSED.")
