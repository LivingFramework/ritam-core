"""
governed_decision_log.py — Governed Decision Log consumer (Session 096, ADR-016 C3)

Built from BUILDABILITY_PACKET.md alone (cold build — no prior RITAM context).
Records C3 gaps encountered during construction.

--- C3 BUILD LOG (preserved as found — append-only research record) ---

GAP-1: SubstrateConfig field name mismatch. [FIXED — Session 098]
  Packet says: singular_categories=["active-decision"]
  Implementation had: plural_categories (inverse logic — lists PLURAL, not SINGULAR)
  Severity: BREAKING — packet alone produced wrong enforcement mode
  Fix: Implementation renamed to singular_categories; logic aligned with spec.
  This file updated to use singular_categories=_SINGULAR_CATEGORIES.

GAP-2: RepairSuggestion not in base API_SPEC. [FIXED — Session 098, spec-only]
  get_repair() and mark_resolved() now documented in BUILDABILITY_PACKET §4 and API_SPEC §2.

GAP-3: plural_categories default behaviour not documented. [FIXED — Session 098]
  Now resolved by the GAP-1 rename: singular_categories=None → all categories plural (permissive).
  This is consistent, documented, and matches spec intent.

GAP-4: RepairSuggestion import path undocumented. [OPEN — Session 099]
  See ADR-017 for remediation.

GAP-5: No public read-by-category API on AdmissionGateway. [OPEN — Session 100]
  current_decision() and list_rationale() still access substrate._db directly.
  See ADR-017 for remediation (list_admitted() to be added to AdmissionGateway).

--- END BUILD LOG ---
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ritam.runtime.v01 import (
    AdmissionVerdict,
    Substrate,
    SubstrateConfig,
)

_KNOWN_CATEGORIES = [
    "active-decision",     # SINGULAR: at-most-one authoritative decision
    "decision-rationale",  # PLURAL: supporting reasons accumulate
    "decision-question",   # PLURAL: open questions accumulate
    "superseded-decision", # PLURAL: past decisions preserved after retraction
]
_SINGULAR_CATEGORIES = ["active-decision"]
# active-decision is the only SINGULAR category — at-most-one enforced.
# All others are plural by default (not listed in singular_categories).


@dataclass
class DecisionResult:
    status: str          # "admitted" | "conflict" | "gap" | "error"
    item_id: str | None
    conflict_with: list[str]
    message: str
    repair: Any          # RepairSuggestion | None (GAP-4: not typed to avoid import)


class GovernedDecisionLog:
    """
    A decision log where the active decision passes through substrate governance.

    One topic per instance (GAP: multi-topic requires separate instances or
    composite category keys — not expressible in the current substrate API).

    Built from BUILDABILITY_PACKET.md + types.py (GAP-1, GAP-5).
    """

    def __init__(self, storage_path: str) -> None:
        config = SubstrateConfig(
            storage_path=storage_path,
            known_categories=_KNOWN_CATEGORIES,
            singular_categories=_SINGULAR_CATEGORIES,
            decay_enabled=False,
            decay_interval_seconds=3600,
        )
        self._substrate = Substrate(config)
        self._gw = self._substrate.admission_gateway()
        self._cs = self._substrate.contradiction_store()
        self._oc = self._substrate.observation_channel()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def set_decision(self, content: str, source: str) -> DecisionResult:
        """Set the active decision. SINGULAR — at-most-one."""
        result = self._gw.propose(content, "active-decision", source)

        if result.verdict == AdmissionVerdict.ADMITTED:
            return DecisionResult(
                status="admitted",
                item_id=result.item_id,
                conflict_with=[],
                message="Decision admitted.",
                repair=None,
            )

        if result.verdict == AdmissionVerdict.QUARANTINED:
            # GAP-2/4: get_repair not in base spec; using extension
            repair = None
            if result.item_id:
                contradictions = self._cs.list_by_category("active-decision")
                for c in contradictions:
                    if result.item_id in c.item_ids:
                        repair = self._cs.get_repair(c.quarantine_id)
                        break
            return DecisionResult(
                status="conflict",
                item_id=result.item_id,
                conflict_with=result.conflict_ids,
                message=f"Decision conflicts with existing: {result.reason}",
                repair=repair,
            )

        return DecisionResult(
            status="gap" if "unknown" in result.reason.lower() or "observation gap" in result.reason.lower() else "error",
            item_id=None,
            conflict_with=[],
            message=result.reason,
            repair=None,
        )

    def add_rationale(self, content: str, source: str) -> DecisionResult:
        """Add supporting rationale. PLURAL — always admitted."""
        result = self._gw.propose(content, "decision-rationale", source)
        return DecisionResult(
            status="admitted" if result.verdict == AdmissionVerdict.ADMITTED else "error",
            item_id=result.item_id,
            conflict_with=[],
            message=result.reason,
            repair=None,
        )

    def add_question(self, content: str, source: str) -> DecisionResult:
        """Add an open question. PLURAL — always admitted."""
        result = self._gw.propose(content, "decision-question", source)
        return DecisionResult(
            status="admitted" if result.verdict == AdmissionVerdict.ADMITTED else "error",
            item_id=result.item_id,
            conflict_with=[],
            message=result.reason,
            repair=None,
        )

    def retract_decision(self, item_id: str, source: str, reason: str) -> DecisionResult:
        """Retract the existing active decision."""
        result = self._gw.retract(item_id, source, reason)
        return DecisionResult(
            status="admitted" if result.verdict == AdmissionVerdict.ADMITTED else "error",
            item_id=result.item_id,
            conflict_with=[],
            message=result.reason,
            repair=None,
        )

    # ------------------------------------------------------------------
    # Read operations (GAP-5 FIXED Session 100: use AdmissionGateway.list_admitted())
    # ------------------------------------------------------------------

    def current_decision(self) -> dict | None:
        """Return the currently admitted active decision, or None."""
        # GAP-5 fix: use public list_admitted() API (no more _db access)
        records = self._gw.list_admitted("active-decision")
        if not records:
            return None
        # Most recent by admitted_at (list_admitted returns ascending; take last)
        rec = records[-1]
        return {
            "item_id": rec.item_id,
            "content": rec.content,
            "source": rec.source,
            "admitted_at": rec.admitted_at,
        }

    def list_rationale(self) -> list[dict]:
        """Return all admitted rationale items."""
        # GAP-5 fix: use public list_admitted() API (no more _db access)
        records = self._gw.list_admitted("decision-rationale")
        return [{"item_id": r.item_id, "content": r.content, "source": r.source} for r in records]

    def list_conflicts(self) -> list[dict]:
        """Return all quarantined conflicts with repair information."""
        records = self._cs.list_by_category("active-decision")
        result = []
        for r in records:
            repair = self._cs.get_repair(r.quarantine_id)  # GAP-2: extension method
            result.append({
                "quarantine_id": r.quarantine_id,
                "conflicting_items": list(zip(r.item_ids, r.contents, r.sources)),
                "quarantined_at": r.quarantined_at.isoformat(),
                "reason": r.reason,
                "resolved": r.resolved,
                "repair": repair,
            })
        return result
