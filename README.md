# Legal Research RAG Chatbot — BNS & BNSS, 2023

A grounded Retrieval-Augmented Generation chatbot for India's new criminal
law: ask a question in plain English and get an answer cited to the exact
sections of the statute, never an ungrounded guess.

It indexes **both** of the 2023 codes that replaced the colonial-era criminal
law:

- **Bharatiya Nyaya Sanhita (BNS), 2023** — the criminal **offences** code
  (replaces the Indian Penal Code).
- **Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023** — the criminal
  **procedure** code (replaces the Code of Criminal Procedure).

> **Live demo:** not yet deployed. The repo is deploy-ready — `render.yaml`
> defines a Render Blueprint (Dockerised backend + static frontend); see
> [Deployment](#deployment). Paste the URL here once live.

---

## Why both documents are indexed

The assignment names the BNS. The BNSS is included **deliberately**, because
offences (BNS) and procedure (BNSS) are inseparable: a question like *"what is
the punishment for murder and how is the trial conducted?"* needs the offence
from the BNS **and** the trial procedure from the BNSS. The BNS alone cannot
answer it.

That choice creates one hard constraint the whole system is built around:
**the two Acts have colliding section numbers.** `BNS s.103` is "Punishment
for murder"; `BNSS s.103` is about searches of a closed place — entirely
unrelated. So **every chunk and every citation carries a `source` field**
(`BNS` or `BNSS`), and the model is forbidden from ever citing a bare
`s.103` — it must say `BNS s.103` or `BNSS s.103`.

---

## Architecture

```
                 ┌─────────────────────── ingest (offline / build time) ───────────────────────┐
  Sources/*.pdf ─►  parser.py ─► sections.json ─► chunker.py ─► chunks.json ─► embed (bge-base) ─► ChromaDB
                 └──────────────────────────────────────────────────────────────────────────────┘
                                                                                         │ (persisted, local)
  user query ──►  FastAPI  POST /chat                                                     ▼
                    │
                    ├─ explicit-section detect  ("BNSS s.187" → fetch + pin)
                    ├─ per-Act dense candidate pools (BNS + BNSS)  ──────────────► ChromaDB similarity
                    ├─ cross-encoder rerank (bge-reranker-base)
                    ├─ diversity cap (≤2 parts/section), keep top-7
                    ├─ build grounded context  ("[BNS s.103 — heading] …")
                    └─ Groq  Llama 3.3 70B  ─► answer + citations + retrieved_sections + no_answer
```

| Layer | Choice | Why |
|---|---|---|
| Backend | Python + FastAPI | Clean async `/chat`, Swagger docs, Docker-friendly |
| Vector DB | ChromaDB, persisted to disk | Open-source, **runs locally**, stores metadata next to vectors |
| Embeddings | `BAAI/bge-base-en-v1.5` (local) | Strong small English retriever; 768-dim |
| Reranker | `BAAI/bge-reranker-base` (local) | Cross-encoder — the real retrieval-quality win |
| LLM | **Llama 3.3 70B** via Groq (`llama-3.3-70b-versatile`) | Open-weight; Groq is very fast |
| Frontend | React + Vite | Lightweight chat UI; deploys as a static site |
| Auth | None | Option B doesn't need it — time spent on retrieval + evals instead |

---

## Quickstart

Prerequisites: **Python 3.11+**, **Node 18+**, and a free
[Groq API key](https://console.groq.com).

```bash
# 1. clone  (backend/, frontend/, Sources/ are at the repo root)
git clone https://github.com/apoorvarastogi00/RAG-Pipeline.git
cd RAG-Pipeline

# 2. install backend deps
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 3. set the Groq key
cp backend/.env.example backend/.env
# edit backend/.env →  GROQ_API_KEY=gsk_...

# 4. build the local vector index (parses chunks.json → embeds → Chroma)
python -m backend.app.ingest
#    creates backend/data/chroma/  (first run also downloads the two models)

# 5. run the backend  (http://127.0.0.1:8000, Swagger at /docs)
python -m uvicorn backend.app.main:app --reload --port 8000

# 6. run the frontend  (in a second terminal)
cd frontend
npm install
cp .env.example .env        # defaults to http://127.0.0.1:8000
npm run dev                 # http://localhost:5173
```

Smoke-test the API directly:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}

curl -s -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is the punishment for murder and how is the trial conducted?"}' \
  | python -m json.tool
```

---

## Chunking strategy & rationale

Legal text has a natural unit — the **section** — so the chunker is
**section-aware** rather than fixed-window:

1. **One chunk per section by default.** A section is a self-contained legal
   unit; splitting it on a blind character window would cut sentences in half
   and scatter a single rule across chunks. ~82% of sections fit in one chunk.
2. **Split only when over budget**, and only on **structural boundaries** —
   top-level sub-clauses `(1) (2)…`, and `Explanation` / `Illustration` /
   `Provided` blocks. Never mid-sentence. Long enumerations (e.g. the 16-item
   Illustrations block under BNS s.303 "Theft") fall back to `(a) (b)…`
   boundaries.
3. **Budget = 1500 characters (~375 tokens).** Comfortably under the
   `bge-base-en-v1.5` 512-token limit even on dense, citation-heavy passages.
4. **Every chunk carries its full lineage** — `source`, `section_number`,
   `marginal_heading`, `chapter`, `chapter_title`, and a `part` index — so a
   split section's pieces are still individually citable and the `source`
   tag travels with the vector into Chroma.

Result: **1162 chunks** (BNS 473, BNSS 689) from 358 + 531 sections.

The tradeoff is deliberate: section-aware chunks are less uniform than
fixed-size chunks, but they preserve legal meaning and citation boundaries.
For this assignment, that matters more than squeezing every passage into the
same token length, because the answer has to cite the exact statutory section
that supports it.

## Retrieval strategy

Two-stage, tuned for the multi-section / cross-document questions this corpus
demands:

- **Explicit-section detection** — if the query names a section
  (`BNS s.103`, `BNSS section 187`, `s. 111`), that exact section is fetched
  by metadata and **pinned** above semantic hits. An unsourced `section 103`
  fetches **both** Acts (collision-safe).
- **Per-Act candidate pools** — dense candidates are pulled separately from
  BNS and BNSS so a cross-document question can't have one Act crowd out the
  other.
- **Cross-encoder reranking** — `bge-reranker-base` re-scores the pooled
  candidates; far more accurate than bi-encoder cosine alone.
- **Diversity cap** — at most 2 parts of the same section in the top-k, so a
  long split section doesn't monopolise the results on a multi-section query.

### Multi-section and cross-document handling

The retriever is designed around two common legal-question shapes:

1. **Multi-section questions within one Act.** Example: *"What is the
   difference between murder and culpable homicide?"* The retriever should
   surface both the murder section and the culpable-homicide section, not just
   the single highest cosine match. The diversity cap is what keeps one long
   section from occupying every context slot.
2. **Cross-document questions across BNS and BNSS.** Example: *"What is the
   punishment for murder and how is the trial conducted?"* The offence lives in
   the BNS; the procedure lives in the BNSS. Pulling candidates separately per
   Act guarantees both documents get a chance before reranking.

This is also why source-qualified citations are mandatory. `BNS s.103` and
`BNSS s.103` are unrelated, so section number alone is not a safe identifier.

---

## Evaluation

`evals/run_evals.py` scores **35 questions** across four categories against
the retriever (`retrieval_proxy` mode measures retrieval hit-rate; `--full`
mode additionally generates answers with Llama 3.3 70B and LLM-judges
correctness). Latest run ([evals/EVAL_RESULTS.md](evals/EVAL_RESULTS.md)):

| Category | Count | Retrieval Hit-Rate | Answer Correctness |
|---|---:|---:|---:|
| easy_lookup | 12 | 83.3% | 83.3% |
| multi_section | 10 | 85.0% | 70.0% |
| cross_document | 7 | 78.6% | 71.4% |
| out_of_scope | 6 | 100.0% | 100.0% |
| **TOTAL** | **35** | **85.7%** | **80.0%** |

Short reflection:

- The strongest result is that the eval now exercises the actual hard cases,
  not just easy single-section lookups: 17 of 35 questions are multi-section or
  cross-document.
- The biggest retrieval misses are precise procedural sections where the user
  asks by concept rather than section number, e.g. undertrial detention
  (`BNSS s.479`) or anticipatory bail (`BNSS s.482`). That suggests the next
  improvement should be lexical/BM25 or marginal-heading boosting alongside
  dense retrieval.
- The cross-document score is lower than easy lookup, but it validates the
  core design choice: without per-Act candidate pools, these questions tend to
  collapse to only BNS or only BNSS context.
- **out_of_scope = 100% in proxy mode**: these rows are labelled as expected
  `NO_ANSWER` cases, including a trap — *"What does Section 379 of the IPC say
  about theft?"*. Run `--full` when Groq quota is available to re-check the
  live model's refusal behaviour.

Run it yourself:

```bash
python evals/run_evals.py            # retrieval-only, no Groq tokens used
python evals/run_evals.py --full     # also generates + LLM-judges (uses Groq)
```

---

## Design decisions

- **Both BNS and BNSS indexed**, with a mandatory `source` tag on every
  chunk and citation — see [Why both documents](#why-both-documents-are-indexed).
  This is the single most important design choice and the reason citations are
  always Act-qualified.
- **ChromaDB, local & persisted** — satisfies "open-source vector DB running
  locally", stores metadata alongside vectors (so `source`-filtered retrieval
  is a one-liner), and persists to `backend/data/chroma/`.
- **Groq + Llama 3.3 70B** — open-weight model (requirement), served fast.
  Temperature 0.1 for faithful, low-variance legal answers.
- **No authentication** — Option B doesn't require it; the time went into
  retrieval quality and the eval harness instead.
- **Index is a rebuildable artifact** — `chunks.json` is committed; the Chroma
  index is gitignored and rebuilt by `ingest.py`. The Docker image bakes it in
  at build time for fast, deterministic cold starts.

---

## Known limitations

- **`no_answer` honesty depends on the LLM.** The prompt forces a `NO_ANSWER`
  sentinel for out-of-corpus questions; it's reliable in testing but is a
  model behaviour, not a hard guarantee.
- **7 of 1162 chunks exceed the embedding model's 512-token window** (long,
  structurally-indivisible sections such as the BNSS s.359 compounding table).
  Their tail content is invisible to retrieval. Listed in `PHASE_2_REPORT.md`.
- **~5% of sections have no `marginal_heading`** — pypdf's two-column gazette
  extraction occasionally strands a heading on the wrong page. Section text is
  unaffected; only that metadata field is blank. Details in `PHASE_1_REPORT.md`.
- **Schedules are not indexed** — both Acts end with tabular schedules that
  need a different (table-aware) parser; excluded for now.
- **Groq free tier ≈ 100k tokens/day (~30 questions)** — a heavy demo session
  or a full `--full` eval run can exhaust it.
- **Backend RAM** — the embedder + reranker + torch need ~1.5 GB resident;
  deploy on a ≥2 GB instance (Render Free/512 MB will OOM).

---

## Project layout

```
Legal Research RAG ChatBot/
├── backend/
│   ├── app/
│   │   ├── parser.py       PDF → sections.json   (Phase 1)
│   │   ├── chunker.py      sections → chunks.json (Phase 2)
│   │   ├── ingest.py       chunks → embeddings → ChromaDB (Phase 3)
│   │   ├── retriever.py    two-stage retrieval + rerank (Phases 4–5)
│   │   ├── generator.py    grounded prompt + Groq call (Phase 4)
│   │   ├── main.py         FastAPI /chat + /health (Phase 4)
│   │   └── config.py       paths, model names, knobs
│   ├── data/               sections.json, chunks.json (chroma/ is gitignored)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               React + Vite chat UI (Phase 7)
├── evals/                  eval_questions.json, run_evals.py, EVAL_RESULTS.md (Phase 6)
├── Sources/                the two source PDFs
├── render.yaml             Render Blueprint (Phase 8)
└── PHASE_0..9_REPORT.md    per-phase implementation notes & manual checks
```

## Deployment

`render.yaml` is a Render Blueprint defining the Dockerised backend (web
service) and the React frontend (static site). `GROQ_API_KEY` is set in the
Render dashboard (never committed). Full steps and caveats in
`PHASE_8_REPORT.md`.

## License

MIT — see [LICENSE](LICENSE).
