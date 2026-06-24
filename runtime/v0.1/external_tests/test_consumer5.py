"""test_consumer5.py — External Reproduction Packet v1.0 Verification Harness"""
import tempfile
from governed_hypothesis_log import GovernedHypothesisLog
from ritam.runtime.v01 import AdmissionVerdict


def test_first_hypothesis_admitted():
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedHypothesisLog(tmp)
        result = log.propose_hypothesis("Dark matter is composed of WIMPs.", "physicist-A")
        assert result.verdict == AdmissionVerdict.ADMITTED


def test_second_hypothesis_quarantined():
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedHypothesisLog(tmp)
        log.propose_hypothesis("Dark matter is composed of WIMPs.", "physicist-A")
        result = log.propose_hypothesis("Dark matter is composed of axions.", "physicist-B")
        assert result.verdict == AdmissionVerdict.QUARANTINED


def test_repair_suggestion_on_conflict():
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedHypothesisLog(tmp)
        log.propose_hypothesis("WIMPs hypothesis.", "physicist-A")
        result = log.propose_hypothesis("Axions hypothesis.", "physicist-B")
        assert result.verdict == AdmissionVerdict.QUARANTINED
        assert result.repair is not None
        pathway_ids = {p.pathway_id for p in result.repair.resolution_pathways}
        assert "RETRACT_EXISTING" in pathway_ids
        assert "KEEP_EXISTING" in pathway_ids
        assert "HOLD_AS_CONTRADICTION" in pathway_ids


def test_current_hypothesis_readable():
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedHypothesisLog(tmp)
        log.propose_hypothesis("WIMPs are the answer.", "physicist-A")
        assert log.current_hypothesis() == "WIMPs are the answer."


def test_current_hypothesis_none_when_empty():
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedHypothesisLog(tmp)
        assert log.current_hypothesis() is None


def test_evidence_accumulates_freely():
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedHypothesisLog(tmp)
        r1 = log.add_evidence("Galaxy rotation curves support WIMPs.", "observation-A")
        r2 = log.add_evidence("Bullet cluster data consistent with WIMPs.", "observation-B")
        r3 = log.add_evidence("CMB power spectrum fitting.", "observation-C")
        assert r1.verdict == AdmissionVerdict.ADMITTED
        assert r2.verdict == AdmissionVerdict.ADMITTED
        assert r3.verdict == AdmissionVerdict.ADMITTED
        assert log.open_contradictions() == 0


def test_counter_evidence_accumulates_freely():
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedHypothesisLog(tmp)
        r1 = log.add_counter_evidence("LHC found no WIMP candidates.", "experiment-A")
        r2 = log.add_counter_evidence("Direct detection experiments null result.", "experiment-B")
        assert r1.verdict == AdmissionVerdict.ADMITTED
        assert r2.verdict == AdmissionVerdict.ADMITTED


def test_all_evidence_returns_content():
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedHypothesisLog(tmp)
        log.add_evidence("Evidence A.", "src")
        log.add_evidence("Evidence B.", "src")
        evidence = log.all_evidence()
        assert len(evidence) == 2
        assert "Evidence A." in evidence
        assert "Evidence B." in evidence


def test_all_counter_evidence_returns_content():
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedHypothesisLog(tmp)
        log.add_counter_evidence("Counter A.", "src")
        counter = log.all_counter_evidence()
        assert len(counter) == 1
        assert "Counter A." in counter


def test_open_contradictions_count():
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedHypothesisLog(tmp)
        assert log.open_contradictions() == 0
        log.propose_hypothesis("Hypothesis 1.", "src-A")
        log.propose_hypothesis("Hypothesis 2.", "src-B")
        assert log.open_contradictions() == 1


def test_retract_and_replace_hypothesis():
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedHypothesisLog(tmp)
        r1 = log.propose_hypothesis("Old hypothesis.", "physicist-A")
        assert r1.verdict == AdmissionVerdict.ADMITTED
        r2 = log.propose_hypothesis("New hypothesis.", "physicist-B")
        assert r2.verdict == AdmissionVerdict.QUARANTINED
        retract_result = log.retract_hypothesis(r1.item_id, source="board", reason="Paradigm shift")
        assert retract_result.verdict == AdmissionVerdict.ADMITTED
        r3 = log.propose_hypothesis("New hypothesis.", "physicist-B")
        assert r3.verdict == AdmissionVerdict.ADMITTED


def test_no_private_db_access():
    with tempfile.TemporaryDirectory() as tmp:
        log = GovernedHypothesisLog(tmp)
        log.propose_hypothesis("Test hypothesis.", "tester")
        log.add_evidence("Some evidence.", "tester")
        log.add_counter_evidence("Some counter.", "tester")
        assert log.current_hypothesis() == "Test hypothesis."
        assert len(log.all_evidence()) == 1
        assert len(log.all_counter_evidence()) == 1
        assert log.open_contradictions() == 0
