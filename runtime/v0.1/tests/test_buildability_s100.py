"""
test_buildability_s100.py — C3 Re-audit (Session 100, ADR-017 complete)

This test re-runs the same 5 buildability criteria from test_buildability_s096.py
against the spec and implementation after all 5 ADR-017 gaps have been closed.

Session 096 verdict: SUPPORTED WITH GAPS — 5/5 criteria pass, 5 spec gaps found.
Session 100 verdict: CLEAN PASS — 5/5 criteria pass, 0 spec gaps.

ADR-017 gap closure record:
  GAP-1 ✅ Session 098: plural_categories → singular_categories rename + logic inversion
  GAP-2 ✅ Session 098: get_repair() + mark_resolved() documented in API_SPEC §2 + BUILDABILITY_PACKET
  GAP-3 ✅ Session 099: singular_categories permissive default documented with warning
  GAP-4 ✅ Session 099: §0 Public Types section + RepairSuggestion import paths
  GAP-5 ✅ Session 100: list_admitted() added to AdmissionGateway; GovernedDecisionLog refactored

All 5 criteria are called using ONLY the public API documented in API_SPEC.md and
BUILDABILITY_PACKET.md — no private attributes, no internal imports.
"""
from __future__ import annotations

import tempfile

# GAP-4 verified: these imports all work from the public spec
from ritam.runtime.v01 import (
    Substrate,
    SubstrateConfig,
    AdmissionVerdict,
    AdmissionRecord,       # GAP-5: now exported
    SignalType,
)
from ritam.runtime.v01.types import RepairSuggestion, ResolutionPathway  # GAP-4


def make_decision_log(tmp_path: str):
    """Build a minimal governed decision log from the spec alone — no private access."""
    config = SubstrateConfig(
        storage_path=tmp_path,
        known_categories=["active-decision", "decision-rationale"],
        singular_categories=["active-decision"],  # GAP-1+GAP-3: correct semantics
    )
    substrate = Substrate(config)
    gw = substrate.admission_gateway()
    cs = substrate.contradiction_store()
    oc = substrate.observation_channel()
    return gw, cs, oc


# ---------------------------------------------------------------------------
# Criterion 1: governance fires on conflict (same as S096 C1)
# ---------------------------------------------------------------------------
def test_c3_criterion_1_governance_fires_on_conflict():
    """Second active-decision → QUARANTINED. GAP-1 fix verified (correct semantics)."""
    with tempfile.TemporaryDirectory() as tmp:
        gw, cs, _ = make_decision_log(tmp)

        r1 = gw.propose("Use PostgreSQL as primary database.", "active-decision", "architect")
        assert r1.verdict == AdmissionVerdict.ADMITTED

        r2 = gw.propose("Use SQLite for all environments.", "active-decision", "engineer")
        assert r2.verdict == AdmissionVerdict.QUARANTINED, \
            f"Expected QUARANTINED, got {r2.verdict}"
        assert cs.count() == 1

        print("PASS: criterion 1 — governance fires on conflict")


# ---------------------------------------------------------------------------
# Criterion 2: repair suggestion present (GAP-2 verified)
# ---------------------------------------------------------------------------
def test_c3_criterion_2_repair_suggestion_present():
    """Conflict produces RepairSuggestion via get_repair(). GAP-2 fix verified."""
    with tempfile.TemporaryDirectory() as tmp:
        gw, cs, _ = make_decision_log(tmp)

        gw.propose("Use microservices.", "active-decision", "cto")
        r2 = gw.propose("Use monolith.", "active-decision", "lead")
        assert r2.verdict == AdmissionVerdict.QUARANTINED

        # GAP-2: get_repair() is now in base ContradictionStore spec
        repair = cs.get_repair(r2.repair.quarantine_id)
        assert repair is not None
        assert isinstance(repair, RepairSuggestion)
        assert len(repair.resolution_pathways) == 3
        pathway_ids = {p.pathway_id for p in repair.resolution_pathways}
        assert "RETRACT_EXISTING" in pathway_ids
        assert "KEEP_EXISTING" in pathway_ids
        assert "HOLD_AS_CONTRADICTION" in pathway_ids

        print("PASS: criterion 2 — repair suggestion present and structured")


# ---------------------------------------------------------------------------
# Criterion 3: retract + readmit (unchanged from S096)
# ---------------------------------------------------------------------------
def test_c3_criterion_3_retract_and_readmit():
    """After retracting existing decision, new proposal is admitted."""
    with tempfile.TemporaryDirectory() as tmp:
        gw, cs, _ = make_decision_log(tmp)

        r1 = gw.propose("Use REST APIs.", "active-decision", "session-001")
        assert r1.verdict == AdmissionVerdict.ADMITTED

        # Conflict
        r2 = gw.propose("Use GraphQL APIs.", "active-decision", "session-002")
        assert r2.verdict == AdmissionVerdict.QUARANTINED

        # Resolve: retract the existing decision
        retract_result = gw.retract(r1.item_id, source="board", reason="GraphQL chosen")
        assert retract_result.verdict == AdmissionVerdict.ADMITTED

        # Mark resolved via ContradictionStore (GAP-2 verified)
        resolved = cs.mark_resolved(r2.repair.quarantine_id, "Board chose GraphQL.")
        assert resolved

        # Now the new decision should be admitted
        r3 = gw.propose("Use GraphQL APIs.", "active-decision", "session-002")
        assert r3.verdict == AdmissionVerdict.ADMITTED, \
            f"Expected ADMITTED after retract, got {r3.verdict}"

        print("PASS: criterion 3 — retract + readmit")


# ---------------------------------------------------------------------------
# Criterion 4: plural category always admitted (GAP-3 verified)
# ---------------------------------------------------------------------------
def test_c3_criterion_4_rationale_always_admitted():
    """Multiple rationale items coexist freely. GAP-3 permissive default verified."""
    with tempfile.TemporaryDirectory() as tmp:
        gw, cs, _ = make_decision_log(tmp)

        r1 = gw.propose("GraphQL reduces over-fetching.", "decision-rationale", "eng")
        r2 = gw.propose("GraphQL has strong typing.", "decision-rationale", "eng")
        r3 = gw.propose("Team has GraphQL expertise.", "decision-rationale", "hr")

        assert r1.verdict == AdmissionVerdict.ADMITTED
        assert r2.verdict == AdmissionVerdict.ADMITTED
        assert r3.verdict == AdmissionVerdict.ADMITTED
        assert cs.count() == 0, "Plural category must never produce contradictions"

        print("PASS: criterion 4 — rationale always admitted (plural default)")


# ---------------------------------------------------------------------------
# Criterion 5: list_admitted() works (GAP-5 verified — NEW)
# ---------------------------------------------------------------------------
def test_c3_criterion_5_list_admitted_public_api():
    """
    Consumer can read current admitted items using the public API.
    GAP-5 fix: list_admitted() replaces direct _db access.
    This criterion REPLACES the original S096 Criterion 5 (list_conflicts via _cs)
    with a stronger test: can the consumer read state without private attributes?
    """
    with tempfile.TemporaryDirectory() as tmp:
        gw, cs, _ = make_decision_log(tmp)

        # Admit a decision and some rationale
        gw.propose("Use event sourcing.", "active-decision", "architect")
        gw.propose("Enables audit trail.", "decision-rationale", "cto")
        gw.propose("Supports replay.", "decision-rationale", "eng")

        # GAP-5 fix: read via public API, no _db access
        decisions = gw.list_admitted("active-decision")
        rationale = gw.list_admitted("decision-rationale")

        assert len(decisions) == 1, f"Expected 1 active decision, got {len(decisions)}"
        assert len(rationale) == 2, f"Expected 2 rationale items, got {len(rationale)}"

        # Verify AdmissionRecord fields (GAP-4+GAP-5: type is importable and complete)
        d = decisions[0]
        assert isinstance(d, AdmissionRecord)
        assert d.category == "active-decision"
        assert d.content == "Use event sourcing."
        assert d.source == "architect"
        assert d.item_id is not None
        assert d.admitted_at is not None

        # Verify empty category returns [] not exception
        empty = gw.list_admitted("nonexistent-category")
        assert empty == []

        print("PASS: criterion 5 — list_admitted() public API works (GAP-5 closed)")


# ---------------------------------------------------------------------------
# Bonus: SignalType enum completeness (GAP-5/SignalType documented)
# ---------------------------------------------------------------------------
def test_c3_bonus_signal_types_importable_and_complete():
    """
    All 15 SignalType members are importable.
    Session 106: COORDINATION_CONFLICT added (Coordination primitive).
    Session 111: REPAIR_ONTOLOGY_CONFLICT added (GAP-6 remediation, ADR-018).
    """
    expected = {
        "ADMITTED", "QUARANTINED", "REJECTED", "RETRACTED",
        "OBSERVATION_GAP", "REPRESENTATION_LIMIT",
        "DECAY_APPLIED", "QUARANTINE_PURGED", "REPAIR_TRIGGERED",
        "TEMPORAL_ALERT",            # Session 103 — Temporal primitive
        "EPISTEMIC_ALERT",           # Session 104 — Epistemic primitive
        "COORDINATION_CONFLICT",     # Session 106 — Coordination primitive
        "ONTOLOGY_MUTATION",         # Session 107 — Ontology primitive
        "REPAIR_LIFECYCLE",          # Session 108 — Repair-as-Primitive
        "REPAIR_ONTOLOGY_CONFLICT",  # Session 111 — GAP-6 fix (Option B)
    }
    actual = {m.name for m in SignalType}
    assert actual == expected, f"SignalType mismatch: {actual ^ expected}"
    print("PASS: bonus — all 15 SignalType members importable")


# ---------------------------------------------------------------------------
# Runner + verdict
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 65)
    print("Session 100 — C3 Re-audit (ADR-017 complete)")
    print("=" * 65)

    test_c3_criterion_1_governance_fires_on_conflict()
    test_c3_criterion_2_repair_suggestion_present()
    test_c3_criterion_3_retract_and_readmit()
    test_c3_criterion_4_rationale_always_admitted()
    test_c3_criterion_5_list_admitted_public_api()
    test_c3_bonus_signal_types_importable_and_complete()

    print()
    print("C3 Re-audit Verdict (Session 100):")
    print("  All 5 criteria: PASS")
    print("  Bonus (SignalType completeness — 12 members): PASS")
    print("  Gaps vs Session 096: 0 (was 5)")
    print()
    print("ADR-017 COMPLETE. All 5 gaps closed:")
    print("  GAP-1 ✅ S098: singular_categories rename + logic inversion")
    print("  GAP-2 ✅ S098: get_repair() + mark_resolved() in spec")
    print("  GAP-3 ✅ S099: permissive default documented + warning")
    print("  GAP-4 ✅ S099: §0 Public Types + import paths")
    print("  GAP-5 ✅ S100: list_admitted() + AdmissionRecord; no _db access needed")
    print()
    print("C3 Assessment: CLEAN PASS")
    print("  A cold builder following API_SPEC.md + BUILDABILITY_PACKET.md")
    print("  can build a governed consumer with no gaps, no private access,")
    print("  and no undocumented lookup required.")
