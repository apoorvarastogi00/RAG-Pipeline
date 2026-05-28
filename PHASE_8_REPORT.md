# Phase 8 Report — Deployment Config

**Phase:** 8
**Agent:** Claude Code (plan assigned this to Gemini CLI; Apoorva routed it here)
**Scope:** deployment config only — **no RAG logic modified.**
**Files added:** [backend/Dockerfile](backend/Dockerfile), [render.yaml](render.yaml), [.dockerignore](.dockerignore)
**Commit:** `chore: add Docker and Render deployment config`
**Live URL:** not deployed by me (no access to Apoorva's Render account) — deploy steps below.

---

## Index strategy — DECISION

**Build the Chroma index at Docker image-build time from the committed
`chunks.json` (no PDF re-parse, no runtime embedding).**

The Dockerfile runs, as a build step:

```dockerfile
RUN python -m backend.app.ingest \
    && python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-base')"
```

`ingest` is idempotent: because `backend/data/chunks.json` (1.2 MB) and
`sections.json` are committed, it reads them directly and embeds the 1162
chunks into `backend/data/chroma/` — it does **not** re-parse the PDFs. The
second line warms the cross-encoder cache. Both model downloads happen once,
at build time, and are baked into the image.

### Why this over the alternatives

| Option | Verdict |
|---|---|
| **Bake index at build from `chunks.json`** ✅ chosen | Deterministic (chunks.json is version-controlled), no fragile PDF parsing at deploy, **zero** model downloads or embedding at container start → fast, stable cold starts. Render spins idle instances down; this avoids re-embedding on every wake. |
| Embed on startup (run `ingest` in entrypoint) | Rejected: every cold start would re-embed (~15 s) and the very first start downloads ~720 MB of model weights → slow, flaky wakes on a spin-down tier. |
| Re-parse PDFs on deploy | Rejected: the parser is the most complex/fragile step (gazette layout quirks). No reason to run it at deploy when `chunks.json` is already committed and reviewed. |
| Commit the Chroma index itself | Rejected: it's a rebuildable binary artifact (stays gitignored). Baking it in the image at build time gives the same startup speed without bloating git history. |

Trade-off accepted: a longer image build (~2–3 min: CPU torch + two model
downloads + embedding) in exchange for fast, predictable runtime.

Verified locally (Docker not installed here, so via the Python that the
build would run):
- `chunks.json` present (1,229,399 bytes) → `ingest` reads it, no PDF re-parse.
- `ingest.py` references no Groq client → safe to run at build with **no**
  `GROQ_API_KEY`.

---

## What each file does

### [backend/Dockerfile](backend/Dockerfile)
- Base `python:3.11-slim`.
- Installs **CPU-only torch** first (from the PyTorch CPU wheel index) so the
  later `-r requirements.txt` sees torch satisfied and never pulls the
  multi-GB CUDA build.
- Copies the `backend` package (code + committed `data/*.json`) and `Sources/`.
- Builds the index + warms both model caches (above).
- Listens on Render's injected `$PORT` (defaults to 7860 locally):
  `uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-7860}`.
- **Build context is the repo root** (`docker build -f backend/Dockerfile .`)
  so the `backend.app.*` package path resolves — `render.yaml` sets
  `dockerContext: .` to match.

### [render.yaml](render.yaml)
- **Backend** — `type: web`, `runtime: docker`, `dockerfilePath:
  ./backend/Dockerfile`, `dockerContext: .`, `healthCheckPath: /health`.
  `plan: standard` (see RAM note). `GROQ_API_KEY` declared with `sync: false`
  → **never in the repo**, set in the Render dashboard.
- **Frontend** — `type: web`, `runtime: static`, `rootDir: frontend`,
  `buildCommand: npm install && npm run build`, `staticPublishPath: dist`,
  with an SPA rewrite (`/* → /index.html`). `VITE_API_BASE_URL` is set to the
  backend's public URL and **baked into the static bundle at build time**.

  Verified: a build with `VITE_API_BASE_URL=https://legal-rag-backend.onrender.com`
  produces a bundle containing that URL — i.e. Vite reads it from the process
  env exactly as Render supplies it. So the deployed frontend will call the
  deployed backend, not localhost.

### [.dockerignore](.dockerignore)
Keeps the build context small/clean: excludes `.git`, `.venv`,
`node_modules`, `__pycache__`, `frontend/dist`, the rebuildable
`backend/data/chroma/`, and `backend/.env` (so the local secret can never be
baked into an image).

---

## Deployment steps (for Apoorva)

1. **Push** this branch to GitHub (already the origin).
2. In Render: **New + → Blueprint**, select the `RAG-Pipeline` repo. Render
   reads `render.yaml` and proposes the two services.
3. **Set the backend secret**: on `legal-rag-backend` → Environment, add
   `GROQ_API_KEY = <your key>`. (It's `sync: false`, so Render prompts for it
   and never stores it in git.)
4. **Confirm the backend plan** is Standard (2 GB) or larger — see RAM note.
5. **Apply** the blueprint. The backend image builds (~2–3 min), the frontend
   builds as a static site.
6. **If you rename the backend service** (or use a custom domain), update
   `VITE_API_BASE_URL` in `render.yaml` to the new backend URL and redeploy
   the frontend (the URL is baked at build time).
7. Smoke-test the live URLs (see manual checks).

To build/run the backend image locally once Docker is installed:
```bash
docker build -f backend/Dockerfile -t legal-rag-backend .
docker run -p 7860:7860 -e GROQ_API_KEY=sk_... legal-rag-backend
curl localhost:7860/health
```

---

## Manual checks for Apoorva

1. **RAM sizing (most important).** The embedding model + cross-encoder
   reranker + torch hold ~1.5 GB resident. Render **Free/Starter (512 MB)
   will OOM-kill** the backend. Use **Standard (2 GB)** — already set as
   `plan: standard`. If cost matters, uncomment `USE_RERANKER=false` in
   `render.yaml` (drops the reranker, ~0.5 GB saved) — but it still needs
   ~1 GB, so Free is not viable either way. Decide the plan before applying.
2. **First-request latency / spin-down.** On non-always-on plans the instance
   sleeps when idle; the first request after a wake takes a few seconds to
   load the two models from the baked cache (no download, just load). Answer
   latency is then ~3–4 s (dominated by the Groq call). Consider an always-on
   plan if you want zero cold starts during the review.
3. **GROQ token budget.** The free Groq tier is 100k tokens/day; each `/chat`
   uses ~3 k. That's ~30 questions/day. The reviewer hitting the live demo
   could exhaust it — consider a paid Groq tier for the demo window. (This is
   the same quota that 500'd a request during Phase 7 testing.)
4. **CORS.** The backend currently sends `Access-Control-Allow-Origin: *`
   (set in Phase 4). That works for the deployed frontend as-is. If you want
   to lock it down to just the frontend origin, that's a one-line change in
   `backend/app/main.py` — I left it untouched per "do not modify RAG logic",
   but flag if you'd like it tightened before going public.
5. **Dependency pinning (recommended, not done).** `requirements.txt` is
   unpinned, so a Render rebuild months from now could pull a newer
   `sentence-transformers`/`chromadb` that behaves differently. Before a
   long-lived deploy, pin from the working venv:
   ```bash
   .venv/bin/pip freeze > backend/requirements.lock.txt
   # then point the Dockerfile at requirements.lock.txt
   ```
   I did not do this automatically to avoid silently changing resolved
   versions — your call.
6. **Verify the live deploy** once applied:
   ```bash
   curl https://legal-rag-backend.onrender.com/health           # {"status":"ok"}
   curl -s -X POST https://legal-rag-backend.onrender.com/chat \
     -H 'Content-Type: application/json' \
     -d '{"query":"Explain BNSS s. 187"}' | python -m json.tool
   ```
   Then open the frontend URL and confirm it talks to the backend (network
   tab shows requests to the onrender backend host, not localhost).
7. **Docker was not installed in my environment**, so I validated the config
   statically (YAML structure, build-time ingest assumptions, Vite env
   baking) but did **not** run an actual `docker build`. Recommend you run the
   local `docker build` once (command above) before applying the blueprint,
   to catch any environment-specific surprise early.

---

## Final submission update — 2026-05-28

Deployment moved from the planned Render path to a working split deployment:
frontend on Vercel and backend on Hugging Face Spaces. `GROQ_API_KEY` is stored
as a Hugging Face secret and is not committed to GitHub.
