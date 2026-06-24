# Consumer Generality Notes
**Session 081 · ChatGPT advisory points 4+5 (2026-06-18)**

> Running document. Append-only. Every time a notebook-specific assumption appears in the substrate or its interfaces, it is logged here with a disposition: push up to notebook layer / generalise / keep with justification.

The purpose of this document is to prevent **consumer drift**: the substrate accidentally becoming a governed notebook instead of a governed cognition substrate.

**Test for every assumption:** "Would a different consumer also need this unchanged?" If no → it belongs in the notebook application layer, not `ritam.runtime.v01`.

---

## Named Consumers (v0.1)

| Consumer | Description | Status |
|---|---|---|
| **Governed Research Notebook** | Wraps Substrate to govern research propositions — findings, hypotheses, questions, method-notes. Kill Test consumer. | Implemented — `runtime/v0.1/notebook/governed_notebook.py` |
| **Governed Agent Memory Layer** | Governs RITAM programme memory: facts, decisions, insights, questions, and the governing hypothesis. Kill Test 8 consumer. | **Implemented S088** — `runtime/v0.1/agent_memory/governed_agent_memory.py` |

The second consumer is named now (not implemented) to make the substrate/application boundary concrete and to surface notebook-centric drift early. Any substrate feature that only makes sense for notebooks and not for the agent memory layer is a warning sign.

---

## Assumption Log

| # | Session | Assumption / Design choice | Location | Verdict |
|---|---|---|---|---|
| 1 | 081 | `plural_categories` defaults for GovernedNotebook are `{"hypothesis", "question", "method-note"}` — these are research notebook category names | `notebook/governed_notebook.py` | **Notebook layer** — correct. SubstrateConfig.plural_categories is general; the notebook populates it with its own vocabulary. Substrate correctly has no opinion on which categories are plural. |
| 2 | 081 | `list_observation_gaps()` drains the channel inside `add_entry()` — means post-hoc calls return empty | `notebook/governed_notebook.py` | **Design note** — channel drain on each add_entry is a notebook convenience choice. An agent consumer might prefer to drain on a schedule. Consider exposing a drain-or-peek option in v0.2. OQ candidate. |
| 3 | 081 | `get_entry()` accesses `substrate._db` directly (internal) | `notebook/governed_notebook.py` | **Boundary violation (minor)** — direct DB access bypasses the substrate interface. Should be exposed as a substrate read method in v0.2. Logged; acceptable for v0.1. |

---

## Second Consumer: Governed Agent Memory Layer — Sketch

**What it would do:**
An autonomous agent proposes observations (what it sees) and plans (what it intends to do). The substrate governs admission: conflicting plans are quarantined rather than both being executed; observations in unknown categories surface as gaps.

**Same substrate API, different vocabulary:**
```python
SubstrateConfig(
    known_categories=["observation", "plan", "action-taken", "constraint"],
    plural_categories=["observation", "action-taken"],  # multiple observations OK
    # "plan" is singular — conflicting plans are a contradiction
)
```

**Kill Test for agent consumer:**
> "Did the substrate prevent the agent from holding two contradictory plans simultaneously?"

**Why naming this now matters:**
Every line added to `ritam.runtime.v01` that only makes sense for notebooks and not for this agent consumer is substrate/application boundary drift. This sketch is the reference.


---

## Session 082 — Assumption Log Addition

**Assumption A-004:** Empty or whitespace-only entry content is a valid admission by default (v0.1).

**Verdict:** Valid in v0.1 (substrate admits anything structurally non-duplicate). **Design concern flagged.**
In singular categories, an empty-string first entry renders all subsequent entries as contradictions — the substrate is correct by its rules but the behaviour is a usability hazard. A content validation hook at admission boundary is the candidate fix.

**Consumer generality question:** Would the Governed Agent Memory Layer also need content validation? Answer: **yes** — an agent plan of `""` is degenerate and should be rejected before governance runs. This is substrate-level behaviour, not consumer-specific. → **OQ-056** logged for v0.2 design.


---

## Session 084 — Kill Test S084 Assumption A-005

**Assumption:** The Kill Test uses `empirical-finding` as a SINGULAR category, meaning only one empirical finding can be admitted per fresh notebook instance.

**Observed:** C2 ("6/9 primitives unimplemented") triggered a false positive conflict against C1 ("structural detection, not semantic") — two findings about different phenomena, both categorized `empirical-finding`.

**Design concern:** Singular empirical-finding is too restrictive for multi-phenomenon research notebooks. The substrate cannot distinguish "second finding" from "contradictory claim."

**OQ-057 logged** for v0.2 design (topic-scoped singular enforcement or category split).

**Consumer generality:** The Governed Agent Memory Layer second consumer has the same exposure — agents accumulate multiple empirical observations across topics.

---

## Session 085 — v0.2 changes and consumer generality

**Changes in v0.2:**
- `empirical-finding` is now PLURAL (OQ-057 fix). Multiple findings coexist without false-positive conflicts.
- `canonical-claim` is new SINGULAR governed category. One authoritative assertion per notebook; conflict detection active.
- Content validation at admission boundary (OQ-056 fix). Empty/whitespace/None content rejected before database operations.

**Consumer generality of canonical-claim:**
The Governed Agent Memory Layer (second consumer) benefits directly. An agent accumulating advice across sessions can hold one canonical position on each governed question. If a later session produces an opposing position, the substrate surfaces the conflict immediately rather than silently overwriting. This is the governance pattern for AI advice-giving — each session's advice enters as a canonical-claim; contradictions surface at write time.

**Kill Test S085 observation:**
First use of canonical-claim produced a genuine governance event (R3 vs C1 — governance-over-reliability vs reliability-over-governance). This is the category working as designed: it governs the programme's direction, not just its evidence base.

---

## Session 088 — Kill Test 8 findings

**Consumer:** GovernedAgentMemory (RITAM programme memory)

**Category vocabulary:**
| Category | Mode | Rationale |
|---|---|---|
| `programme-fact` | PLURAL | Multiple facts accumulate; each fact is a distinct observation |
| `governing-hypothesis` | SINGULAR | At-most-one canonical governing hypothesis; contradictions → QUARANTINE |
| `open-question` | PLURAL | Multiple OQs coexist |
| `decision` | PLURAL | ADRs accumulate; superseded decisions are new entries, not replacements |
| `insight` | PLURAL | INSIGHT-NNN entries accumulate |

**Kill Test 8 result:**
- GovernedAgentMemory: 1 governance event (CC2-as-governing-hypothesis QUARANTINED against P4b)
- BaselineAgentMemory: 0 governance events
- Cumulative: 9 gov events / 9 runs / 0 baseline. Kill condition NOT MET.

**INSIGHT-118:** Substrate-generality confirmed. Same engine, new consumer vocabulary, same governance guarantee.

**Secondary finding (INSIGHT-118 body):** Baseline heuristic produced 15 false-positive "conflicts" among legitimately plural entries (C(5,2)=10 programme-fact pairs plus decision/insight pairs). The baseline cannot distinguish plurality from contradiction. The substrate avoids this by encoding the distinction in the category vocabulary. This is not a minor implementation detail — it is the core governance abstraction.

**Assumption A-006 (S088):**
GovernedAgentMemory accesses `substrate._db` directly for reads (same as GovernedNotebook A-003).
Verdict: boundary violation (minor), acceptable for v0.1. Expose as substrate read method in v0.2.

