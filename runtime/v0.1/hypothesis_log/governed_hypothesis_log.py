"""
governed_hypothesis_log.py — Consumer #5
GovernedHypothesisLog: hypothesis tracking system built on the RITAM substrate.
Built from EXTERNAL_REPRODUCTION_PACKET_V1.md — no internal substrate knowledge used.
"""
from ritam.runtime.v01 import (
    Substrate, SubstrateConfig, AdmissionVerdict, AdmissionRecord,
)
from ritam.runtime.v01.types import AdmissionResult

CATEGORIES = ["working-hypothesis", "supporting-evidence", "counter-evidence"]
SINGULAR   = ["working-hypothesis"]


class GovernedHypothesisLog:
    def __init__(self, storage_path: str) -> None:
        substrate = Substrate(SubstrateConfig(
            storage_path=storage_path,
            known_categories=CATEGORIES,
            singular_categories=SINGULAR,
        ))
        self._gw = substrate.admission_gateway()
        self._cs = substrate.contradiction_store()

    def propose_hypothesis(self, hypothesis: str, source: str) -> AdmissionResult:
        return self._gw.propose(hypothesis, "working-hypothesis", source)

    def add_evidence(self, evidence: str, source: str) -> AdmissionResult:
        return self._gw.propose(evidence, "supporting-evidence", source)

    def add_counter_evidence(self, evidence: str, source: str) -> AdmissionResult:
        return self._gw.propose(evidence, "counter-evidence", source)

    def current_hypothesis(self) -> str | None:
        records = self._gw.list_admitted("working-hypothesis")
        if not records:
            return None
        return records[-1].content

    def all_evidence(self) -> list[str]:
        return [r.content for r in self._gw.list_admitted("supporting-evidence")]

    def all_counter_evidence(self) -> list[str]:
        return [r.content for r in self._gw.list_admitted("counter-evidence")]

    def open_contradictions(self) -> int:
        return self._cs.count()

    def retract_hypothesis(self, item_id: str, source: str, reason: str) -> AdmissionResult:
        return self._gw.retract(item_id, source, reason)
