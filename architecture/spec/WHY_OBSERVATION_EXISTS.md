# Why Observation Exists

*Session 105 · Pre-implementation behavioural definition*
*Format follows WHY_TEMPORAL_EXISTS.md and WHY_EPISTEMIC_EXISTS.md*

---

## §1 The Problem

The substrate already emits signals. When an unknown category is proposed,
`SignalType.OBSERVATION_GAP` fires on the ObservationChannel. When a contradiction
is quarantined, `SignalType.QUARANTINED` fires. This is working.

But all signals are ephemeral. Call `channel.drain()` and they are gone from the
substrate. The substrate has no memory of what it could not see. Three concrete
failures follow from this.

**Failure 1 — Gap records are transient.** When `OBSERVATION_GAP` fires because
a consumer proposed content in an unknown category, that gap is in the channel
buffer. After `drain()`, the substrate itself has no record that this gap ever
occurred. If the same unknown category is proposed fifty times, the substrate
does not know it has been asked fifty times about something it cannot represent.

**Failure 2 — No aggregate visibility into perceptual limits.** There is no way
to ask: "what categories has this substrate failed to represent?" or "which gaps
recur most often?" The substrate is blind to its own blindspots in aggregate. An
operator wanting to understand whether to expand `known_categories` has no
evidence base — only signal drains they may or may not have captured externally.

**Failure 3 — Gap provenance is lost.** When a gap occurs, the information
about *when*, *from whom*, and *with what content type* is available only while
the signal lives in the channel buffer. There is no queryable record of gap
provenance. Auditing the substrate's perceptual history is impossible.

---

## §2 What Observation Governs

Observation governs the **persistent record of what the substrate cannot represent**.

This is distinct from what the ObservationChannel already does. The channel is a
real-time signal bus — it broadcasts events to subscribers. The Observation
primitive is a durable, queryable log of the substrate's perceptual limits.

Three governing mechanisms:

1. **Gap persistence.** When `OBSERVATION_GAP` fires, the event is also written
   to a persistent `ObservationLog`. The substrate now remembers what it could
   not see, independently of whether the channel was drained.

2. **Gap queryability.** Operators and consumers can ask: `gw.list_gaps()` —
   what has this substrate failed to represent? Filter by category, by source,
   by time range.

3. **Recurrence detection.** `gw.gap_count(category)` returns how many times a
   given unknown category has been proposed. This turns transient blindness into
   a structured signal about what the substrate's ontology is missing.

**Protected distinction:** Observation records *what the substrate cannot see* —
not what is true or false about the world. A gap record says "this category was
unknown at this time." It makes no claim about whether the proposed content was
valid, important, or worth admitting. Observation is awareness, not judgement.

---

## §3 Observable Behaviour

**B1 — Gap persistence on OBSERVATION_GAP.** When `gw.propose(content, category,
source)` fires `OBSERVATION_GAP` (because `category` is not in
`known_categories`), a `GapRecord` is simultaneously written to the
`ObservationLog`. The signal fires AND the record persists. These are independent
— draining the channel does not remove the gap record.

**B2 — `gw.list_gaps()` returns all gap records.** Returns a list of `GapRecord`
objects ordered by `observed_at` ascending. Each record carries: `gap_id`,
`category` (the unknown category that was proposed), `content_type` (Python type
name of the proposed content), `source`, `observed_at` (ISO string).

**B3 — Filtering by category.** `gw.list_gaps(category="unknown-category")`
returns only gap records for that specific category. Enables operators to see all
occurrences of a specific perceptual limit.

**B4 — Recurrence count.** `gw.gap_count(category)` returns an integer — how
many times this unknown category has been encountered. Zero if never. This is the
key signal for deciding whether to expand `known_categories`.

---

## §4 Failure Modes

**F1 — Gap log unbounded growth.** If a consumer repeatedly proposes content in
unknown categories (e.g., a bug in a consumer loop), the ObservationLog grows
without bound. In v1.0.x this is acceptable — the log is a research record. A
future version may add pruning or archiving.

**F2 — Gap records do not indicate importance.** A gap that occurs once from one
source and a gap that occurs a thousand times from many sources are both `GapRecord`
objects. The substrate records occurrence count via `gap_count()` but does not
weight, prioritise, or alert on recurrence thresholds. That is a consumer decision.

**F3 — Observation of non-gap events.** The Observation primitive in v1.0.x
records only `OBSERVATION_GAP` events. Other signal types (QUARANTINED, RETRACTED,
TEMPORAL_ALERT, EPISTEMIC_ALERT) are not persisted to ObservationLog — they remain
ephemeral channel signals. This is a deliberate scope boundary. Full operational
logging is a separate concern (audit log, not observation primitive).

**F4 — No observation of successful admissions.** `ADMITTED` events are not
persisted to ObservationLog. The observation primitive is specifically about
perceptual limits — what the substrate cannot represent — not a general-purpose
event log.

---

## §5 Repair Modes

The Observation primitive does not produce `RepairSuggestion` objects. This is a
deliberate departure from Temporal and Epistemic.

**Why no repair here:** Temporal and Epistemic alerts fire on *admitted items* —
things already inside the substrate that need attention. Gaps fire on *rejected
proposals* — things the substrate never admitted. There is no item to repair.
The correct response to a gap is a configuration decision (add the category) or
a consumer decision (rephrase the proposal). Neither is a substrate repair operation.

The gap record is itself the actionable output. An operator reads `list_gaps()`,
sees recurring unknown categories, and decides whether to update `known_categories`
in the next substrate configuration. That decision happens outside the substrate.

---

## §6 Relationship to ObservationChannel, Temporal, and Epistemic

**ObservationChannel** — the real-time signal bus. Observation primitive adds
persistence alongside it, not instead of it. The signal still fires; the record
also persists. They are complementary.

**Temporal** — governs age of admitted items. Observation governs what was never
admitted. Orthogonal.

**Epistemic** — governs declared confidence of admitted items. Observation governs
what the substrate couldn't represent at all. Orthogonal.

**ContradictionStore** — persists contradiction records for admitted items that
conflict. ObservationLog persists gap records for proposals the substrate could not
categorise. Structurally analogous: both are persistent, queryable logs of substrate
governance events. One is for the inside (contradiction among admitted items); the
other is for the boundary (what couldn't get in at all).

---

## §7 What Observation Does NOT Do

- **Does not add unknown categories automatically.** A gap record is not an
  admission. The substrate never self-configures its ontology in response to
  observations.
- **Does not persist all signal types.** Only `OBSERVATION_GAP` events are
  written to ObservationLog. This is v1.0.x scope.
- **Does not prioritise or weight gaps.** All gap records are equal in the log.
  Recurrence count is available; threshold-based alerting is not.
- **Does not observe the consumer.** Observation records what happened at the
  substrate boundary — the proposal attempt. It does not record what the consumer
  intended or what it did with the result.
- **Does not replace ObservationChannel.** The signal bus remains the primary
  real-time mechanism. ObservationLog is the durable counterpart.

---

## §8 Executable Form

Observation exists when all of the following are true and tested:

1. `GapRecord` dataclass exists: `gap_id`, `category`, `content_type`, `source`,
   `observed_at` (ISO string).
2. When `gw.propose(content, unknown_category, source)` fires `OBSERVATION_GAP`,
   a `GapRecord` is simultaneously persisted to `ObservationLog` in SQLite.
3. `gw.list_gaps()` returns `list[GapRecord]` — all persisted gap records,
   ordered by `observed_at` ascending.
4. `gw.list_gaps(category=X)` filters by unknown category name.
5. `gw.gap_count(category)` returns `int` — number of times this unknown
   category has been encountered. Zero if never seen.
6. Gap records persist across `channel.drain()` — draining the ObservationChannel
   does not remove gap records from ObservationLog.
7. Test: propose to unknown category → assert `OBSERVATION_GAP` emitted AND
   `list_gaps()` returns the record AND item not admitted.
8. Test: propose same unknown category three times → `gap_count(category)` == 3.

---

## §9 Protected Distinction

**Observation records perceptual limits, not truth judgements.**

A `GapRecord` says: "at this time, from this source, content of this type was
proposed in a category this substrate does not recognise." It makes no claim
about whether the proposed content was important, valid, or whether the category
*should* exist. The substrate observed a limit; it did not evaluate the proposal.

Signal payloads and `GapRecord` fields must describe the substrate's perceptual
state — never the value or correctness of what was proposed. "Unknown category
encountered" — not "invalid proposal" or "rejected content."

---

*Awaiting sign-off before implementation.*

---

## §10 Design Sign-Off — Session 105

**Rishi's review (verbatim reasoning, 2026-06-22):**

"This is much stronger than I expected Observation to be. Because it passes the test I keep applying to every remaining primitive: Does it solve a substrate failure that the current runtime cannot solve? And surprisingly, I think the answer is: Yes."

"The most important sentence: *Observation ≠ ObservationChannel.* Channel = What happened. Observation = What was missed. Those are different things."

"I agree with the no-repair decision. Temporal: item exists → needs action. Epistemic: item exists → needs attention. Observation gap: item never entered. There is literally nothing inside the substrate to repair."

**Future concern (not v1 scope):** Gap lifecycle — OPEN / RESOLVED / ACKNOWLEDGED. If builders start asking "which gaps still matter?", Observation will need status tracking. Not blocking implementation; flag for a future iteration.

**Architectural observation (Rishi):** "Look at the last three primitives. Temporal tracks Age. Epistemic tracks Confidence. Observation tracks Blindness. These are no longer governing content. They're governing properties of cognition itself."

Sign-off: ✅ Build it.
