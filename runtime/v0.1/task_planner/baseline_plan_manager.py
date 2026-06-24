"""
Baseline Plan Manager — Session 091.

A competent plain-SQLite task planner. No governance layer.
Comparison object for Kill Test 11.

Design principle: do NOT make this a straw man. The baseline uses the same
storage structure and would be considered a reasonable implementation by a
competent engineer who hasn't read RITAM's governance papers.

What the baseline CAN do:
  - Store tasks in all categories reliably with timestamps.
  - Retrieve tasks by category.
  - list_conflicts(): heuristic post-hoc scan — same category, different
    content hash. Detects that two current-task entries exist, but only
    AFTER both are already stored.
  - governance_event_count(): always 0.

What the baseline CANNOT do:
  - Enforce the single-task invariant. A second current-task entry is stored
    silently alongside the first. No signal is raised at write time.
  - Enforce the single-goal invariant. A second plan-goal is stored silently.
  - Surface coherence failures before they happen.

API surface (identical to GovernedTaskPlanner for Kill Test comparability).

Session 091.
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


class BaselinePlanManager:
    """
    Plain SQLite task planner — no governance layer.

    Two simultaneous current-task entries are stored silently. No signal
    is raised. The coherence failure is only detectable post-hoc via the
    heuristic list_conflicts() scan.
    """

    def __init__(self, storage_path: str) -> None:
        storage = Path(storage_path)
        storage.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(
            str(storage / "baseline_plan.db"), check_same_thread=False
        )
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

    def set_goal(self, content: str, source: str = "agent") -> dict:
        """Store a goal. No conflict check. Multiple goals stored silently."""
        return self._store(content, "plan-goal", source)

    def start_task(self, content: str, source: str = "agent") -> dict:
        """
        Store a current-task. No conflict check. If a current-task already
        exists, both are stored silently. No signal is raised.
        """
        return self._store(content, "current-task", source)

    def queue_task(self, content: str, source: str = "agent") -> dict:
        return self._store(content, "pending-task", source)

    def complete_task(self, content: str, source: str = "agent") -> dict:
        return self._store(content, "completed-task", source)

    def block_task(self, content: str, source: str = "agent") -> dict:
        return self._store(content, "blocked-task", source)

    def add_note(self, content: str, source: str = "agent") -> dict:
        return self._store(content, "plan-note", source)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def query(self, category: str) -> list[dict]:
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
        Heuristic: same category, different content hash.
        Both entries are already stored before this check runs.
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
                    "quarantined_at": None,
                    "reason": "Heuristic: same category, different content.",
                    "resolved": False,
                })
        return results

    def governance_event_count(self) -> int:
        """Always 0. The baseline has no governance concept."""
        return 0

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def export_snapshot(self, path: str) -> int:
        rows = self._db.execute(
            """SELECT entry_id, category, content_json, source, created_at
               FROM entries ORDER BY created_at"""
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
            "description": "BaselinePlanManager snapshot. All entries. Session 091.",
            "entry_count": len(entries),
            "entries": entries,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(snapshot, indent=2, default=str))
        return len(entries)

    def load_snapshot(self, path: str) -> tuple[int, int]:
        data = json.loads(Path(path).read_text())
        entries = data.get("entries", [])
        loaded = 0
        for entry in entries:
            content = entry["content"]
            if not isinstance(content, str):
                content = json.dumps(content)
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
                """INSERT INTO entries
                   (entry_id, category, content_hash, content_json, source, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    entry_id, category,
                    _content_hash(content),
                    json.dumps(content),
                    source, _now(),
                ),
            )
        return {
            "status": "stored",
            "entry_id": entry_id,
            "message": f"Stored. category='{category}', source='{source}'.",
        }
