"""
Kill Test 11 — GovernedTaskPlanner vs BaselinePlanManager.
Session 091.

This test validates the third substrate consumer (GovernedTaskPlanner)
and assesses whether it is materially different from the prior two
(GovernedNotebook, GovernedAgentMemory).

Kill condition:
  If GovernedTaskPlanner's governance_event_count() after the concurrent-task
  admission attempt equals BaselinePlanManager's governance_event_count()
  (both 0, or indistinguishable), the kill condition is met.

Expected:
  GovernedTaskPlanner: second start_task() → QUARANTINED. 1 governance event.
  BaselinePlanManager: second start_task() → stored silently. 0 governance events.
  Kill condition NOT met.

Propositions:
  G:  plan-goal     "Implement GovernedTaskPlanner and run Kill Test 11."
  T1: current-task  "Write governed_task_planner.py and baseline_plan_manager.py."
  P1: pending-task  "Write test_kill_test_11.py."
  P2: pending-task  "Run Kill Test 11 and record fixture."
  P3: pending-task  "Assess substrate-generality claim."
  C1: completed-task "Design GovernedTaskPlanner category vocabulary (Session 091)."
  N1: plan-note     "Two SINGULAR categories: plan-goal and current-task."
  T2: current-task  "Run Kill Test 11." ← CONCURRENT TASK — governance fires here

T2 is the adversarial proposition. In a real agent, claiming to work on
'Run Kill Test 11' while 'Write governed_task_planner.py...' is already
the current task represents a coherence failure. The governed substrate
catches it; the baseline does not.

Second singular test:
  G2: plan-goal  "Redirect: validate substrate-generality instead." ← GOAL CHANGE
  G2 tests the plan-goal singular invariant independently.
  Expected: QUARANTINED (2nd governance event in governed; 0 in baseline).

Cumulative Kill Test after S091:
  Expected: 12 governance events / 12 runs / 0 baseline.
  (10 prior + T2 quarantine + G2 quarantine = 12 events, same run counts as 11 runs
   but this test has 2 governance events in 1 run.)
  Actually counting runs: each Kill Test script = 1 run. So: 11 runs total.
  Governance events: 10 prior + 2 this run = 12.

No LLM, no embeddings, no async (Appendix B, API_SPEC.md).
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from task_planner.governed_task_planner import GovernedTaskPlanner
from task_planner.baseline_plan_manager import BaselinePlanManager


# ---------------------------------------------------------------------------
# Propositions
# ---------------------------------------------------------------------------

PLAN_GOAL = "Implement GovernedTaskPlanner and run Kill Test 11."
TASK_1 = "Write governed_task_planner.py and baseline_plan_manager.py."
PENDING_1 = "Write test_kill_test_11.py."
PENDING_2 = "Run Kill Test 11 and record fixture."
PENDING_3 = "Assess substrate-generality claim."
COMPLETED_1 = "Design GovernedTaskPlanner category vocabulary (Session 091)."
NOTE_1 = "Two SINGULAR categories tested: plan-goal and current-task. First consumer with dual singular constraints."

# Adversarial propositions
TASK_2 = "Run Kill Test 11."  # T2 — concurrent task (singular violation)
GOAL_2 = "Redirect: validate substrate-generality claim instead."  # G2 — goal change


def print_section(label: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")


# ---------------------------------------------------------------------------
# Governed
# ---------------------------------------------------------------------------

def run_governed(tmpdir: str) -> dict:
    print_section("GovernedTaskPlanner")
    planner = GovernedTaskPlanner(tmpdir)

    # --- Legitimate plan content ---
    r_g = planner.set_goal(PLAN_GOAL, "session-091")
    print(f"  set_goal        → {r_g.status}")

    r_t1 = planner.start_task(TASK_1, "session-091")
    print(f"  start_task T1   → {r_t1.status}")

    planner.queue_task(PENDING_1, "session-091")
    planner.queue_task(PENDING_2, "session-091")
    planner.queue_task(PENDING_3, "session-091")
    planner.complete_task(COMPLETED_1, "session-091")
    planner.add_note(NOTE_1, "session-091")
    print(f"  queued 3, completed 1, noted 1 → all stored")

    # --- Adversarial: concurrent task (T2) ---
    print(f"\n  [ADVERSARIAL] start_task T2 — concurrent task:")
    print(f"  Existing: '{TASK_1[:60]}...'")
    print(f"  Incoming: '{TASK_2}'")
    r_t2 = planner.start_task(TASK_2, "adversarial-s091")
    print(f"  Result: status={r_t2.status}, conflict_with={r_t2.conflict_with}")
    print(f"  Message: {r_t2.message}")

    # --- Adversarial: goal change (G2) ---
    print(f"\n  [ADVERSARIAL] set_goal G2 — goal change:")
    print(f"  Existing: '{PLAN_GOAL[:60]}...'")
    print(f"  Incoming: '{GOAL_2}'")
    r_g2 = planner.set_goal(GOAL_2, "adversarial-s091")
    print(f"  Result: status={r_g2.status}, conflict_with={r_g2.conflict_with}")
    print(f"  Message: {r_g2.message}")

    gov_events = planner.governance_event_count()
    conflicts = planner.list_conflicts()
    current_tasks = planner.query("current-task")
    plan_goals = planner.query("plan-goal")

    print(f"\n  Governance events: {gov_events}")
    print(f"  Contradiction store entries: {len(conflicts)}")
    print(f"  current-task in store (admitted): {len(current_tasks)}")
    print(f"  plan-goal in store (admitted):    {len(plan_goals)}")

    return {
        "task_2_status": r_t2.status,
        "task_2_conflict_with": r_t2.conflict_with,
        "goal_2_status": r_g2.status,
        "goal_2_conflict_with": r_g2.conflict_with,
        "governance_events": gov_events,
        "contradictions_stored": len(conflicts),
        "admitted_current_tasks": len(current_tasks),
        "admitted_plan_goals": len(plan_goals),
    }


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------

def run_baseline(tmpdir: str) -> dict:
    print_section("BaselinePlanManager")
    planner = BaselinePlanManager(tmpdir)

    r_g = planner.set_goal(PLAN_GOAL, "session-091")
    print(f"  set_goal        → {r_g['status']}")

    r_t1 = planner.start_task(TASK_1, "session-091")
    print(f"  start_task T1   → {r_t1['status']}")

    planner.queue_task(PENDING_1, "session-091")
    planner.queue_task(PENDING_2, "session-091")
    planner.queue_task(PENDING_3, "session-091")
    planner.complete_task(COMPLETED_1, "session-091")
    planner.add_note(NOTE_1, "session-091")
    print(f"  queued 3, completed 1, noted 1 → all stored")

    print(f"\n  [ADVERSARIAL] start_task T2 — concurrent task (no governance):")
    r_t2 = planner.start_task(TASK_2, "adversarial-s091")
    print(f"  Result: status={r_t2['status']} (stored silently)")

    print(f"\n  [ADVERSARIAL] set_goal G2 — goal change (no governance):")
    r_g2 = planner.set_goal(GOAL_2, "adversarial-s091")
    print(f"  Result: status={r_g2['status']} (stored silently)")

    gov_events = planner.governance_event_count()
    conflicts = planner.list_conflicts()
    current_tasks = planner.query("current-task")
    plan_goals = planner.query("plan-goal")

    print(f"\n  Governance events (always 0): {gov_events}")
    print(f"  Heuristic conflicts detected (post-hoc): {len(conflicts)}")
    print(f"  current-task in store (both stored!): {len(current_tasks)}")
    print(f"  plan-goal in store (both stored!):    {len(plan_goals)}")

    return {
        "task_2_status": r_t2["status"],
        "goal_2_status": r_g2["status"],
        "governance_events": gov_events,
        "heuristic_conflicts": len(conflicts),
        "stored_current_tasks": len(current_tasks),
        "stored_plan_goals": len(plan_goals),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> dict:
    print("\n" + "="*70)
    print("  KILL TEST 11 — GovernedTaskPlanner vs BaselinePlanManager")
    print("  Session 091 — Third consumer: materially different domain")
    print("="*70)

    with tempfile.TemporaryDirectory() as g_tmp, \
         tempfile.TemporaryDirectory() as b_tmp:
        governed = run_governed(g_tmp)
        baseline = run_baseline(b_tmp)

    # Kill condition
    print_section("Kill Condition Assessment")

    kill_condition_met = (
        governed["task_2_status"] != "conflict"
        or governed["goal_2_status"] != "conflict"
        or governed["governance_events"] == 0
        or governed["governance_events"] == baseline["governance_events"]
    )

    print(f"  Governed  T2 status          : {governed['task_2_status']}")
    print(f"  Governed  G2 status          : {governed['goal_2_status']}")
    print(f"  Governed  governance events  : {governed['governance_events']}")
    print(f"  Governed  admitted current-task entries: {governed['admitted_current_tasks']}")
    print(f"  Governed  admitted plan-goal entries   : {governed['admitted_plan_goals']}")
    print()
    print(f"  Baseline  T2 status          : {baseline['task_2_status']} (silent)")
    print(f"  Baseline  G2 status          : {baseline['goal_2_status']} (silent)")
    print(f"  Baseline  governance events  : {baseline['governance_events']} (always 0)")
    print(f"  Baseline  stored current-task entries: {baseline['stored_current_tasks']}")
    print(f"  Baseline  stored plan-goal entries   : {baseline['stored_plan_goals']}")
    print()
    print(f"  Kill condition met: {kill_condition_met}")

    if kill_condition_met:
        print("  ⚠  KILL CONDITION MET.")
    else:
        print("  ✓  Kill condition NOT met.")
        print("  ✓  GovernedTaskPlanner enforces dual singular constraints.")
        print("  ✓  Both concurrent-task AND goal-change violations quarantined.")
        print("  ✓  Baseline stores both coherence failures silently.")

    # Fixture
    fixture = {
        "test": "kill_test_11",
        "session": "091",
        "description": (
            "Kill Test 11: GovernedTaskPlanner vs BaselinePlanManager. "
            "Third consumer — task-planning domain (executable work). "
            "Two singular violations tested: concurrent task (T2) + goal change (G2). "
            "First Kill Test with dual singular constraints."
        ),
        "governed": governed,
        "baseline": baseline,
        "kill_condition_met": kill_condition_met,
        "cumulative_kill_test": {
            "prior_governance_events": 10,
            "this_run_governance_events": governed["governance_events"],
            "total_governance_events": 10 + governed["governance_events"],
            "total_runs": 11,
            "baseline_events_all_runs": 0,
        },
        "materiality_note": (
            "GovernedTaskPlanner is materially different from GovernedNotebook "
            "(scientific observation) and GovernedAgentMemory (programme history). "
            "Domain: executable work. Singular invariants: one-goal + one-active-task. "
            "This is the first consumer with dual singular constraints. "
            "All three consumers use the same substrate engine with different vocabularies."
        ),
    }

    fixture_path = Path(__file__).parent / "fixtures" / "kill_test_11_s091.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(json.dumps(fixture, indent=2))
    print(f"\n  Fixture written: {fixture_path}")

    return fixture


if __name__ == "__main__":
    result = main()
    sys.exit(0 if not result["kill_condition_met"] else 1)
