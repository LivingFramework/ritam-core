# RITAM — Governed Cognition Substrate

RITAM is a **governed cognition substrate**: a runnable layer that sits beneath an application and holds its cognitive state under explicit governance. As a database manages persistent structured data, RITAM manages persistent cognitive state — with governed admission, epistemic tracking, contradiction detection, and observable repair. It is infrastructure, not an application, model, or agent.

The substrate is built from nine primitives (State, Memory, Ontology, Governance, Epistemic, Coordination, Temporal, Observation, Repair), each addressing a specific failure mode that appears in AI systems operating without a governance layer: belief drift, contradiction accumulation, uncontrolled decay, and opacity of reasoning. All nine primitives are implemented, integrated, and adversarially audited. Version v1.1.1 passes 146/146 tests.

---

## Start here

**[Technical Overview](architecture/orientation/RITAM_TECHNICAL_OVERVIEW.md)** — What RITAM is, why nine primitives, what has been demonstrated, what remains open. Read this first.

**[North Star](NORTH_STAR.md)** — Why RITAM exists and what counts as success.

**[Substrate Definition](SUBSTRATE_DEFINITION.md)** — The precise definition of what a governed cognition substrate is and is not.

---

## Run the prototype

Requirements: Python 3.9+

```bash
git clone https://github.com/LivingFramework/ritam-core.git
cd ritam-core
pip install -e runtime/v0.1
cd runtime/v0.1
python -m pytest tests/ -q
```

All 146 tests should pass.

---

## What this repository contains

```
NORTH_STAR.md                          Why RITAM exists
SUBSTRATE_DEFINITION.md                What a governed cognition substrate is
architecture/
  orientation/
    RITAM_TECHNICAL_OVERVIEW.md        What has been demonstrated (start here)
  spec/
    WHY_*_EXISTS.md                    Why each of the nine primitives exists
runtime/
  v0.1/                                v1.1.1 source + 146 tests
decisions/                             Key architectural decisions (ADRs)
```

---

## What this repository does not contain

The full research record — 113 sessions of experiments, findings, open questions, working documents, and session logs — remains in the private research repository. This repository is a curated window into that work: the canonical public artifacts only.

---

## Status

**v1.1.1 · Phase 2 · Public Canon**

All nine primitives implemented and integrated. Adversarial audit complete (Phase 5B). Specification transfer demonstrated across five independent AI implementations (INSIGHT-073, Tier D).

This is a research prototype demonstrating governed cognition architecture. It is not production software.

---

## License

[To be determined before public release]

---

*RITAM — LivingFramework · Founded Session 001 · v1.1.1*
