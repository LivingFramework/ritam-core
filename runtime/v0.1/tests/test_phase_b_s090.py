"""
Phase B — OQ-058: Persistent Kill Test across Python process boundaries.
Session 090.

This test answers the core question of OQ-058:
  "Can governance surface contradictions that emerge organically over time
   when entries arrive across separate Python process runs?"

Architecture:
  Phase B simulates two Python processes via snapshot export/import.
  The SQLite store is ephemeral (tempdir) within each run.
  The JSON snapshot is the persistence layer between runs.

Phase B Run 1 — Seed Phase:
  Fresh GovernedAgentMemory (tempdir SQLite).
  Load 24 real RITAM programme history entries (same as Phase A).
  Includes P4b as the governing hypothesis.
  Verify: 0 governance events during seeding (content is consistent).
  Export snapshot → data/programme_memory_snapshot_phase_b_run1.json

Phase B Run 2 — Contradiction Phase (new Python "process"):
  Fresh GovernedAgentMemory (new tempdir SQLite) — simulates new process.
  load_snapshot() from Run 1 JSON — P4b is now in the store.
  Verify: 0 governance events during load (snapshot is clean).
  Propose CC2 as governing hypothesis → QUARANTINED against loaded P4b.
  Verify: 1 governance event raised.
  Export snapshot → data/programme_memory_snapshot_phase_b_run2.json

Kill condition: if CC2 is ADMITTED (gov event count remains 0 after Run 2) → KILL.
Expected: CC2 QUARANTINED → 1 governance event → kill condition NOT met.

Baseline (BaselineAgentMemory):
  Same two-run structure.
  Run 1: Seed, export.
  Run 2: Load from snapshot, propose CC2 → silently stored. 0 gov events.
  list_conflicts() detects it heuristically (post-hoc), but no governance event.

The difference: governance fires at write time in governed; only detectable
post-hoc in baseline. Cross-process persistence is the new evidence quality.

No LLM, no embeddings, no async (Appendix B, API_SPEC.md).
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_memory.governed_agent_memory import GovernedAgentMemory
from agent_memory.baseline_agent_memory import BaselineAgentMemory

# ---------------------------------------------------------------------------
# Programme history (Phase A content — 24 entries, same as test_phase_a_s089.py)
# ---------------------------------------------------------------------------

PHASE_A_CONTENT = {
    "facts": [
        ("PF-01: RITAM is a research programme investigating governed cognition substrates.", "claude-s089"),
        ("PF-02: v0.1 substrate implements three interfaces: AdmissionGateway, ContradictionStore, ObservationChannel.", "claude-s080"),
        ("PF-03: Kill Test runs: 9 governance events / 9 runs / 0 baseline events as of Session 089.", "claude-s089"),
        ("PF-04: GovernedNotebook consumer (Session 080) — substrate generalises beyond Governed Memory Object.", "claude-s080"),
        ("PF-05: GovernedAgentMemory consumer (Session 088) — programme memory with governance layer.", "claude-s088"),
        ("PF-06: Phase A complete: 24 real programme entries governed; 0 false positives (0 governance events on legitimate content).", "claude-s089"),
        ("PF-07: Mahdi external advisory review received Session 089. Priority: OQ-058 > Phase B > Gate B > Third consumer.", "mahdi-s089"),
        ("PF-08: ChatGPT second opinion Session 089: agrees with Mahdi priority order; 'without persistence, you demonstrate governance events; with persistence, governance value'.", "chatgpt-s089"),
        ("PF-09: v0.1 anti-framework rules (API_SPEC.md Appendix B): no LLM, no embeddings, no semantic similarity, no async.", "claude-s081"),
    ],
    "decisions": [
        ("ADR-014: Mission Alignment Gate — every session must answer how work moves toward executable governed-cognition substrate. Sessions tagged BUILD/ANCHORED-RESEARCH/GOVERNANCE/TANGENT.", "rishi-s082"),
        ("ADR-015: P4b as canonical governing hypothesis — 'Substrate-level governance primitives can produce emergent system properties that no individual primitive produces alone, within regime bounds.' (Amended: 'within regime bounds' added.)", "claude-s087"),
        ("ADR-001: Ritam ≠ Niyom. These are separate projects. Never conflate them.", "rishi-s001"),
        ("Phase 2 consumer decision (S087 addendum): Governed Agent Memory Layer anchored to RITAM programme memory — second materially distinct consumer for v0.1 substrate portability claim.", "rishi-s087"),
    ],
    "insights": [
        ("INSIGHT-114: Superadditivity is regime-bounded. Governance produces emergent properties only within specific interaction regimes, not universally. (Session 079.)", "claude-s079"),
        ("INSIGHT-115: Governance ≠ reliability. Governance is a mechanism for making reliability achievable — it is not reliability itself. Reliability requires governance + appropriate content + evaluation. (Session 084.)", "claude-s084"),
        ("INSIGHT-116: Substrate conflict detection requires matching both category and content hash. Bare-string hash match is insufficient when category enforcement is the invariant being tested. (Session 085.)", "claude-s085"),
        ("INSIGHT-117: P4b/CC2 scoping tension. P4b specifies 'substrate-level primitives'; CC2 claims 'necessary AND sufficient across all layers'. These are different scopes. Tension preserved visibly per ADR-015. (Session 087.)", "claude-s087"),
        ("INSIGHT-118 (CORRECTED Session 089): Two consumers sharing same substrate engine with memory-oriented vocabularies demonstrates governance portability across consumers, NOT substrate-generality. Substrate-generality requires materially different consumer domains. Siblings (both memory-oriented) ≠ strangers (memory + task-planner). (Session 088, corrected 089.)", "claude-s089"),
        ("INSIGHT-119: Contradiction detection requires plurality awareness. Without explicit PLURAL/SINGULAR category distinction, legitimate coexistence is misclassified as conflict (false positives). PLURAL/SINGULAR vocabulary is load-bearing substrate architecture, not optional metadata. Empirical evidence: 61 baseline false positives in Phase A, 0 governed false positives. (Session 089.)", "claude-s089"),
    ],
    "questions": [
        ("OQ-056: Is the current Contradiction Store sufficiently general for v0.2? Scope: category-level only; no intra-category semantic resolution. (Session 084.)", "claude-s084"),
        ("OQ-057: Can a singular empirical finding (one contradiction quarantined per Kill Test run) serve as the falsification unit for v0.1? Resolved: yes — a single unambiguous singular conflict per run is sufficient for v0.1 Kill Test. (Session 084, resolved.)", "claude-s085"),
        ("OQ-058: Should Kill Test use persistent cumulative store across sessions? Current: fresh DB per run; cross-session contradictions require explicit seeding. OPEN — Phase B addresses this. (Session 087.)", "claude-s087"),
    ],
    "governing_hypothesis": "P4b: Substrate-level governance primitives can produce emergent system properties that no individual primitive produces alone, within regime bounds.",
    "governing_hypothesis_source": "ADR-015",
}

# Contradictory candidate (used in Run 2)
CC2 = "CC2: Substrate governance is necessary AND sufficient for reliable AI behaviour across all layers."
CC2_SOURCE = "adversarial-phase-b"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def seed_content(memory, content: dict) -> int:
    """Load Phase A programme history into a memory instance. Returns entries loaded."""
    count = 0
    for content_str, source in content["facts"]:
        memory.add_fact(content_str, source); count += 1
    for content_str, source in content["decisions"]:
        memory.add_decision(content_str, source); count += 1
    for content_str, source in content["insights"]:
        memory.add_insight(content_str, source); count += 1
    for content_str, source in content["questions"]:
        memory.add_question(content_str, source); count += 1
    memory.set_governing_hypothesis(content["governing_hypothesis"], content["governing_hypothesis_source"])
    count += 1
    return count


def print_separator(label: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")


# ---------------------------------------------------------------------------
# Phase B — Governed Agent Memory
# ---------------------------------------------------------------------------

def run_governed_phase_b(snapshot_dir: Path) -> dict:
    """
    Two-run simulation for GovernedAgentMemory.
    Returns results dict with governance event counts and verdicts.
    """
    snapshot_run1 = str(snapshot_dir / "governed_snapshot_run1.json")
    snapshot_run2 = str(snapshot_dir / "governed_snapshot_run2.json")

    # -----------------------------------------------------------------------
    # RUN 1: Seed Phase
    # -----------------------------------------------------------------------
    print_separator("GovernedAgentMemory — Run 1 (Seed Phase)")

    with tempfile.TemporaryDirectory() as tmpdir:
        mem_run1 = GovernedAgentMemory(tmpdir)
        entries_seeded = seed_content(mem_run1, PHASE_A_CONTENT)
        gov_events_run1 = mem_run1.governance_event_count()

        # Export snapshot
        exported = mem_run1.export_snapshot(snapshot_run1)
        hyp = mem_run1.query("governing-hypothesis")

    print(f"  Entries seeded: {entries_seeded}")
    print(f"  Governance events during seeding: {gov_events_run1}")
    print(f"  Snapshot exported: {exported} entries → {snapshot_run1}")
    print(f"  Governing hypothesis in store: {len(hyp)} entry/entries")

    assert gov_events_run1 == 0, (
        f"UNEXPECTED: {gov_events_run1} governance events during seeding."
        " Phase A content should admit cleanly."
    )
    assert len(hyp) == 1, f"Expected 1 governing hypothesis, got {len(hyp)}"
    assert exported == entries_seeded, f"Export count mismatch: {exported} vs {entries_seeded}"

    # -----------------------------------------------------------------------
    # RUN 2: Contradiction Phase (new Python "process" = fresh instance)
    # -----------------------------------------------------------------------
    print_separator("GovernedAgentMemory — Run 2 (Contradiction Phase — new process)")

    with tempfile.TemporaryDirectory() as tmpdir2:
        mem_run2 = GovernedAgentMemory(tmpdir2)

        # Load from snapshot — simulates what a new process would do
        loaded, events_during_load = mem_run2.load_snapshot(snapshot_run1)
        print(f"  Loaded from snapshot: {loaded} entries, {events_during_load} governance events during load")

        hyp_loaded = mem_run2.query("governing-hypothesis")
        print(f"  Governing hypothesis in store after load: {len(hyp_loaded)} entry/entries")
        print(f"  Content: {hyp_loaded[0]['content'][:80]}..." if hyp_loaded else "  Content: NONE")

        # Now propose CC2 — this is the organic cross-process contradiction
        print(f"\n  Proposing CC2 (organic contradiction from this run):")
        print(f"  '{CC2[:80]}...'")
        result_cc2 = mem_run2.set_governing_hypothesis(CC2, CC2_SOURCE)
        print(f"  Result: status={result_cc2.status}, conflict_with={result_cc2.conflict_with}")
        print(f"  Message: {result_cc2.message}")

        gov_events_total_run2 = mem_run2.governance_event_count()
        gov_events_this_run = gov_events_total_run2 - 0  # fresh instance, so total = this run
        print(f"\n  Governance events in Run 2: {gov_events_this_run}")

        # Export updated snapshot
        exported_run2 = mem_run2.export_snapshot(snapshot_run2)

    print(f"  Run 2 snapshot exported: {exported_run2} entries → {snapshot_run2}")

    return {
        "run1_entries_seeded": entries_seeded,
        "run1_governance_events": gov_events_run1,
        "run1_snapshot_exported": exported,
        "run2_loaded_from_snapshot": loaded,
        "run2_events_during_load": events_during_load,
        "run2_cc2_status": result_cc2.status,
        "run2_cc2_conflict_with": result_cc2.conflict_with,
        "run2_governance_events": gov_events_this_run,
        "snapshot_run1": snapshot_run1,
        "snapshot_run2": snapshot_run2,
    }


# ---------------------------------------------------------------------------
# Phase B — Baseline Agent Memory
# ---------------------------------------------------------------------------

def run_baseline_phase_b(snapshot_dir: Path) -> dict:
    """
    Two-run simulation for BaselineAgentMemory.
    Returns results dict with governance event counts and conflict detection.
    """
    snapshot_run1 = str(snapshot_dir / "baseline_snapshot_run1.json")
    snapshot_run2 = str(snapshot_dir / "baseline_snapshot_run2.json")

    # -----------------------------------------------------------------------
    # RUN 1: Seed Phase
    # -----------------------------------------------------------------------
    print_separator("BaselineAgentMemory — Run 1 (Seed Phase)")

    with tempfile.TemporaryDirectory() as tmpdir:
        base_run1 = BaselineAgentMemory(tmpdir)
        entries_seeded = seed_content(base_run1, PHASE_A_CONTENT)
        exported = base_run1.export_snapshot(snapshot_run1)

    print(f"  Entries seeded: {entries_seeded}")
    print(f"  Snapshot exported: {exported} entries → {snapshot_run1}")

    # -----------------------------------------------------------------------
    # RUN 2: Contradiction Phase
    # -----------------------------------------------------------------------
    print_separator("BaselineAgentMemory — Run 2 (Contradiction Phase)")

    with tempfile.TemporaryDirectory() as tmpdir2:
        base_run2 = BaselineAgentMemory(tmpdir2)

        loaded, events_during_load = base_run2.load_snapshot(snapshot_run1)
        print(f"  Loaded from snapshot: {loaded} entries, {events_during_load} governance events during load")

        print(f"\n  Proposing CC2:")
        result_cc2 = base_run2.set_governing_hypothesis(CC2, CC2_SOURCE)
        print(f"  Result: status={result_cc2['status']}")

        gov_events_run2 = base_run2.governance_event_count()
        conflicts = base_run2.list_conflicts()
        cross_process_conflicts = [
            c for c in conflicts
            if any("CC2" in str(item.get("content", "")) for item in c["items"])
        ]

        print(f"  Governance events (baseline always 0): {gov_events_run2}")
        print(f"  Heuristic conflicts detected (post-hoc): {len(conflicts)}")
        print(f"  Heuristic conflicts involving CC2 vs P4b: {len(cross_process_conflicts)}")

        exported_run2 = base_run2.export_snapshot(snapshot_run2)

    return {
        "run1_entries_seeded": entries_seeded,
        "run1_snapshot_exported": exported,
        "run2_loaded_from_snapshot": loaded,
        "run2_events_during_load": events_during_load,
        "run2_cc2_status": result_cc2["status"],
        "run2_governance_events": gov_events_run2,
        "run2_heuristic_conflicts": len(conflicts),
        "run2_cross_process_conflict_detected": len(cross_process_conflicts),
        "snapshot_run1": snapshot_run1,
        "snapshot_run2": snapshot_run2,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> dict:
    print("\n" + "="*70)
    print("  PHASE B — OQ-058: Persistent governance across Python process boundaries")
    print("  Session 090")
    print("="*70)

    snapshot_dir = Path(__file__).parent.parent / "data"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Run both
    governed = run_governed_phase_b(snapshot_dir)
    baseline = run_baseline_phase_b(snapshot_dir)

    # -----------------------------------------------------------------------
    # Kill condition
    # -----------------------------------------------------------------------
    print_separator("Kill Condition Assessment")

    kill_condition_met = (
        governed["run2_cc2_status"] != "conflict"
        or governed["run2_governance_events"] == 0
    )

    print(f"  GovernedAgentMemory Run 2 — CC2 status : {governed['run2_cc2_status']}")
    print(f"  GovernedAgentMemory Run 2 — Gov events : {governed['run2_governance_events']}")
    print(f"  BaselineAgentMemory Run 2 — CC2 status : {baseline['run2_cc2_status']}")
    print(f"  BaselineAgentMemory Run 2 — Gov events : {baseline['run2_governance_events']} (always 0)")
    print(f"  Baseline cross-process heuristic detect: {baseline['run2_cross_process_conflict_detected']}")
    print()
    print(f"  Kill condition met : {kill_condition_met}")

    if kill_condition_met:
        print("  ⚠  KILL CONDITION MET — substrate FAILED to surface cross-process contradiction.")
    else:
        print("  ✓  Kill condition NOT met — governance surfaced cross-process contradiction.")
        print("  ✓  OQ-058 v0.1 scope: governance functions across process boundaries when snapshot")
        print("     persistence is provided. Evidence tier upgraded: fixture → accumulating state.")

    # -----------------------------------------------------------------------
    # Fixture
    # -----------------------------------------------------------------------
    fixture = {
        "test": "phase_b_s090",
        "session": "090",
        "description": (
            "Phase B: OQ-058 — persistent governance across Python process boundaries. "
            "Two-run simulation via JSON snapshot export/import. "
            "Run 1 seeds programme history (P4b as governing hypothesis). "
            "Run 2 loads from snapshot, proposes CC2 — governance fires against loaded P4b."
        ),
        "governed": {
            "run1_entries_seeded": governed["run1_entries_seeded"],
            "run1_governance_events": governed["run1_governance_events"],
            "run1_snapshot_exported": governed["run1_snapshot_exported"],
            "run2_loaded_from_snapshot": governed["run2_loaded_from_snapshot"],
            "run2_events_during_load": governed["run2_events_during_load"],
            "run2_cc2_status": governed["run2_cc2_status"],
            "run2_governance_events": governed["run2_governance_events"],
        },
        "baseline": {
            "run1_entries_seeded": baseline["run1_entries_seeded"],
            "run1_snapshot_exported": baseline["run1_snapshot_exported"],
            "run2_loaded_from_snapshot": baseline["run2_loaded_from_snapshot"],
            "run2_cc2_status": baseline["run2_cc2_status"],
            "run2_governance_events": baseline["run2_governance_events"],
            "run2_heuristic_conflicts": baseline["run2_heuristic_conflicts"],
            "run2_cross_process_conflict_detected": baseline["run2_cross_process_conflict_detected"],
        },
        "kill_condition_met": kill_condition_met,
        "oq_058_finding": (
            "RESOLVED (v0.1 scope): Governance surfaces contradictions across Python process "
            "boundaries when snapshot persistence is provided. Evidence tier: "
            "\'fixture\' → \'accumulating state\'. Remaining open: "
            "production-grade persistence (RDBMS / append-only log) deferred to v0.3."
        ) if not kill_condition_met else "FAIL — kill condition met.",
    }

    fixture_path = Path(__file__).parent / "fixtures" / "phase_b_s090.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(json.dumps(fixture, indent=2))
    print(f"\n  Fixture written: {fixture_path}")

    return fixture


if __name__ == "__main__":
    result = main()
    sys.exit(0 if not result["kill_condition_met"] else 1)
