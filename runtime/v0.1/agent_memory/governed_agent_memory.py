"""
Governed Agent Memory — Session 088.

A thin consumer that wraps ritam.runtime.v01.Substrate to govern
RITAM programme memory: the facts, decisions, hypotheses, and questions
the programme accumulates across sessions.

Design contract:
  GovernedAgentMemory does NOT reimplement admission control, contradiction
  detection, or observation-gap surfacing. All governance is provided by the
  substrate. This class translates substrate verdicts into programme-memory
  language.

Category vocabulary:
  programme-fact        PLURAL    Facts about programme state (run counts,
                                  version numbers, empirical observations).
                                  Multiple facts accumulate without conflict.

  governing-hypothesis  SINGULAR  The programme\'s canonical foundational
                                  hypothesis (currently P4b). At-most-one;
                                  if a later session asserts a contradictory
                                  governing hypothesis, the substrate quarantines
                                  it and emits a governance event.

  open-question         PLURAL    Tracked open questions (OQ-NNN). Multiple
                                  coexist; they are resolved by new entries
                                  in other categories, not by replacement.

  decision              PLURAL    Programme decisions/ADRs. Multiple decisions
                                  accumulate. Superseded decisions are recorded
                                  as new decisions referencing the prior one
                                  (append-only principle).

  insight               PLURAL    Programme insights (INSIGHT-NNN). Multiple
                                  insights accumulate.

Thin-consumer test:
  If AdmissionGateway were replaced with a no-op returning ADMITTED,
  GovernedAgentMemory would silently accept all inputs including contradictory
  governing hypotheses, with no governance. That collapse proves governance
  lives in the substrate.

API surface (matches BaselineAgentMemory exactly for Kill Test comparability):
  add_fact(content, source)                   -> MemoryResult
  set_governing_hypothesis(content, source)   -> MemoryResult
  add_question(content, source)               -> MemoryResult
  add_decision(content, source)               -> MemoryResult
  add_insight(content, source)                -> MemoryResult
  query(category)                             -> list[dict]
  list_conflicts()                            -> list[dict]
  governance_event_count()                    -> int

Session 088. No LLM, no embeddings, no async (Appendix B, API_SPEC.md).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ritam.runtime.v01 import (
    AdmissionVerdict,
    SignalType,
    Substrate,
    SubstrateConfig,
)


# ---------------------------------------------------------------------------
# Category vocabulary
# ---------------------------------------------------------------------------

PROGRAMME_CATEGORIES = [
    "programme-fact",
    "governing-hypothesis",
    "open-question",
    "decision",
    "insight",
]

# governing-hypothesis is SINGULAR: at-most-one canonical governing hypothesis.
# All other categories are PLURAL: multiple entries coexist without conflict.
# PLURAL: multiple entries coexist. Categories NOT in this list → SINGULAR enforcement.
SINGULAR_CATEGORIES = ["governing-hypothesis"]
# governing-hypothesis is the only SINGULAR category — at-most-one enforced.
# All others (programme-fact, open-question, decision, insight) are plural: they accumulate.


# ---------------------------------------------------------------------------
# Result type — programme-memory language, not substrate-level
# ---------------------------------------------------------------------------

@dataclass
class MemoryResult:
    """
    What GovernedAgentMemory returns after a write operation.

    status:
      "stored"    — entry admitted; in the programme\'s knowledge base.
      "conflict"  — entry contradicts existing knowledge; governance event raised;
                    both sides preserved in the contradiction store.
      "gap"       — category unknown to this memory; no entry stored.
      "error"     — entry rejected (e.g., empty content); no entry stored.

    entry_id:     assigned if status is \'stored\' or \'conflict\'.
    conflict_with: list of item_ids that this entry contradicts.
    message:       human-readable explanation.
    """
    status: str
    entry_id: str | None
    conflict_with: list[str] = field(default_factory=list)
    message: str = ""


# ---------------------------------------------------------------------------
# Governed Agent Memory
# ---------------------------------------------------------------------------

class GovernedAgentMemory:
    """
    Programme memory where every write passes through substrate governance.

    The singular category (governing-hypothesis) enforces at-most-one canonical
    governing hypothesis. Any attempt to record a contradictory governing
    hypothesis is quarantined and a governance event is raised.

    Instantiation:
        memory = GovernedAgentMemory(storage_path="./programme_memory")
    """

    def __init__(self, storage_path: str) -> None:
        config = SubstrateConfig(
            storage_path=storage_path,
            known_categories=PROGRAMME_CATEGORIES,
            singular_categories=SINGULAR_CATEGORIES,
            decay_enabled=False,
            decay_interval_seconds=3600,
        )
        self._substrate = Substrate(config)
        self._gw = self._substrate.admission_gateway()
        self._cs = self._substrate.contradiction_store()
        self._oc = self._substrate.observation_channel()
        self._governance_events: list[dict] = []

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add_fact(self, content: str, source: str = "programme") -> MemoryResult:
        """Add a programme fact. PLURAL: multiple facts accumulate."""
        return self._write(content, "programme-fact", source)

    def set_governing_hypothesis(self, content: str, source: str = "programme") -> MemoryResult:
        """
        Record the programme\'s governing hypothesis. SINGULAR.

        If a governing hypothesis already exists, this call will be QUARANTINED.
        The governance event is recorded — the contradiction is preserved, not
        silently overwritten.

        The existing hypothesis is NOT replaced. Resolution requires an explicit
        programme decision (a new decision entry) followed by retracting the
        superseded hypothesis via substrate retraction (v0.3 scope).
        """
        return self._write(content, "governing-hypothesis", source)

    def add_question(self, content: str, source: str = "programme") -> MemoryResult:
        """Add an open question. PLURAL: multiple questions accumulate."""
        return self._write(content, "open-question", source)

    def add_decision(self, content: str, source: str = "programme") -> MemoryResult:
        """Add a programme decision. PLURAL: decisions accumulate."""
        return self._write(content, "decision", source)

    def add_insight(self, content: str, source: str = "programme") -> MemoryResult:
        """Add a programme insight. PLURAL: insights accumulate."""
        return self._write(content, "insight", source)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def query(self, category: str) -> list[dict]:
        """Return all admitted entries in a category."""
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

    def list_conflicts(self) -> list[dict]:
        """Return all quarantined conflict records."""
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

    def governance_event_count(self) -> int:
        """Number of governance events raised this session."""
        return len(self._governance_events)


    # ------------------------------------------------------------------
    # Persistence — snapshot export / import (OQ-058, Session 090)
    # ------------------------------------------------------------------

    def export_snapshot(self, path: str) -> int:
        """
        Export all admitted entries to a JSON snapshot file.

        Returns the count of entries written. The snapshot captures the
        programme's accepted knowledge state at the time of export. Quarantined
        (conflicting) entries are NOT included — the snapshot represents
        admitted truth, not rejected proposals.

        The snapshot can be loaded into a fresh GovernedAgentMemory instance
        in a later Python process to simulate cross-session persistence.
        """
        db = self._substrate._db
        rows = db.execute(
            """SELECT item_id, category, content_json, source, admitted_at
               FROM items WHERE retracted = 0
               ORDER BY admitted_at"""
        ).fetchall()
        entries = [
            {
                "item_id": row[0],
                "category": row[1],
                "content": json.loads(row[2]),
                "source": row[3],
                "admitted_at": row[4],
            }
            for row in rows
        ]
        snapshot = {
            "snapshot_version": "1",
            "description": (
                "GovernedAgentMemory snapshot. Admitted entries only. "
                "Generated by export_snapshot(). Load with load_snapshot()."
            ),
            "entry_count": len(entries),
            "entries": entries,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(snapshot, indent=2, default=str))
        return len(entries)

    def load_snapshot(self, path: str) -> tuple[int, int]:
        """
        Load entries from a JSON snapshot file into this GovernedAgentMemory.

        Every entry is re-admitted via the AdmissionGateway, so governance
        fires normally on any contradiction present in the snapshot (which
        should be zero if the snapshot was produced from a clean run).

        Returns (loaded_count, governance_events_during_load).

        Use case: simulate cross-process persistence. Run 1 exports; Run 2
        creates a fresh GovernedAgentMemory, calls load_snapshot(), then
        continues adding entries. Contradictions against the loaded history
        are governed — this is the core of OQ-058.
        """
        data = json.loads(Path(path).read_text())
        entries = data.get("entries", [])
        loaded = 0
        events_before = self.governance_event_count()
        for entry in entries:
            content = entry["content"]
            if not isinstance(content, str):
                content = json.dumps(content)
            result = self._write(content, entry["category"], entry.get("source", "snapshot"))
            if result.status == "stored":
                loaded += 1
        events_during = self.governance_event_count() - events_before
        return loaded, events_during

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write(self, content: str, category: str, source: str) -> MemoryResult:
        result = self._gw.propose(content, category, source)

        if result.verdict == AdmissionVerdict.ADMITTED:
            return MemoryResult(
                status="stored",
                entry_id=result.item_id,
                message=(
                    f"Admitted to \'{category}\'. "
                    f"source=\'{source}\', id={result.item_id}."
                ),
            )

        if result.verdict == AdmissionVerdict.QUARANTINED:
            event = {
                "category": category,
                "content": content,
                "conflict_ids": result.conflict_ids,
                "quarantine_id": result.item_id,
            }
            self._governance_events.append(event)
            return MemoryResult(
                status="conflict",
                entry_id=result.item_id,
                conflict_with=result.conflict_ids,
                message=(
                    f"GOVERNANCE EVENT: conflict in \'{category}\'. "
                    f"Incoming entry contradicts {result.conflict_ids}. "
                    f"Both preserved in contradiction store. "
                    f"Governance event #{len(self._governance_events)} raised."
                ),
            )

        # REJECTED — distinguish gap vs error
        signals = self._oc.drain()
        gap_signals = [s for s in signals if s.signal_type == SignalType.OBSERVATION_GAP]
        if gap_signals:
            gap_cat = gap_signals[0].category
            return MemoryResult(
                status="gap",
                entry_id=None,
                message=(
                    f"Category \'{gap_cat}\' is not known to this memory. "
                    f"Entry not stored. Known: {PROGRAMME_CATEGORIES}."
                ),
            )

        return MemoryResult(
            status="error",
            entry_id=None,
            message=f"Entry rejected: {result.reason}",
        )
