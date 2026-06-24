"""
Governed Task Planner — Session 091.

Third substrate consumer. Wraps ritam.runtime.v01.Substrate to govern
an AI agent's task plan: the goal it is pursuing, the task it is currently
working on, and the tasks it intends to do or has completed.

This consumer is materially different from GovernedNotebook (scientific
observation) and GovernedAgentMemory (programme history):

  Domain:    Executable work — what an agent IS doing and WILL do.
  Invariant: One plan goal; one active task at a time.
  Governance story: Prevents concurrent-task incoherence in agent behaviour.

Two SINGULAR categories (plan-goal, current-task) — the first consumer
in the RITAM substrate portfolio with more than one SINGULAR constraint.
This tests whether the substrate can enforce multiple independent singular
constraints simultaneously.

Category vocabulary:

  plan-goal       SINGULAR  What this plan is trying to achieve.
                            At-most-one. If you try to change the goal
                            mid-plan, governance fires. A plan can only
                            be redirected by resolving the existing goal
                            first (v0.3 retraction scope).

  current-task    SINGULAR  The task being actively worked on RIGHT NOW.
                            At-most-one. If something tries to claim a
                            second concurrent task, it is QUARANTINED.
                            This is the core coherence invariant for
                            single-agent task execution: one thing at a time.

  pending-task    PLURAL    Tasks queued but not yet started. Multiple
                            pending tasks accumulate without conflict.

  completed-task  PLURAL    Finished tasks. Append-only record. A completed
                            task is never removed — it becomes part of the
                            plan history.

  blocked-task    PLURAL    Tasks waiting on an external dependency or
                            blocked by a prior task's outcome.

  plan-note       PLURAL    Annotations, context, decisions made during
                            execution. Free-form notes accumulate.

Thin-consumer test:
  If AdmissionGateway were replaced with a no-op returning ADMITTED,
  GovernedTaskPlanner would silently accept two simultaneous current-task
  entries, violating the one-task-at-a-time invariant with no signal.
  That collapse proves governance lives in the substrate.

Materiality argument (why this is a different consumer domain):
  GovernedNotebook stores observations about the world (what was seen).
  GovernedAgentMemory stores programme history (what was decided/learned).
  GovernedTaskPlanner stores executable intentions (what will be done).
  The substrate's governance engine is identical in all three cases —
  only the category vocabulary changes. This is the substrate-generality
  evidence that Sessions 088-089 could not yet provide.

API surface (matches GovernedAgentMemory pattern for Kill Test comparability):
  set_goal(content, source)              -> PlanResult
  start_task(content, source)            -> PlanResult
  queue_task(content, source)            -> PlanResult
  complete_task(content, source)         -> PlanResult
  block_task(content, source)            -> PlanResult
  add_note(content, source)              -> PlanResult
  query(category)                        -> list[dict]
  list_conflicts()                       -> list[dict]
  governance_event_count()               -> int
  export_snapshot(path)                  -> int
  load_snapshot(path)                    -> tuple[int, int]

Session 091. No LLM, no embeddings, no async (Appendix B, API_SPEC.md).
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

PLAN_CATEGORIES = [
    "plan-goal",
    "current-task",
    "pending-task",
    "completed-task",
    "blocked-task",
    "plan-note",
]

# plan-goal and current-task are SINGULAR — at-most-one enforced.
# All others (pending-task, completed-task, blocked-task, plan-note) are plural: they accumulate.
SINGULAR_CATEGORIES = ["plan-goal", "current-task"]


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class PlanResult:
    """
    What GovernedTaskPlanner returns after a write operation.

    status:
      "stored"    — entry admitted and in the plan.
      "conflict"  — entry contradicts an existing singular entry;
                    governance event raised; both sides preserved.
      "gap"       — category unknown; entry not stored.
      "error"     — entry rejected (e.g., empty content).

    entry_id:      assigned if status is 'stored' or 'conflict'.
    conflict_with: list of item_ids this entry contradicts.
    message:       human-readable explanation.
    """
    status: str
    entry_id: str | None
    conflict_with: list[str] = field(default_factory=list)
    message: str = ""


# ---------------------------------------------------------------------------
# Governed Task Planner
# ---------------------------------------------------------------------------

class GovernedTaskPlanner:
    """
    Task plan where every write passes through substrate governance.

    Two singular invariants are enforced simultaneously:
      1. One plan-goal: a plan pursues exactly one goal.
      2. One current-task: an agent works on exactly one task at a time.

    Attempting to assert a second goal or start a second concurrent task
    triggers a governance event. Both sides of the conflict are preserved
    in the substrate's ContradictionStore — the incoherence is visible,
    not silently resolved.

    Instantiation:
        planner = GovernedTaskPlanner(storage_path="./task_plan")
    """

    def __init__(self, storage_path: str) -> None:
        config = SubstrateConfig(
            storage_path=storage_path,
            known_categories=PLAN_CATEGORIES,
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

    def set_goal(self, content: str, source: str = "agent") -> PlanResult:
        """
        Set the plan's goal. SINGULAR.

        Only one goal is permitted per plan. If a goal already exists,
        this call is QUARANTINED and a governance event is raised.
        The existing goal is preserved — changing the goal mid-plan
        requires explicit resolution (v0.3 retraction scope).
        """
        return self._write(content, "plan-goal", source)

    def start_task(self, content: str, source: str = "agent") -> PlanResult:
        """
        Mark a task as currently being worked on. SINGULAR.

        Only one current task is permitted at a time. If a current-task
        already exists, this call is QUARANTINED and a governance event
        is raised. This enforces the single-agent coherence invariant:
        an agent works on exactly one thing at a time.

        To switch tasks, the existing current-task must be moved to
        completed-task or blocked-task first (v0.3 retraction scope).
        """
        return self._write(content, "current-task", source)

    def queue_task(self, content: str, source: str = "agent") -> PlanResult:
        """Add a task to the pending queue. PLURAL."""
        return self._write(content, "pending-task", source)

    def complete_task(self, content: str, source: str = "agent") -> PlanResult:
        """Record a completed task. PLURAL. Append-only."""
        return self._write(content, "completed-task", source)

    def block_task(self, content: str, source: str = "agent") -> PlanResult:
        """Record a blocked task. PLURAL."""
        return self._write(content, "blocked-task", source)

    def add_note(self, content: str, source: str = "agent") -> PlanResult:
        """Add a plan note or annotation. PLURAL."""
        return self._write(content, "plan-note", source)

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
    # Persistence (OQ-058 pattern, Session 090)
    # ------------------------------------------------------------------

    def export_snapshot(self, path: str) -> int:
        """Export all admitted entries to a JSON snapshot. Returns count."""
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
                "GovernedTaskPlanner snapshot. Admitted entries only. "
                "Session 091."
            ),
            "entry_count": len(entries),
            "entries": entries,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(snapshot, indent=2, default=str))
        return len(entries)

    def load_snapshot(self, path: str) -> tuple[int, int]:
        """
        Load entries from a JSON snapshot. Returns (loaded, gov_events_during_load).
        Simulates cross-process persistence (OQ-058 pattern).
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

    def _write(self, content: str, category: str, source: str) -> PlanResult:
        result = self._gw.propose(content, category, source)

        if result.verdict == AdmissionVerdict.ADMITTED:
            return PlanResult(
                status="stored",
                entry_id=result.item_id,
                message=(
                    f"Admitted to '{category}'. "
                    f"source='{source}', id={result.item_id}."
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
            return PlanResult(
                status="conflict",
                entry_id=result.item_id,
                conflict_with=result.conflict_ids,
                message=(
                    f"GOVERNANCE EVENT: conflict in '{category}'. "
                    f"Incoming entry contradicts {result.conflict_ids}. "
                    f"Both preserved in contradiction store. "
                    f"Governance event #{len(self._governance_events)} raised."
                ),
            )

        # REJECTED
        signals = self._oc.drain()
        gap_signals = [s for s in signals if s.signal_type == SignalType.OBSERVATION_GAP]
        if gap_signals:
            gap_cat = gap_signals[0].category
            return PlanResult(
                status="gap",
                entry_id=None,
                message=(
                    f"Category '{gap_cat}' is not known to this planner. "
                    f"Entry not stored. Known: {PLAN_CATEGORIES}."
                ),
            )

        return PlanResult(
            status="error",
            entry_id=None,
            message=f"Entry rejected: {result.reason}",
        )
