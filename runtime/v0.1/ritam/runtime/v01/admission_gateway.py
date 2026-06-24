"""
ritam.runtime.v01.admission_gateway
AdmissionGateway — constitutive, fail-closed, SQLite-backed.

Invariants (from API_SPEC.md §1):
- I1: governance checkpoint runs before any write; error → REJECTED.
- I3: caller always receives a typed AdmissionResult; no silent paths.
- I7: this is the ONLY path by which items enter storage.
- A-list #1: fail-closed (governance error = REJECTED, not silent write).
- A-list #3: on conflict BOTH items are preserved; neither overwritten.
- A-list #5: temporal context evaluated at write time when provided.

Anti-framework (Appendix B): single-process, SQLite, synchronous, no LLM,
no embeddings, no semantic similarity. Contradiction = same category + same
normalised content hash within the category.

Session 085 (v0.2 — added content validation, OQ-056).
Session 094 (C2 Repair — ADR-016): generates RepairSuggestion on every
QUARANTINED event. Stores repair_json in quarantine table. Implements I5.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import json as _json

from .types import (
    AdmissionResult,
    AdmissionVerdict,
    ProvenanceRecord,
    RepairSuggestion,
    RepairRecord,
    ResolutionPathway,
    SignalType,
    SubstrateConfig,
    AdmissionRecord,
    GapRecord,
    BatchProposal,
    BatchResult,
    CoordinationRecord,
    OntologyRecord,
    SubstrateSignal,
    _now,
    _new_id,
)
from .observation_channel import ObservationChannel


def _content_hash(content: Any) -> str:
    """Stable hash of content for contradiction detection. Structural, not semantic."""
    serialised = json.dumps(content, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode()).hexdigest()


def _standard_resolution_pathways(
    category: str,
    existing_item_id: str,
) -> list[ResolutionPathway]:
    """
    Standard three-pathway menu for singular-category conflicts.
    The substrate proposes; the human/consumer decides.
    """
    return [
        ResolutionPathway(
            pathway_id="RETRACT_EXISTING",
            description=(
                f"Retract the existing item in '{category}' and re-submit the incoming item. "
                "Use when the incoming item is more accurate or current."
            ),
            action_required=(
                f"Call gateway.retract('{existing_item_id}', source, reason) "
                "then gateway.propose(incoming_content, category, source)."
            ),
        ),
        ResolutionPathway(
            pathway_id="KEEP_EXISTING",
            description=(
                f"Discard the incoming item. Keep the existing '{category}' entry as-is. "
                "Use when the existing item is correct and the incoming item is an error or outdated."
            ),
            action_required=(
                "No action required — the incoming item is already in quarantine and will not "
                "be admitted. Optionally call store.mark_resolved(quarantine_id, "
                "'KEEP_EXISTING: <reason>') to record the decision."
            ),
        ),
        ResolutionPathway(
            pathway_id="HOLD_AS_CONTRADICTION",
            description=(
                f"Explicitly acknowledge both items as an open contradiction in '{category}'. "
                "Use when the conflict is real and resolution requires more information or "
                "deliberation."
            ),
            action_required=(
                "Call store.mark_resolved(quarantine_id, "
                "'HOLD_AS_CONTRADICTION: <reason>') to record that this contradiction "
                "is known and intentionally held open. Both items remain preserved."
            ),
        ),
    ]


class AdmissionGateway:
    """
    The single entry point for all knowledge entering the substrate.
    See API_SPEC.md §1 for the full contract.
    """

    def __init__(
        self,
        config: SubstrateConfig,
        channel: ObservationChannel,
        db: sqlite3.Connection,
    ) -> None:
        self._known_categories: set[str] = set(config.known_categories)
        self._singular_categories: set[str] = set(config.singular_categories or [])
        self._channel = channel
        self._db = db
        self._setup_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _setup_schema(self) -> None:
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                item_id       TEXT PRIMARY KEY,
                category      TEXT NOT NULL,
                content_hash  TEXT NOT NULL,
                content_json  TEXT NOT NULL,
                source        TEXT NOT NULL,
                admitted_at   TEXT NOT NULL,
                basis         TEXT NOT NULL,
                retracted     INTEGER NOT NULL DEFAULT 0,
                retracted_at  TEXT,
                retracted_by  TEXT,
                retract_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS quarantine (
                quarantine_id   TEXT PRIMARY KEY,
                category        TEXT NOT NULL,
                reason          TEXT NOT NULL,
                quarantined_at  TEXT NOT NULL,
                resolved        INTEGER NOT NULL DEFAULT 0,
                resolution_note TEXT,
                repair_json     TEXT
            );

            CREATE TABLE IF NOT EXISTS quarantine_items (
                quarantine_id  TEXT NOT NULL,
                item_id        TEXT NOT NULL,
                content_json   TEXT NOT NULL,
                source         TEXT NOT NULL,
                FOREIGN KEY (quarantine_id) REFERENCES quarantine(quarantine_id)
            );
        """)
        # Migration: add columns to existing DBs that predate Session 094
        for col, coldef in [
            ("resolution_note", "TEXT"),
            ("repair_json", "TEXT"),
        ]:
            try:
                self._db.execute(f"ALTER TABLE quarantine ADD COLUMN {col} {coldef}")
                self._db.commit()
            except sqlite3.OperationalError:
                pass  # column already exists
        # Migration: add temporal columns to items table (Session 103)
        for col, coldef in [
            ("expires_after_seconds", "INTEGER"),
            ("expired_at", "TEXT"),
        ]:
            try:
                self._db.execute(f"ALTER TABLE items ADD COLUMN {col} {coldef}")
                self._db.commit()
            except sqlite3.OperationalError:
                pass  # column already exists
        # Migration: add epistemic column to items table (Session 104)
        try:
            self._db.execute("ALTER TABLE items ADD COLUMN confidence REAL")
            self._db.commit()
        except sqlite3.OperationalError:
            pass  # column already exists
        # Observation primitive: persistent gap log (Session 105)
        self._db.executescript(
            "CREATE TABLE IF NOT EXISTS observation_log ("
            "gap_id TEXT PRIMARY KEY, "
            "category TEXT NOT NULL, "
            "content_type TEXT NOT NULL, "
            "source TEXT NOT NULL, "
            "observed_at TEXT NOT NULL"
            ");"
        )
        # Coordination primitive: batch_id column on items + coordination log (Session 106)
        try:
            self._db.execute("ALTER TABLE items ADD COLUMN batch_id TEXT")
            self._db.commit()
        except sqlite3.OperationalError:
            pass  # column already exists
        self._db.executescript(
            "CREATE TABLE IF NOT EXISTS coordination_log ("
            "record_id TEXT PRIMARY KEY, "
            "batch_id TEXT NOT NULL, "
            "category TEXT NOT NULL, "
            "indices TEXT NOT NULL, "
            "observed_at TEXT NOT NULL"
            ");"
        )
        self._db.executescript(
            "CREATE TABLE IF NOT EXISTS ontology_log ("
            "record_id TEXT PRIMARY KEY, "
            "operation TEXT NOT NULL, "
            "category TEXT NOT NULL, "
            "singular INTEGER, "
            "reason TEXT, "
            "mutated_at TEXT NOT NULL"
            ");"
        )
        self._db.executescript(
            "CREATE TABLE IF NOT EXISTS repair_log ("
            "repair_id TEXT PRIMARY KEY, "
            "quarantine_id TEXT NOT NULL, "
            "category TEXT NOT NULL, "
            "status TEXT NOT NULL DEFAULT 'pending', "
            "pathway_chosen TEXT, "
            "notes TEXT, "
            "outcome TEXT, "
            "created_at TEXT NOT NULL, "
            "updated_at TEXT NOT NULL"
            ");"
        )
        self._db.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_conflicts(self, category: str, content_hash: str) -> list[str]:
        """Return item_ids of admitted (non-retracted) items in the same category
        with a *different* content hash — i.e., conflicting content."""
        cur = self._db.execute(
            """
            SELECT item_id FROM items
            WHERE category = ? AND content_hash != ? AND retracted = 0
            """,
            (category, content_hash),
        )
        return [row[0] for row in cur.fetchall()]

    def _fetch_item_content(self, item_id: str) -> tuple[Any, str] | None:
        """Return (content, source) for an admitted item, or None if not found."""
        row = self._db.execute(
            "SELECT content_json, source FROM items WHERE item_id = ?",
            (item_id,),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0]), row[1]

    def _build_repair_suggestion(
        self,
        quarantine_id: str,
        category: str,
        incoming_content: Any,
        incoming_source: str,
        conflict_ids: list[str],
        now: datetime,
    ) -> RepairSuggestion:
        """
        Build a RepairSuggestion for a singular-category conflict.
        Fetches both sides of the conflict and generates resolution pathways.
        Session 094 — ADR-016 C2.
        """
        existing_items = []
        for cid in conflict_ids:
            result = self._fetch_item_content(cid)
            if result:
                content, source = result
                existing_items.append({
                    "item_id": cid,
                    "content": content,
                    "source": source,
                })

        # Use first existing item for pathway action instructions
        primary_existing_id = conflict_ids[0] if conflict_ids else "unknown"

        return RepairSuggestion(
            quarantine_id=quarantine_id,
            category=category,
            rule_triggered=(
                f"singular-category constraint: category '{category}' allows at most one "
                f"active (non-retracted) entry. A new entry was proposed that conflicts with "
                f"{len(conflict_ids)} existing item(s)."
            ),
            incoming_content=incoming_content,
            incoming_source=incoming_source,
            existing_items=existing_items,
            resolution_pathways=_standard_resolution_pathways(category, primary_existing_id),
            generated_at=now,
        )

    def _serialise_repair(self, repair: RepairSuggestion) -> str:
        """Serialise RepairSuggestion to JSON for database storage."""
        return json.dumps({
            "quarantine_id": repair.quarantine_id,
            "category": repair.category,
            "rule_triggered": repair.rule_triggered,
            "incoming_content": repair.incoming_content,
            "incoming_source": repair.incoming_source,
            "existing_items": repair.existing_items,
            "resolution_pathways": [
                {
                    "pathway_id": p.pathway_id,
                    "description": p.description,
                    "action_required": p.action_required,
                }
                for p in repair.resolution_pathways
            ],
            "generated_at": repair.generated_at.isoformat(),
        }, default=str)

    def _emit(self, signal: SubstrateSignal) -> None:
        self._channel.emit(signal)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def propose(
        self,
        content: Any,
        category: str,
        source: str,
        *,
        temporal_context: datetime | None = None,
        expires_after_seconds: int | None = None,
        confidence: float | None = None,
    ) -> AdmissionResult:
        """
        Propose a knowledge item for admission.
        Fail-closed: any unexpected exception returns REJECTED (I1, A-list #1).

        expires_after_seconds: optional expiry contract (Session 103, Temporal).
        confidence: optional confidence declaration 0.0–1.0 (Session 104, Epistemic).
            None = untagged. Declared by proposer; not computed by substrate.
        """
        try:
            return self._propose_inner(content, category, source, temporal_context, expires_after_seconds, confidence)
        except Exception as exc:
            self._emit(SubstrateSignal(
                signal_type=SignalType.REJECTED,
                emitted_at=_now(),
                item_id=None,
                category=category,
                payload={"reason": f"internal error: {exc}", "source": source},
                source_operation="AdmissionGateway.propose",
            ))
            return AdmissionResult(
                verdict=AdmissionVerdict.REJECTED,
                item_id=None,
                provenance=None,
                reason=f"Governance checkpoint failed (internal error). Item not stored.",
                conflict_ids=[],
                repair=None,
            )

    def _propose_inner(
        self,
        content: Any,
        category: str,
        source: str,
        temporal_context: datetime | None,
        expires_after_seconds: int | None = None,
        confidence: float | None = None,
        batch_id: str | None = None,
    ) -> AdmissionResult:
        now = _now()

        # --- Step 0: Content validation (OQ-056) ---
        if content is None:
            self._emit(SubstrateSignal(
                signal_type=SignalType.REJECTED,
                emitted_at=now,
                item_id=None,
                category=category,
                payload={"reason": "content is None", "source": source},
                source_operation="AdmissionGateway.propose",
            ))
            return AdmissionResult(
                verdict=AdmissionVerdict.REJECTED,
                item_id=None,
                provenance=None,
                reason="Content validation failed: content must not be None.",
                conflict_ids=[],
                repair=None,
            )
        if isinstance(content, str) and not content.strip():
            self._emit(SubstrateSignal(
                signal_type=SignalType.REJECTED,
                emitted_at=now,
                item_id=None,
                category=category,
                payload={"reason": "content is empty or whitespace-only", "source": source},
                source_operation="AdmissionGateway.propose",
            ))
            return AdmissionResult(
                verdict=AdmissionVerdict.REJECTED,
                item_id=None,
                provenance=None,
                reason="Content validation failed: content must not be empty or whitespace-only.",
                conflict_ids=[],
                repair=None,
            )

        # --- Step 1: Category check (ObservationGap) ---
        if category not in self._known_categories:
            gap_signal = SubstrateSignal(
                signal_type=SignalType.OBSERVATION_GAP,
                emitted_at=now,
                item_id=None,
                category=category,
                payload={
                    "category": category,
                    "content_type": type(content).__name__,
                    "source": source,
                },
                source_operation="AdmissionGateway.propose",
            )
            self._emit(gap_signal)
            # Observation primitive (Session 105): persist gap record independently
            # of the channel. Gap survives drain(). WHY_OBSERVATION_EXISTS §8 Condition 2.
            gap_id = _new_id()
            with self._db:
                self._db.execute(
                    "INSERT INTO observation_log"
                    " (gap_id, category, content_type, source, observed_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (gap_id, category, type(content).__name__, source, now.isoformat()),
                )
            return AdmissionResult(
                verdict=AdmissionVerdict.REJECTED,
                item_id=None,
                provenance=None,
                reason=(
                    f"Unknown category '{category}'. Substrate has no representation "
                    f"for it. OBSERVATION_GAP signal emitted and gap persisted."
                ),
                conflict_ids=[],
                repair=None,
            )

        # --- Step 2: Contradiction check ---
        content_hash = _content_hash(content)
        if category not in self._singular_categories:
            conflict_ids = []
        else:
            conflict_ids = self._find_conflicts(category, content_hash)

        if conflict_ids:
            item_id = _new_id()
            quarantine_id = _new_id()
            content_json = json.dumps(content, default=str)

            # Build repair suggestion BEFORE the DB write (needs existing item content)
            repair = self._build_repair_suggestion(
                quarantine_id=quarantine_id,
                category=category,
                incoming_content=content,
                incoming_source=source,
                conflict_ids=conflict_ids,
                now=now,
            )
            repair_json = self._serialise_repair(repair)

            with self._db:  # atomic transaction
                self._db.execute(
                    """INSERT INTO quarantine
                       (quarantine_id, category, reason, quarantined_at, repair_json)
                       VALUES (?, ?, ?, ?, ?)""",
                    (quarantine_id, category,
                     "Conflicting content in same category (structural hash mismatch)",
                     now.isoformat(), repair_json),
                )
                # New (incoming) item
                self._db.execute(
                    """INSERT INTO quarantine_items (quarantine_id, item_id, content_json, source)
                       VALUES (?, ?, ?, ?)""",
                    (quarantine_id, item_id, content_json, source),
                )
                # Existing conflicting items
                for cid in conflict_ids:
                    row = self._db.execute(
                        "SELECT content_json, source FROM items WHERE item_id = ?", (cid,)
                    ).fetchone()
                    if row:
                        self._db.execute(
                            """INSERT INTO quarantine_items
                               (quarantine_id, item_id, content_json, source)
                               VALUES (?, ?, ?, ?)""",
                            (quarantine_id, cid, row[0], row[1]),
                        )

            # Persist RepairRecord to repair_log (Repair-as-Primitive — Session 108)
            with self._db:
                self._db.execute(
                    "INSERT INTO repair_log"
                    " (repair_id, quarantine_id, category, status, pathway_chosen,"
                    "  notes, outcome, created_at, updated_at)"
                    " VALUES (?, ?, ?, 'pending', NULL, NULL, NULL, ?, ?)",
                    (quarantine_id, quarantine_id, category,
                     now.isoformat(), now.isoformat()),
                )

            self._emit(SubstrateSignal(
                signal_type=SignalType.QUARANTINED,
                emitted_at=now,
                item_id=item_id,
                category=category,
                payload={
                    "quarantine_id": quarantine_id,
                    "conflict_ids": conflict_ids,
                    "source": source,
                    "repair_pathways": [p.pathway_id for p in repair.resolution_pathways],
                },
                source_operation="AdmissionGateway.propose",
            ))
            return AdmissionResult(
                verdict=AdmissionVerdict.QUARANTINED,
                item_id=item_id,
                provenance=None,
                reason=(
                    f"Conflicting content detected in category '{category}'. "
                    f"Both items preserved in quarantine. "
                    f"RepairSuggestion attached — {len(repair.resolution_pathways)} resolution pathways available."
                ),
                conflict_ids=conflict_ids,
                repair=repair,
            )

        # --- Step 3: Admit ---
        item_id = _new_id()
        content_json = json.dumps(content, default=str)
        basis = "No conflict detected; governance checkpoint passed."
        if temporal_context is not None:
            basis += f" Temporal context: {temporal_context.isoformat()}."

        provenance = ProvenanceRecord(
            item_id=item_id,
            source=source,
            admitted_at=now,
            basis=basis,
        )

        # Compute expired_at at admission time so it is queryable directly
        from datetime import timedelta as _td
        expired_at_iso = (
            (now + _td(seconds=expires_after_seconds)).isoformat()
            if expires_after_seconds is not None else None
        )
        with self._db:
            self._db.execute(
                """INSERT INTO items
                   (item_id, category, content_hash, content_json, source, admitted_at, basis,
                    expires_after_seconds, expired_at, confidence, batch_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, category, content_hash, content_json,
                 source, now.isoformat(), basis,
                 expires_after_seconds, expired_at_iso, confidence, batch_id),
            )

        self._emit(SubstrateSignal(
            signal_type=SignalType.ADMITTED,
            emitted_at=now,
            item_id=item_id,
            category=category,
            payload={"source": source, "basis": basis},
            source_operation="AdmissionGateway.propose",
        ))
        return AdmissionResult(
            verdict=AdmissionVerdict.ADMITTED,
            item_id=item_id,
            provenance=provenance,
            reason="Item admitted. Provenance record created.",
            conflict_ids=[],
            repair=None,
        )

    def retract(self, item_id: str, source: str, reason: str) -> AdmissionResult:
        """
        Retract a previously admitted item. Immutable audit trail — marks retracted,
        does not delete (I3, I7).
        """
        try:
            now = _now()
            row = self._db.execute(
                "SELECT item_id, retracted FROM items WHERE item_id = ?", (item_id,)
            ).fetchone()

            if row is None:
                return AdmissionResult(
                    verdict=AdmissionVerdict.REJECTED,
                    item_id=item_id,
                    provenance=None,
                    reason=f"Item '{item_id}' not found.",
                    conflict_ids=[],
                    repair=None,
                )
            if row[1]:
                return AdmissionResult(
                    verdict=AdmissionVerdict.REJECTED,
                    item_id=item_id,
                    provenance=None,
                    reason=f"Item '{item_id}' already retracted.",
                    conflict_ids=[],
                    repair=None,
                )

            with self._db:
                self._db.execute(
                    """UPDATE items SET retracted=1, retracted_at=?, retracted_by=?, retract_reason=?
                       WHERE item_id=?""",
                    (now.isoformat(), source, reason, item_id),
                )

            self._emit(SubstrateSignal(
                signal_type=SignalType.RETRACTED,
                emitted_at=now,
                item_id=item_id,
                category=None,
                payload={"source": source, "reason": reason},
                source_operation="AdmissionGateway.retract",
            ))
            return AdmissionResult(
                verdict=AdmissionVerdict.ADMITTED,
                item_id=item_id,
                provenance=None,
                reason="Retraction accepted. Item marked retracted (not deleted).",
                conflict_ids=[],
                repair=None,
            )
        except Exception as exc:
            return AdmissionResult(
                verdict=AdmissionVerdict.REJECTED,
                item_id=item_id,
                provenance=None,
                reason=f"Retraction failed (internal error): {exc}",
                conflict_ids=[],
                repair=None,
            )

    def list_admitted(self, category: str) -> list[AdmissionRecord]:
        """
        Return all currently admitted (non-retracted) items in a category.

        GAP-5 fix (Session 100, ADR-017). This is the public read API that previously
        required consumers to access self._substrate._db directly (a private attribute).
        Consumers must use this method; direct DB access is not part of the public API.

        Returns items ordered by admitted_at ascending.
        Returns an empty list if the category is unknown or has no admitted items.
        """
        rows = self._db.execute(
            """SELECT item_id, category, content_json, source, admitted_at,
                      expires_after_seconds, expired_at, confidence, batch_id
               FROM items
               WHERE category = ? AND retracted = 0
               ORDER BY admitted_at ASC""",
            (category,),
        ).fetchall()
        result = []
        for row in rows:
            import json as _json
            try:
                _content = _json.loads(row[2])
            except Exception:
                _content = row[2]
            result.append(AdmissionRecord(
                item_id=row[0],
                category=row[1],
                content=_content,
                source=row[3],
                admitted_at=row[4],
                expires_after_seconds=row[5],
                expired_at=row[6],
                confidence=row[7],
                batch_id=row[8],
            ))
        return result

    # ------------------------------------------------------------------
    # Temporal primitive (Session 103)
    # Conditions 3–7 from WHY_TEMPORAL_EXISTS.md §8 Executable Form.
    # ------------------------------------------------------------------

    def age_of(self, item_id: str) -> float:
        """
        Return the age of an admitted item in seconds since its admitted_at timestamp.

        WHY_TEMPORAL_EXISTS §8 Condition 3 — gw.age_of(item_id) -> float.

        Raises KeyError if item_id is not found in the items table.
        Does not check retracted status — age is a fact about admission, not currency.
        """
        row = self._db.execute(
            "SELECT admitted_at FROM items WHERE item_id = ?", (item_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"item_id not found: {item_id}")
        admitted_at = datetime.fromisoformat(row[0])
        return (_now() - admitted_at).total_seconds()

    def check_expired(self) -> list[AdmissionRecord]:
        """
        Find all non-retracted items whose expiry contract has elapsed.
        For each expired item:
          - Emit SignalType.TEMPORAL_ALERT on the ObservationChannel.
          - Produce a RepairSuggestion with pathways: RETRACT_AND_REPLACE, EXTEND, HOLD_AS_STALE.

        WHY_TEMPORAL_EXISTS §8 Conditions 4–7. Protected distinction (§9):
        TEMPORAL_ALERT signals describe item age, never truth or validity.
        Signal payloads use "item age exceeds declared contract" — never "expired claim".

        Returns the list of expired AdmissionRecords. Empty list if none.
        Does NOT retract any item — the substrate signals; the consumer decides.
        """
        now_iso = _now().isoformat()
        rows = self._db.execute(
            """SELECT item_id, category, content_json, source, admitted_at,
                      expires_after_seconds, expired_at, confidence, batch_id
               FROM items
               WHERE expires_after_seconds IS NOT NULL
                 AND retracted = 0
                 AND expired_at <= ?
               ORDER BY expired_at ASC""",
            (now_iso,),
        ).fetchall()

        import json as _json
        expired_records: list[AdmissionRecord] = []

        for row in rows:
            try:
                _content = _json.loads(row[2])
            except Exception:
                _content = row[2]

            record = AdmissionRecord(
                item_id=row[0],
                category=row[1],
                content=_content,
                source=row[3],
                admitted_at=row[4],
                expires_after_seconds=row[5],
                expired_at=row[6],
                confidence=row[7],
                batch_id=row[8],
            )
            expired_records.append(record)

            # Build RepairSuggestion for this expired item
            repair = RepairSuggestion(
                quarantine_id=_new_id(),  # temporal events share RepairSuggestion shape
                category=record.category,
                rule_triggered="Temporal expiry contract elapsed: item age exceeds declared contract",
                incoming_content=record.content,
                incoming_source=record.source,
                existing_items=[{
                    "item_id": record.item_id,
                    "content": record.content,
                    "source": record.source,
                    "admitted_at": record.admitted_at,
                    "expired_at": record.expired_at,
                }],
                resolution_pathways=[
                    ResolutionPathway(
                        pathway_id="RETRACT_AND_REPLACE",
                        description=(
                            "Retract this item and propose fresh content with a new "
                            "expiry contract. Use when the information is outdated and "
                            "a replacement is available."
                        ),
                        action_required=(
                            "Call gw.retract(item_id, source, reason) then "
                            "gw.propose(new_content, category, source, expires_after_seconds=N)."
                        ),
                    ),
                    ResolutionPathway(
                        pathway_id="EXTEND",
                        description=(
                            "Retract the current item and re-propose the same content "
                            "with a new expiry contract. Use when the information is still "
                            "believed to be correct but the time contract needs renewal."
                        ),
                        action_required=(
                            "Call gw.retract(item_id, source, reason) then "
                            "gw.propose(same_content, category, source, expires_after_seconds=N)."
                        ),
                    ),
                    ResolutionPathway(
                        pathway_id="HOLD_AS_STALE",
                        description=(
                            "Acknowledge the alert but take no action. The item remains "
                            "admitted. Use when expiry is a soft warning and the consumer "
                            "has decided to tolerate staleness explicitly."
                        ),
                        action_required=(
                            "No substrate action required. Record the decision to hold "
                            "in your consumer's audit trail."
                        ),
                    ),
                ],
                generated_at=_now(),
            )

            # Emit TEMPORAL_ALERT — §9 protected distinction: describe age, not truth
            self._emit(SubstrateSignal(
                signal_type=SignalType.TEMPORAL_ALERT,
                emitted_at=_now(),
                item_id=record.item_id,
                category=record.category,
                payload={
                    "message": "item age exceeds declared contract",
                    "expires_after_seconds": record.expires_after_seconds,
                    "expired_at": record.expired_at,
                    "admitted_at": record.admitted_at,
                    "source": record.source,
                    "repair_pathways": [p.pathway_id for p in repair.resolution_pathways],
                },
                source_operation="AdmissionGateway.check_expired",
            ))

        return expired_records

    # ------------------------------------------------------------------
    # Epistemic primitive (Session 104)
    # Conditions from WHY_EPISTEMIC_EXISTS.md §8 Executable Form.
    # ------------------------------------------------------------------

    def check_epistemic(
        self,
        category: str,
        threshold: float = 0.5,
    ) -> list[AdmissionRecord]:
        """
        Detect epistemic fragility in a category.

        WHY_EPISTEMIC_EXISTS §8 Conditions 3–7.

        Trigger: all tagged (confidence IS NOT NULL) non-retracted items in the
        category fall below `threshold`. If any tagged item meets or exceeds the
        threshold, returns empty list (sufficient epistemic cover).

        For each fragile category:
          - Emits SignalType.EPISTEMIC_ALERT on ObservationChannel.
          - Produces RepairSuggestion with pathways:
            RETRACT_AND_REPLACE, DOWNGRADE, REQUEST_EVIDENCE.

        Returns list of tagged below-threshold AdmissionRecords. Empty if not fragile.

        Untagged items (confidence=None) are excluded from fragility detection.
        They are not counted as low-confidence — their confidence is simply unknown.

        Protected distinction (§9): does NOT retract any item.
        Signal payload uses "declared confidence below threshold" — never
        "unreliable item" or "false claim".

        Design note (§3 B3, Session 104): all-below-threshold is the current
        trigger. Proportion-based detection (alert when ≥X% of tagged items are
        below threshold) is the identified forward direction. This is logged as
        an open design question.
        """
        rows = self._db.execute(
            """SELECT item_id, category, content_json, source, admitted_at,
                      expires_after_seconds, expired_at, confidence, batch_id
               FROM items
               WHERE category = ?
                 AND retracted = 0
                 AND confidence IS NOT NULL
               ORDER BY admitted_at ASC""",
            (category,),
        ).fetchall()

        if not rows:
            # No tagged items — fragility is undetectable, not fragile
            return []

        import json as _json

        tagged_records: list[AdmissionRecord] = []
        for row in rows:
            try:
                _content = _json.loads(row[2])
            except Exception:
                _content = row[2]
            tagged_records.append(AdmissionRecord(
                item_id=row[0],
                category=row[1],
                content=_content,
                source=row[3],
                admitted_at=row[4],
                expires_after_seconds=row[5],
                expired_at=row[6],
                confidence=row[7],
                batch_id=row[8],
            ))

        # Fragility check: all-below-threshold trigger
        below_threshold = [r for r in tagged_records if r.confidence < threshold]
        if len(below_threshold) < len(tagged_records):
            # At least one item meets or exceeds threshold — no alert
            return []

        # All tagged items are below threshold — category is epistemically fragile
        repair = RepairSuggestion(
            quarantine_id=_new_id(),
            category=category,
            rule_triggered=(
                f"Epistemic fragility: all tagged items in category fall below "
                f"declared confidence threshold ({threshold})"
            ),
            incoming_content=None,
            incoming_source="AdmissionGateway.check_epistemic",
            existing_items=[
                {
                    "item_id": r.item_id,
                    "content": r.content,
                    "source": r.source,
                    "admitted_at": r.admitted_at,
                    "confidence": r.confidence,
                }
                for r in below_threshold
            ],
            resolution_pathways=[
                ResolutionPathway(
                    pathway_id="RETRACT_AND_REPLACE",
                    description=(
                        "Retract the low-confidence item and propose new content with "
                        "higher declared confidence. Use when stronger evidence is available."
                    ),
                    action_required=(
                        "Call gw.retract(item_id, source, reason) then "
                        "gw.propose(new_content, category, source, confidence=N)."
                    ),
                ),
                ResolutionPathway(
                    pathway_id="DOWNGRADE",
                    description=(
                        "Retract the item and re-propose the same content with an explicit "
                        "low-confidence tag and updated source note. Use when the proposer "
                        "wants the item visible but its epistemic status made explicit."
                    ),
                    action_required=(
                        "Call gw.retract(item_id, source, reason) then "
                        "gw.propose(same_content, category, source, confidence=<explicit_low>)."
                    ),
                ),
                ResolutionPathway(
                    pathway_id="REQUEST_EVIDENCE",
                    description=(
                        "Take no substrate action. Hold the item pending higher-confidence "
                        "information. Use when stronger evidence is expected to arrive."
                    ),
                    action_required=(
                        "No substrate action required. Record the decision to hold in "
                        "your consumer's audit trail."
                    ),
                ),
            ],
            generated_at=_now(),
        )

        # Emit EPISTEMIC_ALERT — §9 protected distinction: declared confidence, not truth
        self._emit(SubstrateSignal(
            signal_type=SignalType.EPISTEMIC_ALERT,
            emitted_at=_now(),
            item_id=None,
            category=category,
            payload={
                "message": "declared confidence below threshold",
                "threshold": threshold,
                "fragile_item_count": len(below_threshold),
                "fragile_items": [
                    {"item_id": r.item_id, "confidence": r.confidence}
                    for r in below_threshold
                ],
                "repair_pathways": [p.pathway_id for p in repair.resolution_pathways],
            },
            source_operation="AdmissionGateway.check_epistemic",
        ))

        return below_threshold

    # ------------------------------------------------------------------
    # Observation primitive (Session 105)
    # Conditions from WHY_OBSERVATION_EXISTS.md §8 Executable Form.
    # ------------------------------------------------------------------

    def list_gaps(self, category: str | None = None) -> list[GapRecord]:
        """
        Return all persisted gap records from ObservationLog.
        WHY_OBSERVATION_EXISTS §8 Conditions 3–4.

        Gap records persist independently of ObservationChannel.drain().
        Draining the signal bus does not remove gap records.

        Args:
            category: if provided, filter to gaps for this specific unknown category.
                      If None, return all gap records.

        Returns gap records ordered by observed_at ascending.
        Returns empty list if no gaps have been observed.

        Protected distinction: gap records describe perceptual limits —
        never the validity or importance of what was proposed.
        """
        if category is None:
            rows = self._db.execute(
                "SELECT gap_id, category, content_type, source, observed_at"
                " FROM observation_log"
                " ORDER BY observed_at ASC",
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT gap_id, category, content_type, source, observed_at"
                " FROM observation_log"
                " WHERE category = ?"
                " ORDER BY observed_at ASC",
                (category,),
            ).fetchall()

        return [
            GapRecord(
                gap_id=row[0],
                category=row[1],
                content_type=row[2],
                source=row[3],
                observed_at=row[4],
            )
            for row in rows
        ]

    def gap_count(self, category: str) -> int:
        """
        Return how many times an unknown category has been encountered.
        WHY_OBSERVATION_EXISTS §8 Condition 5.

        Returns 0 if the category has never been encountered as a gap.
        This is the key signal for deciding whether to expand known_categories.
        """
        row = self._db.execute(
            "SELECT COUNT(*) FROM observation_log WHERE category = ?",
            (category,),
        ).fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------
    # Coordination primitive (Session 106)
    # Conditions from WHY_COORDINATION_EXISTS.md §8 Executable Form.
    # ------------------------------------------------------------------

    def propose_batch(self, proposals: list) -> "BatchResult":
        """
        Submit multiple proposals as a named admission batch.
        WHY_COORDINATION_EXISTS.md §8 Conditions 3–8.

        Governance semantics:
        1. Pre-flight: check all proposals against each other for
           singular-category conflicts (intra-batch conflict detection).
        2. For each conflicting pair (i, j), emit COORDINATION_CONFLICT
           signal and persist a CoordinationRecord to CoordinationLog.
        3. Process all proposals in index order via _propose_inner().
        4. Return BatchResult with one AdmissionResult per proposal.

        Design decisions (WHY_COORDINATION_EXISTS §10):
        - Signal-and-continue: batch is not atomic. Each proposal is
          admitted or quarantined independently. Batch coherence is NOT
          guaranteed in v1.
        - Persist only on conflict: clean batches leave no CoordinationLog entry.
        - batch_id lineage: every admitted item from this batch carries
          batch_id so coordination relationships remain queryable.

        Protected distinction: admission order (index position) ≠ cognitive
        priority. Proposal 0 was processed first as a coordination artifact,
        not because it is more valid than proposal 2.

        Args:
            proposals: list of BatchProposal objects

        Returns:
            BatchResult with batch_id, per-proposal results, and any
            coordination_conflicts detected.
        """
        now = _now()
        batch_id = _new_id()
        coordination_conflicts = []

        # --- Pre-flight: intra-batch conflict detection ---
        # Only applies to singular categories.
        # Check all pairs (i < j) where both target the same singular category.
        import json as _json

        for i in range(len(proposals)):
            for j in range(i + 1, len(proposals)):
                pi = proposals[i]
                pj = proposals[j]
                if pi.category != pj.category:
                    continue
                if pi.category not in self._singular_categories:
                    continue
                # Same singular category — potential conflict
                # Conflict if content is distinct (same content = duplicate, not conflict)
                ci = _json.dumps(pi.content, default=str, sort_keys=True)
                cj = _json.dumps(pj.content, default=str, sort_keys=True)
                if ci == cj:
                    continue  # Duplicate, not conflict
                # Conflict detected
                conflict = {"indices": [i, j], "category": pi.category}
                coordination_conflicts.append(conflict)

                # Emit COORDINATION_CONFLICT signal
                self._emit(SubstrateSignal(
                    signal_type=SignalType.COORDINATION_CONFLICT,
                    emitted_at=now,
                    item_id=None,
                    category=pi.category,
                    payload={
                        "batch_id": batch_id,
                        "conflicting_indices": [i, j],
                        "category": pi.category,
                        "source_i": pi.source,
                        "source_j": pj.source,
                    },
                    source_operation="AdmissionGateway.propose_batch",
                ))

                # Persist CoordinationRecord (conflict-only persistence — §7)
                record_id = _new_id()
                with self._db:
                    self._db.execute(
                        "INSERT INTO coordination_log"
                        " (record_id, batch_id, category, indices, observed_at)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (record_id, batch_id, pi.category,
                         _json.dumps([i, j]), now.isoformat()),
                    )

        # --- Admit proposals in index order ---
        results = []
        for proposal in proposals:
            result = self._propose_inner(
                content=proposal.content,
                category=proposal.category,
                source=proposal.source,
                temporal_context=None,
                expires_after_seconds=proposal.expires_after_seconds,
                confidence=proposal.confidence,
                batch_id=batch_id,
            )
            results.append(result)

        return BatchResult(
            batch_id=batch_id,
            results=results,
            coordination_conflicts=coordination_conflicts,
        )

    def list_coordination_conflicts(self, category: str | None = None) -> list:
        """
        Return persisted CoordinationRecord objects from CoordinationLog.
        WHY_COORDINATION_EXISTS.md §8 Condition 7.

        Only records where COORDINATION_CONFLICT fired are present.
        Clean batches leave no entry (conflict-only persistence — §7).

        Args:
            category: if provided, filter to conflicts in this singular category.
                      If None, return all coordination conflict records.

        Returns records ordered by observed_at ascending.
        """
        import json as _json
        if category is None:
            rows = self._db.execute(
                "SELECT record_id, batch_id, category, indices, observed_at"
                " FROM coordination_log"
                " ORDER BY observed_at ASC",
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT record_id, batch_id, category, indices, observed_at"
                " FROM coordination_log"
                " WHERE category = ?"
                " ORDER BY observed_at ASC",
                (category,),
            ).fetchall()

        return [
            CoordinationRecord(
                record_id=row[0],
                batch_id=row[1],
                category=row[2],
                indices=row[3],
                observed_at=row[4],
            )
            for row in rows
        ]


    # ------------------------------------------------------------------
    # Ontology primitive (Session 107 — WHY_ONTOLOGY_EXISTS.md)
    # ------------------------------------------------------------------

    def add_category(
        self,
        category: str,
        singular: bool = False,
        reason: "str | None" = None,
    ) -> "OntologyRecord | None":
        """
        Add a category to the substrate's known vocabulary.
        WHY_ONTOLOGY_EXISTS.md §3, §9.

        If the category already exists this is a no-op and returns None.
        No duplicate OntologyRecord is written; no signal is emitted.

        On success:
        - Adds category to self._known_categories (live effect — immediate)
        - If singular=True, adds to self._singular_categories
        - Emits ONTOLOGY_MUTATION signal
        - Persists OntologyRecord in ontology_log

        Protected distinction: adding a category does not validate or endorse
        the content that will be admitted under it. Category existence !=
        category validity (WHY_ONTOLOGY_EXISTS.md §2).

        Args:
            category: the category name to add
            singular: if True, this category enforces at-most-one admission
                      (triggers COORDINATION_CONFLICT on intra-batch conflict
                      and QUARANTINE on duplicate admission attempt).
                      Default False (plural — multiple items coexist freely).
            reason:   optional provenance string answering "why was this added?"
                      Stored in OntologyRecord for future auditability.

        Returns:
            OntologyRecord on success, None if category already existed.
        """
        if category in self._known_categories:
            return None

        now = _now()
        record_id = _new_id()

        # Live effect — immediate: subsequent proposals see the new category
        self._known_categories.add(category)
        if singular:
            self._singular_categories.add(category)

        # Persist record
        with self._db:
            self._db.execute(
                "INSERT INTO ontology_log"
                " (record_id, operation, category, singular, reason, mutated_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record_id,
                    "add",
                    category,
                    1 if singular else 0,
                    reason,
                    now.isoformat(),
                ),
            )

        record = OntologyRecord(
            record_id=record_id,
            operation="add",
            category=category,
            singular=singular,
            reason=reason,
            mutated_at=now.isoformat(),
        )

        # Emit signal
        self._emit(SubstrateSignal(
            signal_type=SignalType.ONTOLOGY_MUTATION,
            emitted_at=now,
            item_id=None,
            category=category,
            payload={
                "operation": "add",
                "category": category,
                "singular": singular,
                "reason": reason,
            },
            source_operation="AdmissionGateway.add_category",
        ))

        return record

    def remove_category(
        self,
        category: str,
        reason: "str | None" = None,
    ) -> "OntologyRecord | None":
        """
        Remove a category from the substrate's known vocabulary.
        WHY_ONTOLOGY_EXISTS.md §3, §9.

        If the category does not exist this is a no-op and returns None.

        On success:
        - Removes category from self._known_categories (live effect — immediate)
        - Removes from self._singular_categories if present
        - Emits ONTOLOGY_MUTATION signal
        - Persists OntologyRecord in ontology_log

        IMPORTANT: existing admitted items are NOT deleted. They remain in the
        admission log under the now-retired category name. Future proposals to
        this category will trigger OBSERVATION_GAP (WHY_ONTOLOGY_EXISTS.md §7 F3).

        Args:
            category: the category name to remove
            reason:   optional provenance string

        Returns:
            OntologyRecord on success, None if category did not exist.
        """
        if category not in self._known_categories:
            return None

        # GAP-6 fix (Option B — S111, ADR-018, INSIGHT-135).
        # Query for in-flight repairs BEFORE removing the category.
        # "In-flight" = any repair not yet VERIFIED (i.e. not yet closed).
        # We query now so we have the data for signal emission after removal.
        _in_flight_statuses = ("pending", "acknowledged", "executed")
        _placeholders = ",".join("?" * len(_in_flight_statuses))
        _in_flight_repairs = self._db.execute(
            f"SELECT repair_id, status FROM repair_log"
            f" WHERE category = ? AND status IN ({_placeholders})",
            (category, *_in_flight_statuses),
        ).fetchall()

        now = _now()
        record_id = _new_id()

        # Live effect — immediate
        self._known_categories.discard(category)
        self._singular_categories.discard(category)

        # Persist record (singular=None for remove — property no longer applies)
        with self._db:
            self._db.execute(
                "INSERT INTO ontology_log"
                " (record_id, operation, category, singular, reason, mutated_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record_id,
                    "remove",
                    category,
                    None,
                    reason,
                    now.isoformat(),
                ),
            )

        record = OntologyRecord(
            record_id=record_id,
            operation="remove",
            category=category,
            singular=None,
            reason=reason,
            mutated_at=now.isoformat(),
        )

        # Emit ONTOLOGY_MUTATION signal (category removed)
        self._emit(SubstrateSignal(
            signal_type=SignalType.ONTOLOGY_MUTATION,
            emitted_at=now,
            item_id=None,
            category=category,
            payload={
                "operation": "remove",
                "category": category,
                "singular": None,
                "reason": reason,
            },
            source_operation="AdmissionGateway.remove_category",
        ))

        # GAP-6 fix (Option B — S111, ADR-018, INSIGHT-135).
        # Emit REPAIR_ONTOLOGY_CONFLICT for each in-flight repair whose category
        # was just removed. Signal-and-continue: repairs are NOT blocked.
        # I8 (Contradiction Visibility): the ambiguity is a visible event.
        # I10 (Architectural Honesty): we surface what we know, not a forced resolution.
        # Open-world semantics: "removal in progress" ≠ "category never existed".
        for _repair_id, _repair_status in _in_flight_repairs:
            self._emit(SubstrateSignal(
                signal_type=SignalType.REPAIR_ONTOLOGY_CONFLICT,
                emitted_at=now,
                item_id=None,
                category=category,
                payload={
                    "conflict_type": "ontology_removed_during_active_repair",
                    "repair_id": _repair_id,
                    "repair_status": _repair_status,
                    "category": category,
                    "removal_reason": reason,
                    "note": (
                        "Category was removed while a repair referencing it was "
                        "in-flight. The repair lifecycle may continue but its "
                        "ontological context no longer exists in the substrate. "
                        "Open-world: the repair is not blocked; the conflict is "
                        "surfaced for governance. See ADR-018, INSIGHT-135."
                    ),
                },
                source_operation="AdmissionGateway.remove_category",
            ))

        return record

    def list_ontology_mutations(
        self,
        operation: "str | None" = None,
    ) -> "list[OntologyRecord]":
        """
        Return persisted OntologyRecord objects from OntologyLog.
        WHY_ONTOLOGY_EXISTS.md §6.

        All governed category mutations are recorded here — both additions
        and removals. Drain() does not clear this log.

        Args:
            operation: if "add" or "remove", filter to that operation type.
                       If None, return all mutations ordered by mutated_at ASC.

        Returns:
            list of OntologyRecord, ordered by mutated_at ascending.
        """
        if operation is not None:
            rows = self._db.execute(
                "SELECT record_id, operation, category, singular, reason, mutated_at"
                " FROM ontology_log"
                " WHERE operation = ?"
                " ORDER BY mutated_at ASC",
                (operation,),
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT record_id, operation, category, singular, reason, mutated_at"
                " FROM ontology_log"
                " ORDER BY mutated_at ASC",
            ).fetchall()

        return [
            OntologyRecord(
                record_id=row[0],
                operation=row[1],
                category=row[2],
                singular=bool(row[3]) if row[3] is not None else None,
                reason=row[4],
                mutated_at=row[5],
            )
            for row in rows
        ]


    # ------------------------------------------------------------------
    # Repair-as-Primitive (Session 108 — WHY_REPAIR_AS_PRIMITIVE_EXISTS.md)
    # ------------------------------------------------------------------

    def acknowledge_repair(self, repair_id: str) -> "RepairRecord":
        """
        Transition a RepairRecord from PENDING to ACKNOWLEDGED.
        WHY_REPAIR_AS_PRIMITIVE_EXISTS.md §3, §8.

        Declares: "This repair suggestion has been read and is being handled."
        Does NOT mean the repair has been carried out — use execute_repair() for that.

        Protected distinction: seeing a repair suggestion ≠ executing one.

        Args:
            repair_id: the repair_id from the RepairRecord (same as quarantine_id)

        Returns:
            Updated RepairRecord with status="acknowledged"

        Raises:
            ValueError: if repair_id not found or transition not valid (not PENDING)
        """
        now = _now()
        row = self._db.execute(
            "SELECT repair_id, quarantine_id, category, status, pathway_chosen,"
            " notes, outcome, created_at, updated_at"
            " FROM repair_log WHERE repair_id = ?",
            (repair_id,),
        ).fetchone()

        if row is None:
            raise ValueError(f"repair_id '{repair_id}' not found in repair_log.")
        if row[3] != "pending":
            raise ValueError(
                f"Cannot acknowledge repair '{repair_id}': "
                f"current status is '{row[3]}', expected 'pending'."
            )

        with self._db:
            self._db.execute(
                "UPDATE repair_log SET status = 'acknowledged', updated_at = ?"
                " WHERE repair_id = ?",
                (now.isoformat(), repair_id),
            )

        record = RepairRecord(
            repair_id=row[0], quarantine_id=row[1], category=row[2],
            status="acknowledged", pathway_chosen=row[4],
            notes=row[5], outcome=row[6],
            created_at=row[7], updated_at=now.isoformat(),
        )

        self._emit(SubstrateSignal(
            signal_type=SignalType.REPAIR_LIFECYCLE,
            emitted_at=now,
            item_id=None,
            category=row[2],
            payload={
                "repair_id": repair_id,
                "from_status": "pending",
                "to_status": "acknowledged",
                "category": row[2],
                "notes": None,
            },
            source_operation="AdmissionGateway.acknowledge_repair",
        ))
        return record

    def execute_repair(
        self,
        repair_id: str,
        pathway_chosen: "str | None" = None,
        notes: "str | None" = None,
    ) -> "RepairRecord":
        """
        Transition a RepairRecord from ACKNOWLEDGED to EXECUTED.
        WHY_REPAIR_AS_PRIMITIVE_EXISTS.md §3, §4, §8.

        Declares: "The repair action has been carried out."
        In v1, this is a declaration — the substrate records the claim but does
        not verify or automate the repair. The caller is responsible for having
        actually performed the repair before calling this method.

        I1 (Governance Before Autonomy): the substrate governs; it does not act.

        Args:
            repair_id:       the repair to transition
            pathway_chosen:  pathway_id from ResolutionPathway (e.g. "RETRACT_AND_REPLACE")
            notes:           optional caller description of what was done

        Returns:
            Updated RepairRecord with status="executed"

        Raises:
            ValueError: if repair_id not found or not in ACKNOWLEDGED state
        """
        now = _now()
        row = self._db.execute(
            "SELECT repair_id, quarantine_id, category, status, pathway_chosen,"
            " notes, outcome, created_at, updated_at"
            " FROM repair_log WHERE repair_id = ?",
            (repair_id,),
        ).fetchone()

        if row is None:
            raise ValueError(f"repair_id '{repair_id}' not found in repair_log.")
        if row[3] != "acknowledged":
            raise ValueError(
                f"Cannot execute repair '{repair_id}': "
                f"current status is '{row[3]}', expected 'acknowledged'."
            )

        with self._db:
            self._db.execute(
                "UPDATE repair_log"
                " SET status = 'executed', pathway_chosen = ?, notes = ?, updated_at = ?"
                " WHERE repair_id = ?",
                (pathway_chosen, notes, now.isoformat(), repair_id),
            )

        record = RepairRecord(
            repair_id=row[0], quarantine_id=row[1], category=row[2],
            status="executed", pathway_chosen=pathway_chosen,
            notes=notes, outcome=row[6],
            created_at=row[7], updated_at=now.isoformat(),
        )

        self._emit(SubstrateSignal(
            signal_type=SignalType.REPAIR_LIFECYCLE,
            emitted_at=now,
            item_id=None,
            category=row[2],
            payload={
                "repair_id": repair_id,
                "from_status": "acknowledged",
                "to_status": "executed",
                "category": row[2],
                "pathway_chosen": pathway_chosen,
                "notes": notes,
            },
            source_operation="AdmissionGateway.execute_repair",
        ))
        return record

    def verify_repair(
        self,
        repair_id: str,
        outcome: "str | None" = None,
    ) -> "RepairRecord":
        """
        Transition a RepairRecord from EXECUTED to VERIFIED.
        WHY_REPAIR_AS_PRIMITIVE_EXISTS.md §3, §4, §8.

        Declares: "The repair outcome has been confirmed."
        This is the terminal state. Closes the governance loop.

        In v1, verification is a declaration. The substrate records the outcome
        claim without independently validating it. The audit trail is now complete:
        suggestion → acknowledgement → execution → verification.

        Args:
            repair_id:  the repair to close
            outcome:    optional description of the verified outcome

        Returns:
            Updated RepairRecord with status="verified"

        Raises:
            ValueError: if repair_id not found or not in EXECUTED state
        """
        now = _now()
        row = self._db.execute(
            "SELECT repair_id, quarantine_id, category, status, pathway_chosen,"
            " notes, outcome, created_at, updated_at"
            " FROM repair_log WHERE repair_id = ?",
            (repair_id,),
        ).fetchone()

        if row is None:
            raise ValueError(f"repair_id '{repair_id}' not found in repair_log.")
        if row[3] != "executed":
            raise ValueError(
                f"Cannot verify repair '{repair_id}': "
                f"current status is '{row[3]}', expected 'executed'."
            )

        with self._db:
            self._db.execute(
                "UPDATE repair_log"
                " SET status = 'verified', outcome = ?, updated_at = ?"
                " WHERE repair_id = ?",
                (outcome, now.isoformat(), repair_id),
            )

        record = RepairRecord(
            repair_id=row[0], quarantine_id=row[1], category=row[2],
            status="verified", pathway_chosen=row[4],
            notes=row[5], outcome=outcome,
            created_at=row[7], updated_at=now.isoformat(),
        )

        self._emit(SubstrateSignal(
            signal_type=SignalType.REPAIR_LIFECYCLE,
            emitted_at=now,
            item_id=None,
            category=row[2],
            payload={
                "repair_id": repair_id,
                "from_status": "executed",
                "to_status": "verified",
                "category": row[2],
                "outcome": outcome,
            },
            source_operation="AdmissionGateway.verify_repair",
        ))
        return record

    def list_repairs(
        self,
        status: "str | None" = None,
    ) -> "list[RepairRecord]":
        """
        Return persisted RepairRecord objects from RepairLog.
        WHY_REPAIR_AS_PRIMITIVE_EXISTS.md §6, §8.

        Every RepairRecord persisted here began as a RepairSuggestion generated
        on a QUARANTINE event. The log survives drain().

        Args:
            status: filter by lifecycle state ("pending", "acknowledged",
                    "executed", "verified"). If None, return all records.

        Returns:
            list of RepairRecord ordered by created_at ascending.
        """
        if status is not None:
            rows = self._db.execute(
                "SELECT repair_id, quarantine_id, category, status, pathway_chosen,"
                " notes, outcome, created_at, updated_at"
                " FROM repair_log WHERE status = ?"
                " ORDER BY created_at ASC",
                (status,),
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT repair_id, quarantine_id, category, status, pathway_chosen,"
                " notes, outcome, created_at, updated_at"
                " FROM repair_log ORDER BY created_at ASC",
            ).fetchall()

        return [
            RepairRecord(
                repair_id=row[0],
                quarantine_id=row[1],
                category=row[2],
                status=row[3],
                pathway_chosen=row[4],
                notes=row[5],
                outcome=row[6],
                created_at=row[7],
                updated_at=row[8],
            )
            for row in rows
        ]
