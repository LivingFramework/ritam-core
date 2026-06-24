"""
Governed Research Notebook — Session 080.

A thin consumer application that wraps ritam.runtime.v01.Substrate.

Design contract (from API_SPEC.md Appendix C):
  The notebook does NOT reimplement admission control, contradiction detection,
  or observation-gap surfacing. All governance is provided by the substrate.
  The notebook translates substrate verdicts into notebook-level language.

Thin-consumer test (docstring, not a test suite):
  If AdmissionGateway were replaced with a no-op that always returns ADMITTED,
  the notebook would silently accept everything — contradictions, unknown
  categories, duplicates — with no governance. That collapse is the proof that
  governance actually lives in the substrate, not here.

API surface (matches notebook_baseline.py exactly for Kill Test comparability):
  add_entry(content, category, source)     -> NotebookResult
  get_entry(item_id)                       -> dict | None
  query_by_category(category)              -> list[dict]
  list_contradictions(category=None)       -> list[dict]
  list_observation_gaps()                  -> list[dict]

Session 085 (v0.2). No LLM, no embeddings, no async (Appendix B).
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Public interface only — no internal ritam module imports (Appendix C)
from ritam.runtime.v01 import (
    AdmissionVerdict,
    SignalType,
    Substrate,
    SubstrateConfig,
)


# ---------------------------------------------------------------------------
# Result type — notebook-level language, not substrate-level
# ---------------------------------------------------------------------------

@dataclass
class NotebookResult:
    """
    What the notebook tells the caller after an add_entry() call.

    status:
      "admitted"    — entry stored; provenance available
      "conflict"    — entry conflicts with existing knowledge; both preserved
      "gap"         — category unknown to the notebook; no entry stored
      "error"       — governance checkpoint failed; no entry stored

    entry_id: set if an item_id was assigned (admitted or conflict).
    conflict_with: list of item_ids that conflict with this entry.
    gap_category: the unknown category name if status == "gap".
    message: human-readable explanation.
    """
    status: str
    entry_id: str | None
    conflict_with: list[str]
    gap_category: str | None
    message: str


# ---------------------------------------------------------------------------
# Governed Research Notebook
# ---------------------------------------------------------------------------

class GovernedNotebook:
    """
    A research notebook where every entry passes through substrate governance.

    Instantiation:
        notebook = GovernedNotebook(
            storage_path="./notebook_data",
            categories=["empirical-finding", "hypothesis", "question", "method-note", "canonical-claim"]
        )

    The caller names the categories at construction time. Any entry in an
    unknown category surfaces as an observation gap — the notebook cannot
    store what it has no representation for.
    """

    def __init__(self, storage_path: str, categories: list[str]) -> None:
        # Plural categories: allow multiple coexisting entries; no contradiction
        # detection. Singular categories enforce at-most-one canonical content.
        #
        # v0.2 design (OQ-057 fix):
        #   empirical-finding  → PLURAL. Many findings coexist; no false positives
        #                        when two unrelated findings share this category.
        #   hypothesis         → PLURAL. Many hypotheses under investigation.
        #   question           → PLURAL. Open questions accumulate.
        #   method-note        → PLURAL. Procedural notes accumulate.
        #   canonical-claim    → SINGULAR. One authoritative claim per notebook;
        #                        contradiction detection active. Use for the single
        #                        governing assertion the programme is testing.
        _plural_defaults = {"hypothesis", "question", "method-note", "empirical-finding"}
        singular = [c for c in categories if c not in _plural_defaults]

        config = SubstrateConfig(
            storage_path=storage_path,
            known_categories=categories,
            singular_categories=singular,
            decay_enabled=False,          # v0.1: decay not yet wired
            decay_interval_seconds=3600,
        )
        self._substrate = Substrate(config)
        self._gw = self._substrate.admission_gateway()
        self._cs = self._substrate.contradiction_store()
        self._oc = self._substrate.observation_channel()

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def add_entry(self, content: Any, category: str, source: str) -> NotebookResult:
        """
        Add a research entry. Returns a NotebookResult describing what happened.

        The substrate performs admission control. The notebook translates the
        substrate's verdict into notebook-level language and drains any
        observation-gap signals from the channel.
        """
        result = self._gw.propose(content, category, source)

        if result.verdict == AdmissionVerdict.ADMITTED:
            return NotebookResult(
                status="admitted",
                entry_id=result.item_id,
                conflict_with=[],
                gap_category=None,
                message=(
                    f"Entry admitted. "
                    f"Provenance: source='{source}', "
                    f"admitted_at={result.provenance.admitted_at.isoformat()}."
                ),
            )

        if result.verdict == AdmissionVerdict.QUARANTINED:
            return NotebookResult(
                status="conflict",
                entry_id=result.item_id,
                conflict_with=result.conflict_ids,
                gap_category=None,
                message=(
                    f"Conflict detected in category '{category}'. "
                    f"Both this entry and the existing entry are preserved. "
                    f"Review list_contradictions('{category}') to see both sides."
                ),
            )

        # REJECTED — check signals to distinguish gap vs error
        signals = self._oc.drain()
        gap_signals = [s for s in signals if s.signal_type == SignalType.OBSERVATION_GAP]

        if gap_signals:
            gap_cat = gap_signals[0].category
            return NotebookResult(
                status="gap",
                entry_id=None,
                conflict_with=[],
                gap_category=gap_cat,
                message=(
                    f"Category '{gap_cat}' is not known to this notebook. "
                    f"The entry was not stored. "
                    f"Known categories: {sorted(self._gw._known_categories)}."
                ),
            )

        return NotebookResult(
            status="error",
            entry_id=None,
            conflict_with=[],
            gap_category=None,
            message=f"Entry rejected by governance: {result.reason}",
        )

    def get_entry(self, item_id: str) -> dict | None:
        """
        Retrieve an admitted entry by its item_id.
        Returns None if not found or retracted.
        """
        db = self._substrate._db
        row = db.execute(
            """SELECT item_id, category, content_json, source, admitted_at, basis
               FROM items WHERE item_id = ? AND retracted = 0""",
            (item_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "item_id": row[0],
            "category": row[1],
            "content": json.loads(row[2]),
            "source": row[3],
            "admitted_at": row[4],
            "basis": row[5],
        }

    def query_by_category(self, category: str) -> list[dict]:
        """
        Return all admitted (non-retracted) entries in a category.
        Returns an empty list for unknown categories — use list_observation_gaps()
        to see if any entries were rejected because of this.
        """
        db = self._substrate._db
        rows = db.execute(
            """SELECT item_id, content_json, source, admitted_at
               FROM items WHERE category = ? AND retracted = 0
               ORDER BY admitted_at""",
            (category,),
        ).fetchall()
        return [
            {
                "item_id": row[0],
                "content": json.loads(row[1]),
                "source": row[2],
                "admitted_at": row[3],
            }
            for row in rows
        ]

    def list_contradictions(self, category: str | None = None) -> list[dict]:
        """
        Return quarantined contradiction records.
        If category is given, filter to that category.
        Each record contains both sides of the conflict.
        """
        if category is not None:
            records = self._cs.list_by_category(category)
        else:
            records = self._cs.list_all()

        return [
            {
                "quarantine_id": r.quarantine_id,
                "category": r.categories[0] if r.categories else None,
                "items": [
                    {"item_id": iid, "content": c, "source": s}
                    for iid, c, s in zip(r.item_ids, r.contents, r.sources)
                ],
                "quarantined_at": r.quarantined_at.isoformat(),
                "reason": r.reason,
                "resolved": r.resolved,
            }
            for r in records
        ]

    def list_observation_gaps(self) -> list[dict]:
        """
        Return any OBSERVATION_GAP signals currently buffered in the channel.

        Observation gaps are emitted when an entry is proposed in a category
        the notebook has no representation for. They accumulate in the channel
        until drained. Call this to see what categories callers have tried to
        use that the notebook doesn't know about.

        Note: draining clears the buffer. Gaps are also returned as part of
        the NotebookResult when add_entry() is called, so this method is most
        useful for batch inspection after multiple add_entry() calls.
        """
        signals = self._oc.drain()
        return [
            {
                "signal_type": s.signal_type.value,
                "category_attempted": s.category,
                "emitted_at": s.emitted_at.isoformat(),
                "payload": s.payload,
            }
            for s in signals
            if s.signal_type == SignalType.OBSERVATION_GAP
        ]
