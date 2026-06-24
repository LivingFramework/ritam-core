"""
Baseline Agent Memory — Session 088.

A competent, honest plain-SQLite programme memory store.
No AdmissionGateway. No ContradictionStore. No ObservationChannel.

This is the comparison object for Kill Test 8.

Design principle: do NOT deliberately make this worse than a competent engineer
would build. The Kill Test is only meaningful if the baseline is genuinely good
at what it does. If the baseline is a straw man, the comparison proves nothing.

What the baseline CAN do well:
  - Store programme facts, decisions, insights reliably with timestamps
  - Retrieve entries by category
  - list_conflicts(): heuristic — same category, different content hash, different
    source. NOT structural. Entries are ALREADY STORED before this check runs.
  - governance_event_count(): always 0 — the baseline has no governance concept.

What the baseline CANNOT do:
  - Enforce at-most-one governing hypothesis. A contradictory governing hypothesis
    is stored silently alongside the original. No signal is raised.
  - Surface conflicts at write time. list_conflicts() is post-hoc and heuristic.

API surface (identical to GovernedAgentMemory for Kill Test comparability):
  add_fact(content, source)                   -> dict
  set_governing_hypothesis(content, source)   -> dict
  add_question(content, source)               -> dict
  add_decision(content, source)               -> dict
  add_insight(content, source)                -> dict
  query(category)                             -> list[dict]
  list_conflicts()                            -> list[dict]
  governance_event_count()                    -> int

Session 088.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


class BaselineAgentMemory:
    """
    Plain SQLite programme memory — no governance layer.

    All entries are accepted. Conflict detection is heuristic and post-hoc.
    Contradictory governing hypotheses are stored silently alongside the original.
    No governance event is ever raised.
    """

    def __init__(self, storage_path: str) -> None:
        storage = Path(storage_path)
        storage.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(storage / "baseline_memory.db"), check_same_thread=False)
        self._setup_schema()

    def _setup_schema(self) -> None:
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS entries (
                entry_id      TEXT PRIMARY KEY,
                category      TEXT NOT NULL,
                content_hash  TEXT NOT NULL,
                content_json  TEXT NOT NULL,
                source        TEXT NOT NULL,
                created_at    TEXT NOT NULL
            );
        """)
        self._db.commit()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add_fact(self, content: str, source: str = "programme") -> dict:
        return self._store(content, "programme-fact", source)

    def set_governing_hypothesis(self, content: str, source: str = "programme") -> dict:
        """
        Store a governing hypothesis. No conflict check. If a governing hypothesis
        already exists, both are stored silently. No signal is raised.
        """
        return self._store(content, "governing-hypothesis", source)

    def add_question(self, content: str, source: str = "programme") -> dict:
        return self._store(content, "open-question", source)

    def add_decision(self, content: str, source: str = "programme") -> dict:
        return self._store(content, "decision", source)

    def add_insight(self, content: str, source: str = "programme") -> dict:
        return self._store(content, "insight", source)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def query(self, category: str) -> list[dict]:
        """Return all entries in a category."""
        rows = self._db.execute(
            """SELECT entry_id, content_json, source, created_at
               FROM entries WHERE category = ?
               ORDER BY created_at""",
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
        """
        Heuristic conflict detection: entries in the same category with
        different content hashes.

        NOT structural. Conflicts are detected AFTER both entries are already
        stored. There is no pre-write check. The baseline does not distinguish
        a legitimate second fact from a contradictory governing hypothesis.
        """
        rows = self._db.execute(
            """SELECT e1.entry_id, e1.content_json, e1.source,
                      e2.entry_id, e2.content_json, e2.source,
                      e1.category
               FROM entries e1
               JOIN entries e2
                 ON e1.category = e2.category
                AND e1.content_hash != e2.content_hash
                AND e1.entry_id < e2.entry_id""",
        ).fetchall()

        seen = set()
        results = []
        for row in rows:
            key = (row[0], row[3])
            if key not in seen:
                seen.add(key)
                results.append({
                    "quarantine_id": None,
                    "category": row[6],
                    "items": [
                        {"item_id": row[0], "content": json.loads(row[1]), "source": row[2]},
                        {"item_id": row[3], "content": json.loads(row[4]), "source": row[5]},
                    ],
                    "quarantined_at": None,   # not quarantined — both silently stored
                    "reason": "Heuristic: same category, different content.",
                    "resolved": False,
                })
        return results

    def governance_event_count(self) -> int:
        """Always 0. The baseline has no governance concept."""
        return 0


    # ------------------------------------------------------------------
    # Persistence — snapshot export / import (OQ-058, Session 090)
    # ------------------------------------------------------------------

    def export_snapshot(self, path: str) -> int:
        """
        Export all entries to a JSON snapshot file.

        Returns count of entries written. Unlike GovernedAgentMemory, the
        baseline stores everything including contradictions — the snapshot
        contains all entries, not just "admitted" ones, because there is
        no admission concept.
        """
        rows = self._db.execute(
            """SELECT entry_id, category, content_json, source, created_at
               FROM entries ORDER BY created_at"""
        ).fetchall()
        import json as _json
        from pathlib import Path as _Path
        entries = [
            {
                "item_id": row[0],
                "category": row[1],
                "content": _json.loads(row[2]),
                "source": row[3],
                "admitted_at": row[4],
            }
            for row in rows
        ]
        snapshot = {
            "snapshot_version": "1",
            "description": (
                "BaselineAgentMemory snapshot. All stored entries (no governance). "
                "Generated by export_snapshot()."
            ),
            "entry_count": len(entries),
            "entries": entries,
        }
        _Path(path).parent.mkdir(parents=True, exist_ok=True)
        _Path(path).write_text(_json.dumps(snapshot, indent=2, default=str))
        return len(entries)

    def load_snapshot(self, path: str) -> tuple[int, int]:
        """
        Load entries from a JSON snapshot file.

        No governance fires. All entries are stored directly.
        Returns (loaded_count, governance_events_during_load).
        governance_events_during_load is always 0.
        """
        import json as _json
        from pathlib import Path as _Path
        data = _json.loads(_Path(path).read_text())
        entries = data.get("entries", [])
        loaded = 0
        for entry in entries:
            content = entry["content"]
            if not isinstance(content, str):
                content = _json.dumps(content)
            self._store(content, entry["category"], entry.get("source", "snapshot"))
            loaded += 1
        return loaded, 0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _store(self, content: str, category: str, source: str) -> dict:
        entry_id = _new_id()
        with self._db:
            self._db.execute(
                """INSERT INTO entries (entry_id, category, content_hash, content_json, source, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (entry_id, category, _content_hash(content), json.dumps(content), source, _now()),
            )
        return {
            "status": "stored",
            "entry_id": entry_id,
            "message": f"Stored. category=\'{category}\', source=\'{source}\'.",
        }
