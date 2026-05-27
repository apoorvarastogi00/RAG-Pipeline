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

Scaffold only (Phase 0). Implementation is incoming — see `PROJECT_PLAN.md` for
the full phased plan.

## Stack (planned)

| Layer | Choice |
|---|---|
| Backend | Python + FastAPI |
| Vector DB | ChromaDB (local, persisted) |
| Embeddings | `BAAI/bge-base-en-v1.5` |
| Reranker | `BAAI/bge-reranker-base` |
| LLM | Llama 3.3 70B via Groq |
| Frontend | React + Vite |
| Deployment | Render |

## Setup

Setup instructions will be added once the backend and frontend land. For now:

```bash
cp backend/.env.example backend/.env
# fill in GROQ_API_KEY
```
