"""
Kill Test Baseline Notebook — Session 080.

A competent, honest plain-dict + SQLite research notebook.
No AdmissionGateway. No ContradictionStore. No ObservationChannel.

This is the comparison object for the Kill Test.
Design principle: do NOT deliberately make this worse than a competent engineer
would build. The Kill Test is only meaningful if the baseline is genuinely good
at what it does. If the baseline is a straw man, the comparison proves nothing.

What this baseline CAN do well:
  - Store entries reliably with timestamps and source attribution
  - Retrieve entries by id or category
  - list_contradictions() is intentionally honest: it does its best using a
    simple heuristic (entries in the same category from different sources)
    but it has no structural guarantee. Silent acceptance is the norm.
  - list_observation_gaps() returns an empty list — the baseline has no
    mechanism to detect what it doesn't know.

API surface (identical to GovernedNotebook for Kill Test comparability):
  add_entry(content, category, source)     -> dict
  get_entry(item_id)                       -> dict | None
  query_by_category(category)              -> list[dict]
  list_contradictions(category=None)       -> list[dict]
  list_observation_gaps()                  -> list[dict]

Session 080.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _content_hash(content: Any) -> str:
    serialised = json.dumps(content, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode()).hexdigest()


class BaselineNotebook:
    """
    Plain SQLite research notebook — no governance layer.

    All entries are accepted. Contradiction detection is heuristic (same
    category, different content hash, different source). There is no
    structural guarantee that conflicts will be detected.

    Observation gaps are not surfaced — unknown categories are accepted silently.
    The caller receives no signal that a category may be outside the notebook's
    intended scope.
    """

    def __init__(self, storage_path: str) -> None:
        storage = Path(storage_path)
        storage.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(storage / "baseline.db"), check_same_thread=False)
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
    # Core API
    # ------------------------------------------------------------------

    def add_entry(self, content: Any, category: str, source: str) -> dict:
        """
        Add an entry. Always succeeds. Returns a result dict.

        Note: no contradiction check before writing. No category validation.
        The entry is stored regardless of whether it conflicts with existing
        knowledge or whether the category makes sense.
        """
        entry_id = _new_id()
        content_hash = _content_hash(content)
        content_json = json.dumps(content, default=str)
        created_at = _now()

        with self._db:
            self._db.execute(
                """INSERT INTO entries (entry_id, category, content_hash, content_json, source, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (entry_id, category, content_hash, content_json, source, created_at),
            )

        return {
            "status": "stored",
            "entry_id": entry_id,
            "message": f"Entry stored. category='{category}', source='{source}'.",
        }

    def get_entry(self, entry_id: str) -> dict | None:
        """Retrieve an entry by id. Returns None if not found."""
        row = self._db.execute(
            """SELECT entry_id, category, content_json, source, created_at
               FROM entries WHERE entry_id = ?""",
            (entry_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "item_id": row[0],
            "category": row[1],
            "content": json.loads(row[2]),
            "source": row[3],
            "admitted_at": row[4],   # named to match GovernedNotebook for comparability
        }

    def query_by_category(self, category: str) -> list[dict]:
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

    def list_contradictions(self, category: str | None = None) -> list[dict]:
        """
        Heuristic contradiction detection: entries in the same category
        from different sources with different content hashes.

        This is NOT structural. It will miss contradictions from the same
        source. It has no guarantee of completeness. Entries are already
        stored by the time this is called — there is no pre-write check.
        """
        if category is not None:
            rows = self._db.execute(
                """SELECT e1.entry_id, e1.content_json, e1.source,
                          e2.entry_id, e2.content_json, e2.source,
                          e1.category
                   FROM entries e1
                   JOIN entries e2
                     ON e1.category = e2.category
                    AND e1.content_hash != e2.content_hash
                    AND e1.entry_id < e2.entry_id
                   WHERE e1.category = ?""",
                (category,),
            ).fetchall()
        else:
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
                    "quarantine_id": None,        # no quarantine concept
                    "category": row[6],
                    "items": [
                        {"item_id": row[0], "content": json.loads(row[1]), "source": row[2]},
                        {"item_id": row[3], "content": json.loads(row[4]), "source": row[5]},
                    ],
                    "quarantined_at": None,       # not quarantined — both silently stored
                    "reason": "Heuristic: same category, different content hash.",
                    "resolved": False,
                })
        return results

    def list_observation_gaps(self) -> list[dict]:
        """
        Always returns an empty list.

        The baseline has no category validation and therefore no mechanism
        to detect that an entry was filed in an unknown or unexpected category.
        If you filed 'Order 50 GPU servers' under 'action-item', the baseline
        stored it without comment.
        """
        return []
