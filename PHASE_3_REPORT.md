# Phase 3 Report — Embedding pipeline + Chroma index

**Phase:** 3
**Agent:** Claude Code
**Modules:** [backend/app/config.py](backend/app/config.py), [backend/app/ingest.py](backend/app/ingest.py)
**Vector DB:** ChromaDB persisted at [backend/data/chroma/](backend/data/chroma/) (~20 MB)
**Embedding model:** `BAAI/bge-base-en-v1.5` (open-source, runs locally)
**Run:** `.venv/bin/python -m backend.app.ingest`
**Commit:** `feat: add embedding pipeline and Chroma index`

---

## Result

```
Total chunks indexed: 1162    (BNS 473, BNSS 689)
Collection name:      legal_sections
Distance metric:      cosine (vectors normalized)
Embedding time:       ~13 s for full re-index on CPU (Apple Silicon)
Disk footprint:       20 MB total (15 MB SQLite + ~5 MB HNSW index)
Re-run idempotency:   confirmed — second `python -m backend.app.ingest`
                      leaves the collection at 1162 (upsert by chunk_id).
```

## What ingest does

`backend/app/ingest.py` is one end-to-end command:

1. **Hydrate sections** — if `backend/data/sections.json` is missing, re-runs
   the Phase 1 parser; otherwise reads the existing file.
2. **Hydrate chunks** — same for `backend/data/chunks.json` and the Phase 2
   chunker.
3. **Embed** — loads `BAAI/bge-base-en-v1.5` via sentence-transformers and
   encodes every chunk. The vector input is the chunk body prefixed with a
   compact context header (`"BNS section 103. Punishment for murder. OF
   OFFENCES AFFECTING THE HUMAN BODY.\n\n<body>"`) so semantic similarity
   captures the section identifier even when the user's query uses different
   wording. Vectors are L2-normalised; Chroma is configured with
   `hnsw:space="cosine"` so distance ≈ 1 − cosine similarity.
4. **Upsert** — writes 1162 documents into the persistent Chroma collection
   `legal_sections`, keyed by `chunk_id` (so re-runs overwrite in place;
   never duplicate).

Stored per document:
- `documents` — the raw body text (what we return to the LLM in Phase 4).
- `metadatas` — `{source, section_number, marginal_heading, chapter,
  chapter_title, part}`. Every entry has `source` populated to `"BNS"` or
  `"BNSS"`, which is what makes the section-103 collision resolvable both
  ways (see sample queries 1 and the source-filter check below).
- `embeddings` — 768-dim float32 vectors.

## Query helper

`ingest.query(coll, model, text, k=5, where=None)`:
- Prefixes the query with `"Represent this sentence for searching relevant
  passages: "` — the official BGE recommendation for short-query-to-passage
  retrieval (s2p task).
- Returns Chroma's native shape (`metadatas`, `documents`, `distances`).
- Pass `where={"source": "BNS"}` (or `{"source": "BNSS"}`) to constrain
  retrieval to one Act — used for explicit-section queries in Phase 5.

## Sample similarity queries

Two BNS-flavoured, two BNSS-flavoured queries, top-5 each. All returned the
correct Act and the on-point section in the #1 or #2 slot.

```
QUERY (BNS): What is the punishment for murder?
  [1] BNS s.103_p1  dist=0.277  Punishment for murder
      → 103.(1) Whoever commits murder shall be punished with death or imprisonment for life…
  [2] BNS s.104_p1  dist=0.292  Punishment for murder by life-convict
      → 104.Whoever, being under sentence of imprisonment for life, commits murder…
  [3] BNS s.105_p1  dist=0.304  Punishment for culpable homicide not amounting to murder
      → 105. Whoever commits culpable homicide not amounting to murder, shall be punished…
  [4] BNS s.110_p1  dist=0.320  Attempt to commit culpable homicide
  [5] BNS s.109_p1  dist=0.334  Attempt to murder

QUERY (BNS): What is the punishment for theft?
  [1] BNS s.304_p1  dist=0.272  Snatching
      → 304. (1) Theft is snatching if, in order to commit theft, the offender suddenly or quickly…
  [2] BNS s.303_p6  dist=0.291  Theft
      → (2) Whoever commits theft shall be punished with imprisonment of either description…
  [3] BNS s.317_p2  dist=0.311  Stolen property
  [4] BNS s.305_p1  dist=0.312  Theft in a dwelling house, or means of transportation or place of worship
  [5] BNS s.134_p1  dist=0.329  Assault or criminal force in attempt to commit theft of property carried

QUERY (BNSS): How long can the police detain a person before producing them in court?
  [1] BNSS s.187_p3 dist=0.253  Procedure when investigation cannot be completed in twenty-four hours
      → Explanation I.—For the avoidance of doubts, it is hereby declared that…
  [2] BNSS s.58_p1  dist=0.266  Person arrested not to be detained more than twenty-four hours
      → 58. No police officer shall detain in custody a person arrested without warrant for a longer period…
  [3] BNSS s.187_p2 dist=0.281  Procedure when investigation cannot be completed in twenty-four hours
  [4] BNSS s.78_p1  dist=0.285  Person arrested to be brought before Court without delay
  [5] BNSS s.40_p1  dist=0.322  Arrest by private person and procedure on such arrest

QUERY (BNSS): What is the procedure for arrest without a warrant?
  [1] BNSS s.55_p1  dist=0.248  Procedure when police officer deputes subordinate to arrest without warrant
  [2] BNSS s.35_p1  dist=0.264  When police may arrest without warrant
      → 35. (1) Any police officer may without an order from a Magistrate and without a warrant…
  [3] BNSS s.35_p5  dist=0.269  When police may arrest without warrant
  [4] BNSS s.57_p1  dist=0.288  Person arrested to be taken before Magistrate or officer in charge of police station
  [5] BNSS s.35_p2  dist=0.291  When police may arrest without warrant
```

### Source-disambiguation check (the section-103 collision)

With `where={"source": "BNS"}` the same `"section 103"` query returns BNS
s.103 ("Punishment for murder"). With `where={"source": "BNSS"}` it returns
BNSS s.103 ("Persons in charge of closed place to allow search"). Both
collide on number; both are correctly indexed; metadata filtering keeps
them apart.

## Observations to revisit in Phase 5

1. **Theft query returned `Snatching` at #1, `Theft` at #2.** The bge model
   sees "punishment for theft" and matches `BNS s.304` ("Snatching is theft
   if …") slightly better than `BNS s.303` because s.303 part 1 is the
   *definition* of theft, while s.303 part 6 is the punishment sub-clause.
   A cross-encoder reranker (Phase 5) should re-order this — it's the
   canonical case where dense retrieval is close-but-not-quite.
2. **`BNSS s.187_p3` outranks `BNSS s.58_p1`.** The 24-hour rule lives in
   *both* sections. s.58 is the headline one-liner; s.187 is the procedural
   detail. Both are correct; the reranker / generator can be told to prefer
   the more general statement.
3. **Distance values cluster in `0.25–0.35`.** That's expected for
   semantically-related-but-not-identical query/passage pairs with
   normalised cosine. Use these as a calibration baseline if we later add
   a "no_answer" threshold.

---

## Manual checks for Apoorva

1. **Re-run ingest, confirm idempotency:**
   ```bash
   .venv/bin/python -m backend.app.ingest | tail -5
   # → "collection now has 1162" — same as the first run, no duplicates.
   ```
2. **Confirm the persistence directory exists and is gitignored:**
   ```bash
   ls -la backend/data/chroma/         # should show chroma.sqlite3 + 1 UUID dir
   git check-ignore backend/data/chroma  # should print the path = ignored
   ```
3. **Cross-check section-103 collision via Python REPL:**
   ```bash
   .venv/bin/python - <<'PY'
   import chromadb
   from backend.app import config
   from backend.app.ingest import query
   from sentence_transformers import SentenceTransformer
   coll = chromadb.PersistentClient(path=str(config.CHROMA_DIR)).get_collection(config.COLLECTION_NAME)
   m = SentenceTransformer(config.EMBED_MODEL_NAME)
   for src in ("BNS", "BNSS"):
       r = query(coll, m, "section 103 explained", k=1, where={"source": src})
       md = r["metadatas"][0][0]
       print(src, "→", md["source"], "s." + md["section_number"], "|", md["marginal_heading"])
   PY
   # Expect:
   #   BNS  → BNS  s.103 | Punishment for murder
   #   BNSS → BNSS s.103 | Persons in charge of closed place to allow search
   ```
4. **Two cross-document queries** (these should surface BOTH Acts when run
   without a filter — they exercise the assignment's "questions that span
   multiple sections of the law / both documents" requirement):
   - *"What is murder and how is the trial conducted?"* — should return BNS
     s.101–s.103 (offence) AND BNSS s.250-ish (charge / trial procedure).
   - *"Can police search someone's house, and what offences could be
     committed inside it?"* — should mix BNSS Chapter VII (search procedure)
     and BNS Chapter VI (offences inside a dwelling).
   These are exploratory — they're how we'll calibrate retrieval depth in
   Phase 5. If you want me to run them now and capture the results, say so.
5. **Embedding header — design call to confirm.** Each chunk is embedded
   as `"{source} section {N}. {heading}. {chapter_title}.\n\n{body}"`. The
   *document* stored in Chroma is still the raw body, so this only affects
   the vector. If you'd rather embed the bare body (matches the chunk text
   1:1), it's a single function (`_embedding_input` in
   [backend/app/ingest.py](backend/app/ingest.py)) to drop the prefix and
   re-run. My recommendation is to keep it — sample query 1 shows the
   identifier is what disambiguates "punishment for murder" between BNS
   s.103 and BNSS sections; without the prefix the top hit was correct but
   the runners-up included less-relevant BNSS sections.
6. **Heads-up: 7 chunks are over the 512-token model limit** (carried over
   from Phase 2). Their embeddings reflect only the first ~1800 chars; the
   tail is invisible to retrieval. Listed in [PHASE_2_REPORT.md](PHASE_2_REPORT.md).
   We can revisit if any of them shows up missing in the Phase 6 evals.
