# Zenodo Submission Guide — RITAM v1.1.1

## What to submit
A **Technical Report** (not a research paper). Zenodo supports this record type.
This gives RITAM a DOI, a permanent archive, and a timestamped priority record.

---

## Step-by-step

### 1. Connect GitHub to Zenodo (one-time setup)
1. Go to https://zenodo.org and sign in (or create account with GitHub)
2. Go to https://zenodo.org/account/settings/github/
3. Find `LivingFramework/ritam-core` in the list and flip the toggle **ON**
4. From this point, every GitHub Release automatically creates a Zenodo record

### 2. Create the GitHub Release (if not done already)
- Go to https://github.com/LivingFramework/ritam-core/releases/new
- Tag: `v1.1.1`
- Title: `RITAM v1.1.1 — Initial Public Release`
- Body: copy from `RELEASE_NOTES_v1.1.1.md` in the repo
- Click **Publish release**

### 3. Zenodo auto-creates the record
After the release is published, Zenodo creates a draft record automatically.
Go to https://zenodo.org/deposit to find it.

### 4. Edit the Zenodo record metadata

**Upload type:** Software *(or Technical Report if you prefer — both work)*

**Title:**
```
RITAM: A Governed Cognition Substrate (v1.1.1)
```

**Authors:**
```
Living Framework AI
```

**Description (paste this):**
```
RITAM is a governed cognition substrate — a runtime layer that sits beneath an AI 
application and holds its cognitive state under explicit governance. It implements 
nine substrate primitives (State, Memory, Ontology, Governance, Epistemic, 
Coordination, Temporal, Observation, Repair) with 146 tests across adversarial, 
integration, and buildability scenarios.

Key findings:
- Governance changes outcomes: a governed substrate produces measurably different 
  results from an ungoverned baseline
- All nine primitives are load-bearing: removing any one causes observable failure 
  in adversarial testing  
- The specification is transferable: five independent AI systems reproduced the 
  runtime from the specification alone (60/60 tests)

This is a research prototype. v1.1.1 is the first public release.
```

**Keywords (add each separately):**
```
cognitive architecture
ai governance
governed cognition
ai substrate
knowledge management
contradiction detection
epistemic state
long-horizon ai
research prototype
```

**Licence:** Apache Software License 2.0

**Version:** 1.1.1

**Related identifiers:**
- Add: https://github.com/LivingFramework/ritam-core (is supplement to)

### 5. Publish
Click **Publish** — Zenodo issues the DOI immediately.

### 6. Add DOI badge to README
After publishing, Zenodo shows a badge like:
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)

Tell Claude the DOI number and I'll add the badge to the README.

---

## Why Zenodo over arXiv?
- No peer review gate — publish immediately
- DOI issued instantly — citable from day one
- Timestamps the architecture before any future similar work
- Software + Technical Report record types both supported
- Free, permanent, backed by CERN

---

## Timeline
Mahdi's recommendation: don't rush. Let the public repo sit for a few weeks first.
The Zenodo submission can happen any time after the repo feels stable.
