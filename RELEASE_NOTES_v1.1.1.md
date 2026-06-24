# RITAM v1.1.1 — Initial Public Release

**Released:** 2026-06-24  
**Repository:** https://github.com/LivingFramework/ritam-core

---

## What Is This

RITAM is a governed cognition substrate — a runtime layer that sits beneath an AI application and holds its cognitive state under explicit governance.

This is the first public release. It represents 115 research sessions and a complete implementation of nine substrate primitives, validated across adversarial, integration, and cross-builder scenarios.

---

## What Is Included

**Runtime (v0.1)**
- Nine substrate primitives fully implemented: State, Memory, Ontology, Governance, Epistemic, Coordination, Temporal, Observation, Repair
- 146 tests across 22 test files: adversarial, integration, buildability, outcome, and repair scenarios
- Three consumer examples: GovernedNotebook, GovernedDecisionLog, GovernedAgentMemory
- `pip install -e runtime/v0.1` — installs as `ritam` package

**Architecture documentation**
- Technical Overview — what has been demonstrated, what remains unknown (evidence-separated)
- Foundations of RITAM — the worldview: why governance must precede persistence
- Why RITAM Might Be Wrong — strongest objections and open falsification targets
- WHY_ derivation docs for all nine primitives — failure argument for each
- V1.0 Declaration — the three criteria used to declare v1.0 and the evidence that satisfied them
- Six Architecture Decision Records (ADR-001, 002, 006, 014, 018, 019)

**Evidence**
- External reproduction results (Session 102): five independent AI systems, 60/60 tests — Tier D (transfer-validated)
- V1 Evidence Ledger: permanent record of why v1.0 was declared

---

## Key Findings

- Governance changes outcomes: a governed substrate produces measurably different results from an ungoverned baseline
- All nine primitives are load-bearing: removing any one causes observable failure in adversarial testing
- The specification is transferable: five independent AI systems reproduced the runtime from the spec alone
- GAP-6 (ontology mutation during active repair) was identified by adversarial audit and closed in the same session

---

## What This Is Not

- Not production software
- Not an AI model, agent, or LLM wrapper
- Not a complete solution to AI alignment or hallucination
- Not a claim that nine primitives are sufficient — necessity is established, sufficiency remains open

---

## How to Run

```bash
git clone https://github.com/LivingFramework/ritam-core.git
cd ritam-core
pip install -e runtime/v0.1
python -m pytest runtime/v0.1/tests/ -q
```

Expected: **146 passed**

---

## Licence

Apache 2.0 — see [LICENSE](LICENSE)
