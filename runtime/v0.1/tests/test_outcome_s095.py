"""
test_outcome_s095.py — C1 Outcome Test (Session 095, ADR-016 C1)

ADR-016 C1: "Governance produces measurably more coherent outcomes than baseline."

The Kill Test (Sessions 080-094) proved that governance FIRES and baseline
doesn't — governance is present vs absent. Necessary but not sufficient.

The Outcome Test asks a harder question:
  After processing the same inputs, is the final STATE more coherent under
  governance than under no governance?

--- Design (Session 095) ---

Consumer pair used: GovernedTaskPlanner + BaselinePlanManager.
Rationale: GovernedTaskPlanner has TWO explicit singular constraints
(plan-goal, current-task), giving the Outcome Test two independent
measurements. GovernedNotebook was not used because its plural_defaults
logic is internal; direct substrate use was not used because the Outcome
Test should be a consumer-level claim, not a primitive-level claim.

Unit of outcome coherence (singular categories):
  The number of contradictory items simultaneously held as admitted truth.
  Singular categories carry an "at-most-one" contract. Any count > 1
  is a constraint violation — incoherence by definition.

Measurement — constraint_violations(planner, singular_categories):
  For each singular category: count admitted items.
  violation_count += max(0, count - 1)
  Sum across all singular categories.

Comparison:
  - Feed identical adversarial input to GovernedTaskPlanner and
    BaselinePlanManager (same operations, same order).
  - Measure constraint_violations in final state of each.
  - Assert: governed_violations == 0 (structural guarantee).
  - Assert: baseline_violations >= 1 (no enforcement).
  - Assert: governed_violations < baseline_violations (C1 core claim).

Falsifiability:
  The test FAILS if baseline achieves 0 violations (it has no mechanism
  to do so) OR if governance allows violations (substrate bug). Either
  is a genuine signal.

I5 (Observable Repair Loops):
  Every governance conflict yields a RepairSuggestion. The Outcome Test
  verifies "more coherent" is not silent suppression — it is structured,
  actionable governance.

Session 095. ADR-016 C1 design.
"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from task_planner.governed_task_planner import GovernedTaskPlanner
from task_planner.baseline_plan_manager import BaselinePlanManager

SINGULAR_CATEGORIES = ["plan-goal", "current-task"]


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

def constraint_violations(planner, categories=SINGULAR_CATEGORIES) -> dict:
    """
    Count singular-category constraint violations.
    Returns dict: {category: violation_count} and "total".

    A violation is: (admitted_count - 1) for any count > 1.
    Governed planner enforces 0; baseline may hold N > 1.
    """
    result = {}
    total = 0
    for cat in categories:
        items = planner.query(cat)
        v = max(0, len(items) - 1)
        result[cat] = v
        total += v
    result["total"] = total
    return result


# ---------------------------------------------------------------------------
# Adversarial input stream — designed to maximise singular violations
# ---------------------------------------------------------------------------

def feed_adversarial_inputs(planner_gov, planner_base):
    """
    Feed identical adversarial operations to both planners.
    Returns list of (op, result_gov, result_base).
    """
    ops = [
        # plan-goal: 3 attempts (only first should be admitted under governance)
        ("set_goal", "Build the governed-cognition substrate v1.0", "session-095"),
        ("set_goal", "Switch direction: focus on theoretical foundations only", "session-challenge"),
        ("set_goal", "Third competing goal: publish paper before building", "session-challenge-2"),

        # current-task: 3 attempts (only first should be admitted under governance)
        ("start_task", "Write ADR-012 amendment for Gate B", "session-095"),
        ("start_task", "Write C1 Outcome Test simultaneously", "session-095-b"),
        ("start_task", "Also do session close documentation now", "session-095-c"),

        # plural categories — all should be admitted by both
        ("queue_task", "Design Outcome Test measurement unit", "session-095"),
        ("queue_task", "Implement test_outcome_s095.py", "session-095"),
        ("queue_task", "Run full test suite", "session-095"),
        ("add_note", "C1 design: unit = constraint violations in final state", "session-095"),
    ]

    results = []
    for op, content, source in ops:
        r_gov = getattr(planner_gov, op)(content, source)
        r_base = getattr(planner_base, op)(content, source)
        results.append((op, content, r_gov, r_base))
    return results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_outcome_governed_zero_violations():
    """
    After adversarial input, GovernedTaskPlanner has 0 singular-category
    violations. Governance provides a structural guarantee, not probabilistic.
    """
    with tempfile.TemporaryDirectory() as tmp_g,          tempfile.TemporaryDirectory() as tmp_b:

        gov = GovernedTaskPlanner(storage_path=tmp_g)
        base = BaselinePlanManager(storage_path=tmp_b)

        feed_adversarial_inputs(gov, base)

        violations = constraint_violations(gov)
        assert violations["total"] == 0, (
            f"Governed state has {violations['total']} constraint violations: "
            f"{violations}. Singular-category guarantee broken (substrate bug)."
        )

        print(f"  Governed violations: {violations}")
    print("PASS: test_outcome_governed_zero_violations")


def test_outcome_baseline_has_violations():
    """
    After adversarial input, BaselinePlanManager has >= 1 singular-category
    violations. Baseline has no constraint enforcement.
    """
    with tempfile.TemporaryDirectory() as tmp_g,          tempfile.TemporaryDirectory() as tmp_b:

        gov = GovernedTaskPlanner(storage_path=tmp_g)
        base = BaselinePlanManager(storage_path=tmp_b)

        feed_adversarial_inputs(gov, base)

        violations = constraint_violations(base)
        assert violations["total"] >= 1, (
            f"Baseline has {violations['total']} violations — expected >= 1. "
            f"Baseline has gained constraint enforcement it should not have."
        )
        # Each singular category had 3 conflicting inputs → 2 violations each
        assert violations["plan-goal"] == 2, (
            f"plan-goal: expected 2 violations (3 items admitted), "
            f"got {violations['plan-goal']}"
        )
        assert violations["current-task"] == 2, (
            f"current-task: expected 2 violations (3 items admitted), "
            f"got {violations['current-task']}"
        )

        print(f"  Baseline violations: {violations}")
    print("PASS: test_outcome_baseline_has_violations")


def test_outcome_governed_strictly_better():
    """
    Core C1 test: governed_violations < baseline_violations on identical input.
    This is the Outcome Test — the comparison the Kill Test could not make.

    Kill Test:  does governance FIRE?       (yes/no)
    Outcome Test: is the final STATE better? (measured difference)
    """
    with tempfile.TemporaryDirectory() as tmp_g,          tempfile.TemporaryDirectory() as tmp_b:

        gov = GovernedTaskPlanner(storage_path=tmp_g)
        base = BaselinePlanManager(storage_path=tmp_b)

        feed_adversarial_inputs(gov, base)

        gov_v = constraint_violations(gov)
        base_v = constraint_violations(base)

        assert gov_v["total"] < base_v["total"], (
            f"C1 FAILED: governed={gov_v['total']}, baseline={base_v['total']}. "
            f"Governance did not produce more coherent final state."
        )
        assert gov_v["total"] == 0, (
            f"Governed violations = {gov_v['total']}, expected 0."
        )

        improvement = base_v["total"] - gov_v["total"]
        print(f"  Governed violations:  {gov_v['total']}  (per category: {gov_v})")
        print(f"  Baseline violations:  {base_v['total']}  (per category: {base_v})")
        print(f"  Improvement:          {improvement} fewer violations under governance")

    print("PASS: test_outcome_governed_strictly_better")


def test_outcome_plural_categories_unaffected():
    """
    Plural categories (pending-task, plan-note) accumulate in both planners.
    Governance does not block plural entries — coexistence is their contract.
    """
    with tempfile.TemporaryDirectory() as tmp_g,          tempfile.TemporaryDirectory() as tmp_b:

        gov = GovernedTaskPlanner(storage_path=tmp_g)
        base = BaselinePlanManager(storage_path=tmp_b)

        feed_adversarial_inputs(gov, base)

        # 3 queued tasks + 1 note were fed to both
        gov_pending = gov.query("pending-task")
        base_pending = base.query("pending-task")
        gov_notes = gov.query("plan-note")
        base_notes = base.query("plan-note")

        assert len(gov_pending) == 3, f"Governed pending-task: expected 3, got {len(gov_pending)}"
        assert len(base_pending) == 3, f"Baseline pending-task: expected 3, got {len(base_pending)}"
        assert len(gov_notes) == 1, f"Governed plan-note: expected 1, got {len(gov_notes)}"
        assert len(base_notes) == 1, f"Baseline plan-note: expected 1, got {len(base_notes)}"

        print(f"  Plural categories: governed pending={len(gov_pending)}, "
              f"notes={len(gov_notes)} | baseline pending={len(base_pending)}, "
              f"notes={len(base_notes)}")

    print("PASS: test_outcome_plural_categories_unaffected")


def test_outcome_governance_events_count():
    """
    Governance fires exactly as many times as there are singular-category
    conflicts in the input. 3 goal-attempts + 3 task-attempts = 2+2 = 4
    governance events (first of each is admitted; 2 subsequent are quarantined
    per category).
    """
    with tempfile.TemporaryDirectory() as tmp_g,          tempfile.TemporaryDirectory() as tmp_b:

        gov = GovernedTaskPlanner(storage_path=tmp_g)
        base = BaselinePlanManager(storage_path=tmp_b)

        results = feed_adversarial_inputs(gov, base)

        gov_conflicts = [r_g for (op, c, r_g, r_b) in results if r_g.status == "conflict"]
        base_conflicts = base.list_conflicts()

        # 2 extra goal attempts + 2 extra task attempts = 4 conflicts
        assert len(gov_conflicts) == 4, (
            f"Expected 4 governance events, got {len(gov_conflicts)}"
        )
        # Baseline: heuristic may find some but they are post-hoc
        # Governance: structural, pre-write interception
        print(f"  Governed conflicts (pre-write):   {len(gov_conflicts)}")
        print(f"  Baseline conflicts (post-hoc):    {len(base_conflicts)}")
        print(f"  Key distinction: governed blocks BEFORE write; "
              f"baseline detects AFTER (if at all)")

    print("PASS: test_outcome_governance_events_count")


def test_outcome_repair_on_every_conflict():
    """
    I5 (Observable Repair Loops): every governance conflict has a RepairSuggestion.
    'More coherent' is not silent suppression — it is structured, actionable output.
    """
    with tempfile.TemporaryDirectory() as tmp_g,          tempfile.TemporaryDirectory() as tmp_b:

        gov = GovernedTaskPlanner(storage_path=tmp_g)
        base = BaselinePlanManager(storage_path=tmp_b)

        results = feed_adversarial_inputs(gov, base)

        store = gov._substrate.contradiction_store()
        all_contradictions = store.list_all()

        repairs_found = 0
        for contradiction in all_contradictions:
            repair = store.get_repair(contradiction.quarantine_id)
            assert repair is not None, (
                f"No RepairSuggestion for quarantine {contradiction.quarantine_id}"
            )
            assert repair.incoming_content is not None
            assert len(repair.resolution_pathways) == 3
            assert repair.existing_items, "At least one existing item must be in repair"
            repairs_found += 1

        assert repairs_found == 4, (
            f"Expected 4 RepairSuggestions (one per conflict), got {repairs_found}"
        )

        print(f"  {repairs_found} conflicts, {repairs_found} RepairSuggestions (100%)")
        print(f"  Every conflict is actionable (I5 confirmed)")

    print("PASS: test_outcome_repair_on_every_conflict")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_c1_summary():
    with tempfile.TemporaryDirectory() as tmp_g,          tempfile.TemporaryDirectory() as tmp_b:

        gov = GovernedTaskPlanner(storage_path=tmp_g)
        base = BaselinePlanManager(storage_path=tmp_b)
        feed_adversarial_inputs(gov, base)

        gov_v = constraint_violations(gov)
        base_v = constraint_violations(base)

    print()
    print("C1 Outcome Test summary:")
    print(f"  Governed final state:   {gov_v['total']} constraint violations")
    print(f"  Baseline final state:   {base_v['total']} constraint violations")
    print(f"  Improvement:            {base_v['total'] - gov_v['total']} "
          f"(governance structural guarantee: 0 violations)")
    print()
    print("What C1 claims (supported by this test):")
    print("  - After identical adversarial input, governed state is measurably")
    print("    more coherent than baseline on singular-category constraints.")
    print("  - Governance provides a STRUCTURAL guarantee (0 violations),")
    print("    not a probabilistic improvement.")
    print("  - Every governance intervention is accompanied by a RepairSuggestion.")
    print()
    print("Honest scope limitations:")
    print("  - Input stream is adversarial/synthetic, not real-world usage.")
    print("  - Coherence measurement covers singular-category integrity only.")
    print("    Temporal, epistemic, and coordination coherence not yet measured.")
    print("  - BaselinePlanManager could be upgraded to enforce constraints;")
    print("    the comparison proves governance works, not that baselines can't.")
    print("  - Measurement is count-based, not semantic.")


if __name__ == "__main__":
    print("=" * 60)
    print("Session 095 — C1 Outcome Test (ADR-016 C1)")
    print("=" * 60)

    test_outcome_governed_zero_violations()
    test_outcome_baseline_has_violations()
    test_outcome_governed_strictly_better()
    test_outcome_plural_categories_unaffected()
    test_outcome_governance_events_count()
    test_outcome_repair_on_every_conflict()

    print_c1_summary()

    print("=" * 60)
    print("ALL OUTCOME TESTS PASSED")
    print("ADR-016 C1: SUPPORTED")
    print("  — singular-category coherence, adversarial input stream,")
    print("    structural guarantee (0 governed violations vs 4 baseline)")
    print("=" * 60)
