"""
Kill Test 8 — Governed Agent Memory Layer consumer.
Session 088.

This is the first Kill Test using the second substrate consumer:
GovernedAgentMemory. The research notebook consumer (GovernedNotebook)
has been tested across runs 1-7. Kill Test 8 tests whether the same
substrate governs a different consumer domain correctly.

Consumer: RITAM programme memory — facts, decisions, insights, and the
governing hypothesis the programme is currently operating under.

Propositions (real RITAM programme memory, not invented):
  F1-F5: Programme facts (PLURAL — multiple should be admitted)
  D1-D2: Programme decisions (PLURAL)
  I1-I3: Programme insights (PLURAL)
  OQ1:   Open question (PLURAL)
  P4b:   Governing hypothesis — narrowed (SINGULAR — first admission)
  CC2:   Contradictory governing hypothesis (SINGULAR — should QUARANTINE)

Kill condition (unchanged from prior runs, now applied to new consumer):
  The substrate fails if governance events are indistinguishable from the
  baseline AND the governed consumer provides no additional signal.

  Current state (runs 1-8 governed, runs 1-7 baseline): baseline 0/7.
  Kill Test 8 must produce ≥1 governance event in the governed consumer
  and 0 in the baseline for the kill condition to remain unmet.

What this test proves beyond Kill Tests 1-7:
  Substrate-generality: the same substrate engine, with a different consumer
  vocabulary (programme-memory categories vs research-notebook categories),
  produces the same governance guarantee. The governance lives in the substrate,
  not in the notebook consumer wrapper.
"""
import os
import sys
import json
import tempfile
from pathlib import Path

# Add the v0.1 runtime to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_memory.governed_agent_memory import GovernedAgentMemory
from agent_memory.baseline_agent_memory import BaselineAgentMemory


# ---------------------------------------------------------------------------
# Propositions — real RITAM programme memory
# ---------------------------------------------------------------------------

FACTS = [
    ("F1", "Kill Test series: 8 runs completed, 8 governance events, baseline 0/7."),
    ("F2", "Current substrate version: v0.1. Implementation complete: AdmissionGateway, ContradictionStore, ObservationChannel."),
    ("F3", "v0.2 changes: empirical-finding PLURAL (OQ-057 fix); canonical-claim SINGULAR; content validation at admission boundary (OQ-056 fix)."),
    ("F4", "OQ-058 open: Kill Test uses fresh DB per run; cross-session conflicts require explicit seeding. Deferred to v0.3/Phase 2."),
    ("F5", "Prototype sequence: 1=GovernedMemoryObject, 2=StateTransitionSimulator, 3=ContradictionPersistenceEngine, 4=MemoryDecaySimulator, 5=OntologyMutationSandbox. All complete."),
]

DECISIONS = [
    ("D1", "ADR-015: P4b reclassified as governing hypothesis (not law, not empirical finding). Reflects OQ-054 private literature scan finding that the core is a governance-framed re-expression of Quickest Change Detection theory."),
    ("D2", "ADR-015 amendment (S087): P4b narrowed to substrate layer only. Reasoning: CC2 quarantine (Kill Test 7) showed the original P4b over-claimed. Substrate governance does not extend to the AI reasoning layer above."),
]

INSIGHTS = [
    ("I1", "INSIGHT-115: Governance does not equal reliability. RITAM targets governed behaviour (bounded/observable/repairable), not reliable behaviour (predictable output). These are different properties at different layers."),
    ("I2", "INSIGHT-116: canonical-claim category makes the programme's own governing assertion a first-class governed object. The substrate can govern itself."),
    ("I3", "INSIGHT-117 (resolved S087): P4b/CC2 scoping tension is a scoping artifact, not a genuine contradiction. P4b governs the substrate layer; CC2 addresses the AI reasoning layer above. Both findings are valid at their respective layers."),
]

OPEN_QUESTIONS = [
    ("OQ1", "OQ-058: Should Kill Test use a persistent cumulative store across runs? Would surface cross-session conflicts organically. Deferred to v0.3/Phase 2."),
]

# GOVERNING HYPOTHESIS: narrowed P4b (ADR-015 amendment, confirmed S087)
P4B_NARROWED = (
    "P4b (governing hypothesis, narrowed S087): A governance-first substrate makes the knowledge "
    "management layer bounded, observable, and repairable — governance events surface, contradictions "
    "are preserved rather than hidden, and repair is enabled. This guarantee applies to the substrate's "
    "own operations; it does not require, and does not extend to, reliable behaviour from the AI "
    "reasoning layer above the substrate."
)

# CONTRADICTORY GOVERNING HYPOTHESIS: what CC2 + the un-narrowed P4b together would imply
# This is NOT a straw man — it is the position that would follow if someone rejected the narrowing
CC2_AS_GOVERNING_HYPOTHESIS = (
    "Counter-hypothesis (CC2 framing): Substrate governance is necessary AND sufficient for "
    "reliable AI behaviour across all layers. A governance-first substrate that is bounded, "
    "observable, and repairable guarantees reliable AI outputs, not just reliable substrate "
    "operations. The verification problem is solvable at the substrate level alone."
)


# ---------------------------------------------------------------------------
# Kill Test runner
# ---------------------------------------------------------------------------

def run_kill_test_8(gov_dir: str, base_dir: str) -> dict:
    gov = GovernedAgentMemory(gov_dir)
    base = BaselineAgentMemory(base_dir)

    results = {
        "governed": [],
        "baseline": [],
        "gov_event_count": 0,
        "base_event_count": 0,
    }

    # --- Facts (PLURAL) ---
    for name, text in FACTS:
        r_gov = gov.add_fact(text, source=f"programme/{name}")
        r_base = base.add_fact(text, source=f"programme/{name}")
        results["governed"].append({"prop": name, "status": r_gov.status, "entry_id": r_gov.entry_id})
        results["baseline"].append({"prop": name, "status": r_base["status"]})

    # --- Decisions (PLURAL) ---
    for name, text in DECISIONS:
        r_gov = gov.add_decision(text, source=f"programme/{name}")
        r_base = base.add_decision(text, source=f"programme/{name}")
        results["governed"].append({"prop": name, "status": r_gov.status, "entry_id": r_gov.entry_id})
        results["baseline"].append({"prop": name, "status": r_base["status"]})

    # --- Insights (PLURAL) ---
    for name, text in INSIGHTS:
        r_gov = gov.add_insight(text, source=f"programme/{name}")
        r_base = base.add_insight(text, source=f"programme/{name}")
        results["governed"].append({"prop": name, "status": r_gov.status, "entry_id": r_gov.entry_id})
        results["baseline"].append({"prop": name, "status": r_base["status"]})

    # --- Open questions (PLURAL) ---
    for name, text in OPEN_QUESTIONS:
        r_gov = gov.add_question(text, source=f"programme/{name}")
        r_base = base.add_question(text, source=f"programme/{name}")
        results["governed"].append({"prop": name, "status": r_gov.status, "entry_id": r_gov.entry_id})
        results["baseline"].append({"prop": name, "status": r_base["status"]})

    # --- Governing hypothesis (SINGULAR) ---
    r_gov_p4b = gov.set_governing_hypothesis(P4B_NARROWED, source="ADR-015-amendment")
    r_base_p4b = base.set_governing_hypothesis(P4B_NARROWED, source="ADR-015-amendment")
    results["governed"].append({"prop": "P4b", "status": r_gov_p4b.status, "entry_id": r_gov_p4b.entry_id})
    results["baseline"].append({"prop": "P4b", "status": r_base_p4b["status"]})

    # --- Contradictory governing hypothesis (SINGULAR — should QUARANTINE in governed) ---
    r_gov_cc2 = gov.set_governing_hypothesis(CC2_AS_GOVERNING_HYPOTHESIS, source="counter-hypothesis")
    r_base_cc2 = base.set_governing_hypothesis(CC2_AS_GOVERNING_HYPOTHESIS, source="counter-hypothesis")
    results["governed"].append({
        "prop": "CC2-as-governing-hypothesis",
        "status": r_gov_cc2.status,
        "entry_id": r_gov_cc2.entry_id,
        "conflict_with": r_gov_cc2.conflict_with,
        "message": r_gov_cc2.message,
    })
    results["baseline"].append({"prop": "CC2-as-governing-hypothesis", "status": r_base_cc2["status"]})

    results["gov_event_count"] = gov.governance_event_count()
    results["base_event_count"] = base.governance_event_count()
    results["gov_conflicts"] = gov.list_conflicts()
    results["base_conflicts"] = base.list_conflicts()

    return results


def print_report(results: dict) -> None:
    print()
    print("=" * 70)
    print("KILL TEST 8 — Governed Agent Memory Layer")
    print("Session 088 · Consumer: RITAM programme memory")
    print("=" * 70)

    print()
    print("PROPOSITION-BY-PROPOSITION RESULTS")
    print("-" * 50)
    gov_rows = results["governed"]
    base_rows = results["baseline"]
    for g, b in zip(gov_rows, base_rows):
        flag = "⚡ GOVERNANCE EVENT" if g["status"] == "conflict" else ""
        print(f"  {g['prop']:30s} | governed={g['status']:8s} | baseline={b['status']:8s}  {flag}")

    print()
    print("GOVERNANCE EVENT COUNTS")
    print(f"  Governed consumer : {results['gov_event_count']} governance event(s)")
    print(f"  Baseline consumer : {results['base_event_count']} governance event(s)")

    print()
    print("GOVERNED CONTRADICTION STORE")
    for c in results["gov_conflicts"]:
        print(f"  quarantine_id : {c['quarantine_id']}")
        print(f"  category      : {c['category']}")
        print(f"  items         :")
        for item in c["items"]:
            snippet = str(item["content"])[:80]
            print(f"    [{item['item_id'][:8]}] {snippet}...")
        print(f"  quarantined_at: {c['quarantined_at']}")
        print(f"  reason        : {c['reason']}")
        print()

    print("BASELINE 'CONFLICT' DETECTION (heuristic, post-hoc)")
    if results["base_conflicts"]:
        for c in results["base_conflicts"]:
            print(f"  category: {c['category']} | both entries ALREADY STORED before this check ran")
    else:
        print("  (none detected by heuristic — contradictory hypothesis stored silently)")

    print()
    print("KILL CONDITION ASSESSMENT")
    print("-" * 50)
    gov_events = results["gov_event_count"]
    base_events = results["base_event_count"]

    # Kill Test 7 cumulative: 8 gov runs / 8 gov events; baseline 0/7
    # After Kill Test 8:
    total_gov_runs = 9
    total_gov_events = 8 + gov_events  # prior 8 + this run
    total_base_events = 0 + base_events  # baseline still 0

    print(f"  Kill Test 8 gov events  : {gov_events}")
    print(f"  Kill Test 8 base events : {base_events}")
    print(f"  Cumulative (9 runs)     : {total_gov_events} gov events / {total_base_events} baseline")

    if gov_events > 0 and base_events == 0:
        print()
        print("  ✓ KILL CONDITION NOT MET")
        print("    Governed consumer produced governance events; baseline produced none.")
        print("    Substrate-generality validated: same engine, new consumer vocabulary,")
        print("    same governance guarantee.")
    elif gov_events == 0:
        print()
        print("  ✗ KILL CONDITION ASSESSMENT: governed produced 0 events this run.")
        print("    Investigate: did CC2 get quarantined?")
    else:
        print()
        print("  ✗ UNEXPECTED: baseline produced governance events. Check implementation.")

    print()
    print("=" * 70)


def save_fixture(results: dict, path: str) -> None:
    """Save results as a JSON fixture for the programme record."""
    fixture = {
        "kill_test_run": 8,
        "session": "088",
        "consumer": "GovernedAgentMemory",
        "consumer_domain": "RITAM programme memory",
        "category_vocabulary": {
            "programme-fact": "PLURAL",
            "governing-hypothesis": "SINGULAR",
            "open-question": "PLURAL",
            "decision": "PLURAL",
            "insight": "PLURAL",
        },
        "propositions": [r["prop"] for r in results["governed"]],
        "gov_event_count": results["gov_event_count"],
        "base_event_count": results["base_event_count"],
        "governed_results": results["governed"],
        "baseline_results": results["baseline"],
        "gov_conflicts_count": len(results["gov_conflicts"]),
        "base_conflicts_count": len(results["base_conflicts"]),
        "cumulative_gov_events": 8 + results["gov_event_count"],
        "cumulative_runs": 9,
        "kill_condition_met": not (results["gov_event_count"] > 0 and results["base_event_count"] == 0),
        "notes": (
            "First Kill Test using second substrate consumer (GovernedAgentMemory). "
            "CC2-as-governing-hypothesis is the counter-hypothesis to narrowed P4b "
            "(ADR-015 amendment). QUARANTINE in governed consumer demonstrates "
            "substrate-generality: same engine, new consumer vocabulary, same governance guarantee. "
            "Baseline stores contradictory governing hypotheses silently — no signal raised."
        ),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fixture, f, indent=2, default=str)
    print(f"Fixture saved: {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    fixture_dir = Path(__file__).parent / "fixtures"
    fixture_dir.mkdir(exist_ok=True)
    fixture_path = str(fixture_dir / "kill_test_s088.json")

    with tempfile.TemporaryDirectory() as tmpdir:
        gov_dir = os.path.join(tmpdir, "kill8_gov")
        base_dir = os.path.join(tmpdir, "kill8_base")
        results = run_kill_test_8(gov_dir, base_dir)

    print_report(results)
    save_fixture(results, fixture_path)
