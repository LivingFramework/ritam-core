# Contributing to RITAM

Thank you for your interest in RITAM.

## Before You Open a PR

RITAM is a research prototype in active development. Before submitting a pull request, please open an issue first to discuss what you would like to change. This ensures your effort is aligned with the current research direction.

## What We Welcome

- **Bug reports** — if a test fails from a clean clone, that is a bug
- **Specification questions** — if the WHY_ documents or Technical Overview are unclear, open a discussion
- **Reproduction reports** — if you built a consumer on the substrate and want to share results, we would like to hear about it
- **Objections** — see `WHY_RITAM_MIGHT_BE_WRONG.md`; if you have a stronger objection not listed there, open an issue

## What We Are Not Looking For Right Now

- New primitives (the current set is under active research)
- Application-layer consumers (out of scope for this repo)
- Performance optimisations (research prototype, not production software)

## Running the Tests

```bash
git clone https://github.com/LivingFramework/ritam-core.git
cd ritam-core
pip install -e runtime/v0.1
python -m pytest runtime/v0.1/tests/ -q
```

Expected: 146 passed.

## Code Style

- Python 3.9+
- No external dependencies beyond the standard library for the core runtime
- All new behaviour must be covered by tests
- All new primitives (if ever added) must have a `WHY_<PRIMITIVE>_EXISTS.md` doc with a concrete failure argument

## Governance

RITAM is governed research. Architectural decisions are recorded in `decisions/` as ADRs. If you propose a change that affects the architecture, expect a discussion about the failure argument it addresses.

---

*RITAM — Living Framework · Apache 2.0*
