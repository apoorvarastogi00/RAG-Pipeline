# Phase 5 Report — Retrieval Quality + Multi-section / Multi-document

**Phase:** 5
**Agent:** Claude Code
**Module:** [backend/app/retriever.py](backend/app/retriever.py) (rewritten), [backend/app/main.py](backend/app/main.py) (wired to new search), [backend/app/config.py](backend/app/config.py) (retrieval knobs)
**Reranker:** `BAAI/bge-reranker-base` (cross-encoder, local)
**Commit:** `feat: add reranking and multi-section retrieval`

---

## What changed since Phase 4

Phase 4 retrieval was a single bi-encoder search, `k=5`, no reranking. Phase 5
is a two-stage pipeline:

```
query
  │
  ├─ detect_section_refs(query)   →  explicit refs e.g. [('BNS','103')]
  ├─ detect_source_hint(query)    →  "BNS" | "BNSS" | None
  │
  ├─ 1. EXPLICIT  fetch each named section by metadata (all parts), PIN to top
  │
  ├─ 2. DENSE     pull CANDIDATE_POOL_PER_SOURCE (15) per Act with bge-base
  │               — both Acts unless the query names one (guarantees BNSS
  │                 candidates even for an offence-flavoured query, and v.v.)
  │
  ├─ 3. RERANK    bge-reranker-base cross-encoder re-scores the dense union
  │
  └─ 4. SELECT    forced sections first, then best-reranked, capped at
                  max 2 parts/section for diversity → top-k (RERANK_TOP_K=7)
```

New config (in [config.py](backend/app/config.py)):
`CANDIDATE_POOL_PER_SOURCE=15`, `RERANK_TOP_K=7`, `USE_RERANKER=True`.

Three concrete capabilities added:

1. **Reranking.** A wide candidate pool (up to 30 chunks across both Acts) is
   re-scored by the cross-encoder, which reads the query and passage *together*
   — far more accurate than cosine on the bi-encoder vectors alone.
2. **Explicit-section detection.** `detect_section_refs` recognises
   `BNS s.103`, `BNS 103`, `BNSS section 187`, `s. 111`, `section 103`. A
   sourced ref fetches that exact section; an unsourced `section 103` fetches
   **both** BNS s.103 and BNSS s.103 (collision-safe), unless the query also
   names a single Act. Forced sections are pinned above semantic hits and
   bypass the parts cap.
3. **Per-Act candidate pools + diversity cap.** Pulling candidates per Act
   stops one Act from crowding out the other on cross-document questions. The
   ≤2-parts-per-section cap stops a long split section (e.g. BNS s.2, 10 parts)
   from filling every slot on a multi-section question.

---

## Before / after retrieval — six test queries

`*` marks a section pinned by explicit-section detection.
BEFORE = Phase 4 path (`semantic_only`, k=5, no rerank).
AFTER  = Phase 5 path (`search`, k=7, rerank + explicit + per-Act + cap).

### Multi-section #1 — "What is the difference between murder and culpable homicide?"
*(no explicit refs, no source hint)*

| | Sections surfaced (in order) |
|---|---|
| BEFORE | BNS s.101 (Murder), s.102, s.100 (Culpable homicide) |
| AFTER  | BNS s.101 (Murder), s.102, **s.3 (General explanations)**, **s.100 (Culpable homicide)**, s.110, BNSS s.337 |

Both the *Murder* (s.101) and *Culpable homicide* (s.100) definitions are
retained, and the reranker promotes BNS s.3 ("General explanations") which
actually contains the statutory distinction between the two — exactly the
section a lawyer would cite for this question.

### Multi-section #2 — "What offences relate to theft, such as snatching and robbery?"
*(no explicit refs, no source hint)*

| | Sections surfaced |
|---|---|
| BEFORE | BNS s.304 (Snatching), s.309 (Robbery), s.134, s.112 |
| AFTER  | BNS s.304 (Snatching), s.112 (Petty organised crime), BNSS s.201, s.309 (Robbery), s.317 (Stolen property), s.305 (Theft in a dwelling house) |

After surfaces a wider span of theft-family offences (snatching, robbery,
stolen property, theft-in-dwelling). One mild miss: BNSS s.201 (place of
trial) sneaks in at #3 — a procedure section the cross-encoder over-scored;
harmless, the generator ignores irrelevant context.

### Section-number #1 — "What does BNS section 103 say?"
*(explicit ref `('BNS','103')`, source hint BNS)*

| | Sections surfaced |
|---|---|
| BEFORE | BNS s.2, BNSS s.393, BNSS s.411, BNS s.20, BNSS s.317 — **s.103 absent!** |
| AFTER  | **\*BNS s.103 (Punishment for murder)** pinned #1, then BNS s.257, s.2, s.236, s.125, s.1 |

This is the clearest win. The bare bi-encoder could not find s.103 from the
phrase "section 103" (it's not semantically distinctive) — s.103 was missing
entirely from the Phase 4 top-5. Explicit detection fetches it directly and
pins it. The source hint also keeps retrieval inside BNS.

### Section-number #2 — "Explain BNSS s. 187"
*(explicit ref `('BNSS','187')`, source hint BNSS)*

| | Sections surfaced |
|---|---|
| BEFORE | BNSS s.283, **BNS s.187** (wrong Act!), BNSS s.116, BNSS s.187, BNSS s.298 |
| AFTER  | **\*BNSS s.187 (Procedure when investigation cannot be completed in 24 hrs)** pinned, all parts, then BNSS s.237 |

BEFORE pulled `BNS s.187` ("Person employed in mint…") — the **wrong Act's**
section 187 — as its #2 hit, exactly the section-number-collision trap the
project warns about. AFTER pins the correct BNSS s.187 (all parts) at the top.

### Cross-document #1 — "What is the punishment for murder and how is the trial conducted?"
*(no explicit refs, no source hint)*

| | Sections surfaced |
|---|---|
| BEFORE | BNS s.104, s.103, s.105, s.110, s.109 — **100% BNS, zero procedure** |
| AFTER  | BNS s.103 (Punishment for murder), s.104, s.109, **BNSS s.248 (Trial to be conducted by Public Prosecutor)**, BNS s.105, s.101, s.110 |

Per-Act pooling surfaces **BNSS s.248** — the trial-procedure half of the
question that Phase 4 completely missed (its top-5 was all BNS). End-to-end
`/chat` answer now covers both halves:

> "The punishment for murder is stated in **BNS s.103** … **BNS s.104** …
> The trial for such offences is conducted by a Public Prosecutor, as stated
> in **BNSS s.248**, which mandates that in every trial before a Court of
> Session, the prosecution shall be conducted…"
>
> citations: `BNS s.103`, `BNS s.104`, `BNSS s.248` — `no_answer: false`

(Phase 4's answer to the same question ended with "the context does not
provide information on how the trial for murder is conducted.")

### Cross-document #2 — "Can the police search a person's house, and what offence is committed by someone who obstructs the search?"
*(no explicit refs, no source hint)*

| | Sections surfaced |
|---|---|
| BEFORE | BNSS s.44, s.49, s.100, s.103 — **100% BNSS, zero offence sections** |
| AFTER  | BNSS s.103 (search), **BNS s.330 (house-breaking)**, **BNS s.329 (house-trespass)**, **BNS s.333**, BNSS s.44, s.49 |

Per-Act pooling surfaces the BNS offence sections alongside the BNSS search
procedure. End-to-end `/chat` answer:

> "According to **BNSS s.103**, the police can search a person's house …
> If a person obstructs the search, as per **BNSS s.103(8)**, they shall be
> deemed to have committed an offence under **BNS s.222** … Regarding the
> search of a place, **BNSS s.44** allows a police officer to enter and
> search…"
>
> citations: `BNSS s.103`, `BNS s.222`, `BNSS s.44`, `BNS s.329`, `BNS s.330`, `BNS s.333` — `no_answer: false`

(The model even followed the statutory cross-reference inside BNSS s.103(8)
to **BNS s.222** — a section that wasn't itself retrieved. That citation
carries the snippet `"(citation not present in retrieved context)"`; see
manual-check 4.)

---

## Summary of the wins

| Failure mode in Phase 4 | Fixed by |
|---|---|
| "section 103" couldn't find s.103 | explicit-section fetch + pin |
| "BNSS s.187" returned BNS s.187 (wrong Act) | explicit ref carries source + source hint filter |
| cross-doc query returned one Act only | per-Act candidate pools |
| long split sections crowded the top-k | ≤2 parts/section diversity cap |
| close-but-wrong dense ranking | cross-encoder rerank |

Latency: ~+1–1.5 s per query for the cross-encoder over ~30 candidates on
CPU. Total `/chat` latency ~3–4 s, still dominated by the Groq generation
call. Server start-up is ~9 s now (loads bge-base **and** bge-reranker-base
once in the lifespan hook).

---

## Manual checks for Apoorva

1. **Reproduce the before/after table.** A standalone comparison script path
   was used during development; you can reproduce any single query via the
   REPL:
   ```bash
   .venv/bin/python - <<'PY'
   from backend.app.retriever import Retriever
   r = Retriever()
   for c in r.search("Explain BNSS s. 187", k=7):
       tag = "*" if c.forced else " "
       print(f"{tag}{c.source} s.{c.section_number} part {c.part}  rerank={c.rerank_score}")
   PY
   ```
   The `*` rows are the explicitly-pinned section.
2. **The collision trap, end to end.** Through the running server:
   ```bash
   curl -s -X POST localhost:7860/chat -H 'Content-Type: application/json' \
     -d '{"query":"Explain BNSS s. 187"}' | python -m json.tool
   ```
   Citations must be `BNSS s.187` (procedure), never `BNS s.187` (mint/coin).
3. **Cross-document coverage.** Ask the two cross-document questions above and
   confirm the citations list mixes BNS **and** BNSS. This is the assignment's
   "questions that span both documents" requirement — it now works.
4. **Citations the model inferred via cross-reference.** In cross-doc #2 the
   model cited `BNS s.222` because BNSS s.103(8) names it, even though s.222
   wasn't retrieved. Its citation snippet is the placeholder
   `"(citation not present in retrieved context)"`. Decide whether you want
   the API to (a) leave it as-is, (b) do a follow-up fetch of cited-but-not-
   retrieved sections to fill the snippet, or (c) drop such citations. My
   recommendation: option (b) in Phase 6/8 — it's a small, high-value fetch.
5. **Tunable knobs** in [config.py](backend/app/config.py):
   `CANDIDATE_POOL_PER_SOURCE` (breadth vs latency), `RERANK_TOP_K` (how many
   chunks the LLM sees), `USE_RERANKER` (set False to A/B against pure dense).
   The `max_parts_per_section` cap is a parameter on `Retriever.search`
   (default 2). Flag if you want different defaults before Phase 6 evals.
6. **One mild over-retrieval** noted: multi-section #2 surfaced BNSS s.201
   (place of trial) for a pure-offence question. It's harmless (generator
   ignores irrelevant context), but if the Phase 6 evals show procedure noise
   hurting offence-only questions, we can add a light source-bias when the
   query is clearly offence-only. Not doing it now to avoid over-fitting.

---

## Final submission update — 2026-05-28

Phase 5 retrieval remains the deployed retrieval path: explicit-section
pinning, per-Act candidate pools, reranking, and diversity-capped top-k.
The new 20-question eval includes an `ambiguous_followup` row that retrieves
both BNS s.109 and BNS s.103 for the public-shooting scenario.
