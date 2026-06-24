"""
ritam.runtime.v01.contradiction_store
ContradictionStore — read-only view over all quarantined contradictions,
plus repair retrieval and resolution recording (Session 094, ADR-016 C2).

Invariants (from API_SPEC.md §2):
- I8: contradictions are surfaced, never hidden.
- I3: all held contradictions are inspectable.
- A-list #3: retrieval pool is protected; no query can delete or overwrite.

This interface is primarily READ-ONLY. The only write operation is
mark_resolved() — a narrow exception that closes the repair loop (I5)
without modifying the contradiction record itself. Admitted per ADR-016 C2.
Session 079. Session 094: added get_repair(), mark_resolved().
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from .types import ContradictionRecord, RepairSuggestion, ResolutionPathway


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


class ContradictionStore:
    """
    Access to all preserved contradictions and their repair suggestions.
    See API_SPEC.md §2 for the full contract.
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    def _build_record(self, q_row: tuple, item_rows: list[tuple]) -> ContradictionRecord:
        quarantine_id, category, reason, quarantined_at, resolved = q_row[:5]
        resolution_note = q_row[5] if len(q_row) > 5 else None
        item_ids = [r[0] for r in item_rows]
        contents = [json.loads(r[1]) for r in item_rows]
        categories = [category] * len(item_rows)
        sources = [r[2] for r in item_rows]
        return ContradictionRecord(
            quarantine_id=quarantine_id,
            item_ids=item_ids,
            contents=contents,
            categories=categories,
            sources=sources,
            quarantined_at=_parse_dt(quarantined_at),
            reason=reason,
            resolved=bool(resolved),
            resolution_note=resolution_note,
        )

    def _fetch_items(self, quarantine_id: str) -> list[tuple]:
        cur = self._db.execute(
            "SELECT item_id, content_json, source FROM quarantine_items WHERE quarantine_id = ?",
            (quarantine_id,),
        )
        return cur.fetchall()

    def _fetch_quarantine_row(self, quarantine_id: str) -> tuple | None:
        return self._db.execute(
            """SELECT quarantine_id, category, reason, quarantined_at, resolved, resolution_note
               FROM quarantine WHERE quarantine_id = ?""",
            (quarantine_id,),
        ).fetchone()

    # ------------------------------------------------------------------
    # Read operations (original interface)
    # ------------------------------------------------------------------

    def get(self, quarantine_id: str) -> ContradictionRecord | None:
        row = self._fetch_quarantine_row(quarantine_id)
        if row is None:
            return None
        return self._build_record(row, self._fetch_items(quarantine_id))

    def list_all(self) -> list[ContradictionRecord]:
        rows = self._db.execute(
            """SELECT quarantine_id, category, reason, quarantined_at, resolved, resolution_note
               FROM quarantine ORDER BY quarantined_at ASC"""
        ).fetchall()
        return [self._build_record(r, self._fetch_items(r[0])) for r in rows]

    def list_by_category(self, category: str) -> list[ContradictionRecord]:
        rows = self._db.execute(
            """SELECT quarantine_id, category, reason, quarantined_at, resolved, resolution_note
               FROM quarantine WHERE category = ? ORDER BY quarantined_at ASC""",
            (category,),
        ).fetchall()
        return [self._build_record(r, self._fetch_items(r[0])) for r in rows]

    def list_involving(self, item_id: str) -> list[ContradictionRecord]:
        rows = self._db.execute(
            """
            SELECT DISTINCT q.quarantine_id, q.category, q.reason, q.quarantined_at,
                            q.resolved, q.resolution_note
            FROM quarantine q
            JOIN quarantine_items qi ON qi.quarantine_id = q.quarantine_id
            WHERE qi.item_id = ?
            ORDER BY q.quarantined_at ASC
            """,
            (item_id,),
        ).fetchall()
        return [self._build_record(r, self._fetch_items(r[0])) for r in rows]

    def count(self) -> int:
        row = self._db.execute("SELECT COUNT(*) FROM quarantine").fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------
    # Repair operations (Session 094 — ADR-016 C2)
    # ------------------------------------------------------------------

    def get_repair(self, quarantine_id: str) -> RepairSuggestion | None:
        """
        Return the RepairSuggestion stored for a quarantine event, or None if
        not found or if the record predates Session 094.

        The repair suggestion contains both sides of the conflict, the rule
        that triggered, and three actionable resolution pathways.
        """
        row = self._db.execute(
            "SELECT repair_json FROM quarantine WHERE quarantine_id = ?",
            (quarantine_id,),
        ).fetchone()
        if row is None or row[0] is None:
            return None
        try:
            data = json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return None

        pathways = [
            ResolutionPathway(
                pathway_id=p["pathway_id"],
                description=p["description"],
                action_required=p["action_required"],
            )
            for p in data.get("resolution_pathways", [])
        ]
        return RepairSuggestion(
            quarantine_id=data["quarantine_id"],
            category=data["category"],
            rule_triggered=data["rule_triggered"],
            incoming_content=data["incoming_content"],
            incoming_source=data["incoming_source"],
            existing_items=data.get("existing_items", []),
            resolution_pathways=pathways,
            generated_at=_parse_dt(data["generated_at"]),
        )

    def mark_resolved(self, quarantine_id: str, resolution_note: str) -> bool:
        """
        Mark a quarantine record as resolved and record the resolution taken.

        This is the narrow write exception on ContradictionStore (ADR-016 C2,
        I5 Observable Repair Loops). It does NOT delete or modify the
        contradiction record — it adds a resolution note and flips the
        resolved flag. The original conflict is permanently preserved (I8).

        resolution_note: free-text description of the pathway taken and why.
          Convention: start with the pathway_id, e.g.
          "RETRACT_EXISTING: incoming measurement supersedes prior estimate."
          "KEEP_EXISTING: incoming entry was a duplicate error."
          "HOLD_AS_CONTRADICTION: both readings valid in different contexts."

        Returns True if the record was found and updated, False otherwise.
        """
        row = self._db.execute(
            "SELECT quarantine_id, resolved FROM quarantine WHERE quarantine_id = ?",
            (quarantine_id,),
        ).fetchone()
        if row is None:
            return False
        try:
            with self._db:
                self._db.execute(
                    """UPDATE quarantine SET resolved = 1, resolution_note = ?
                       WHERE quarantine_id = ?""",
                    (resolution_note, quarantine_id),
                )
            return True
        except Exception:
            return False
