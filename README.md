# Legal Research RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot answering questions about Indian
criminal law, indexing **both**:

- **Bharatiya Nyaya Sanhita (BNS), 2023** — the new criminal code (replaces IPC).
- **Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023** — the new criminal procedure
  code (replaces CrPC).

Both documents are indexed deliberately: the assignment names the BNS, and the
BNSS is included because offences (BNS) and procedure (BNSS) are inseparable —
procedure questions cannot be answered from the BNS alone. Every chunk and every
citation carries a `source` field (`BNS` or `BNSS`) because section numbers
collide across the two documents (e.g. BNS s.103 and BNSS s.103 are unrelated).

## Status

Implemented through **Phase 5**:

- PDF parsing for BNS and BNSS.
- Section-aware chunking with source-safe citations.
- Local Chroma vector index build pipeline.
- FastAPI `/chat` endpoint backed by Groq.
- Phase 5 retrieval quality upgrades: explicit section detection, per-Act
  candidate pools, cross-encoder reranking, and multi-section diversity.

See `PHASE_0_REPORT.md` through `PHASE_5_REPORT.md` for the phase-by-phase
implementation notes.

## Stack

| Layer | Choice |
|---|---|
| Backend | Python + FastAPI |
| Vector DB | ChromaDB (local, persisted) |
| Embeddings | `BAAI/bge-base-en-v1.5` |
| Reranker | `BAAI/bge-reranker-base` |
| LLM | Llama 3.3 70B via Groq |
| Frontend | Placeholder only; not implemented yet |
| Deployment | Planned |

## Setup

Use Python 3.11+ from the repository root.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cp backend/.env.example backend/.env
# edit backend/.env and set GROQ_API_KEY
```

The first ingest/server run downloads the embedding and reranker models from
Hugging Face through `sentence-transformers`.

## Build the local index

The repo includes parsed `sections.json` and `chunks.json`; the Chroma index is
ignored because it is a rebuildable local artifact.

```bash
python -m backend.app.ingest
```

This creates `backend/data/chroma/`.

## Run the API

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

Useful checks:

```bash
curl http://127.0.0.1:8000/health

curl -s -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"query":"Explain BNSS s. 187"}' | python -m json.tool
```

Open `http://127.0.0.1:8000/docs` for the Swagger UI.

## Phase 5 retrieval smoke test

```bash
python - <<'PY'
from backend.app.retriever import Retriever

r = Retriever()
for c in r.search("Explain BNSS s. 187", k=7):
    tag = "*" if c.forced else " "
    print(f"{tag}{c.source} s.{c.section_number} part {c.part} rerank={c.rerank_score}")
PY
```

Expected result: `BNSS s.187` appears at the top with `*`, proving explicit
section detection and wrong-Act collision handling are active.

## Notes for public replication

- A valid `GROQ_API_KEY` is required for `/chat`.
- Internet access is required on first install/model download.
- The checked-in PDFs under `Sources/` are the source documents used to
  regenerate `sections.json`, `chunks.json`, and the local Chroma index.
- `backend/data/chroma/`, `.env`, virtual environments, and editor/system files
  are intentionally ignored.
