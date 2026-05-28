# Phase 0 Report — Repo Scaffold

**Phase:** 0 (Repo scaffold)
**Agent:** Claude Code
**Working dir:** `/Users/apoorvarastogi/Desktop/Project Task/Legal Research RAG ChatBot`
**Commit:** `chore: scaffold repo structure` (root commit on `main`)

---

## What was created

### Folders
- `backend/`
- `backend/app/` (contains `.gitkeep`)
- `backend/data/` (created on disk; not tracked because contents are gitignored)
- `backend/data/chroma/` (created on disk; gitignored — index artifact)
- `frontend/`
- `frontend/src/` (contains `.gitkeep`)
- `evals/` (contains `.gitkeep`)

### Files
- `.gitignore` — ignores `.env`, `backend/data/chroma/`, `node_modules/`, `__pycache__/`, `*.pyc` (+ `*.pyo/*.pyd`), `.DS_Store`, plus `.venv/`, `venv/`, `.vscode/`, `.idea/`, `*.egg-info/`.
- `LICENSE` — MIT, Copyright (c) 2026 Apoorva Rastogi.
- `README.md` — stub describing the project, the both-documents indexing rationale, planned stack, and a placeholder setup section.
- `backend/requirements.txt` — `fastapi`, `uvicorn[standard]`, `python-dotenv`, `pydantic`, `pydantic-settings`, `pypdf`, `sentence-transformers`, `torch`, `chromadb`, `groq`, `tqdm`, `numpy`. Unpinned — pin in Phase 8 alongside the Dockerfile.
- `backend/.env.example` — single line `GROQ_API_KEY=`.
- `backend/app/.gitkeep`, `frontend/src/.gitkeep`, `evals/.gitkeep` — keep the otherwise-empty folders tracked in git.

### Git
- Initialised on branch `main`.
- Local `user.email` / `user.name` set to `apoorva.rastogi004@gmail.com` / `Apoorva Rastogi` (repo-local only — global git config not touched).
- First commit: `chore: scaffold repo structure` (root commit, 10 files).

---

## Plan items deferred to later phases (intentionally not created now)

These are listed in PROJECT_PLAN.md Section 2 but belong to later phases — creating empty stubs now would be dead code:

- `backend/app/main.py`, `parser.py`, `chunker.py`, `ingest.py`, `retriever.py`, `generator.py`, `config.py` → Phases 1–4.
- `backend/data/sections.json`, `chunks.json` → outputs of Phases 1–2.
- `backend/Dockerfile`, `render.yaml` → Phase 8.
- `frontend/package.json` and React source → Phase 7 (Codex CLI).
- `evals/eval_questions.json`, `run_evals.py`, `EVAL_RESULTS.md` → Phase 6.

---

## Manual checks for Apoorva

1. **PDFs are in `Sources/`, not at the repo root.**
   PROJECT_PLAN.md Section 2 shows both PDFs at the repo root (`Legal Research RAG ChatBot/250883_english_01042024.pdf`, `…/250884_2_english_01042024.pdf`). They currently live in `Sources/`. Before Phase 1, decide one of:
   - Move them to the repo root to match the plan: `mv Sources/*.pdf . && rmdir Sources` (and update the next commit), or
   - Keep them in `Sources/` and update `config.py` paths in Phase 3 accordingly.
   I left them in `Sources/` (and committed them there) so as not to take a destructive action without confirmation.

2. **GitHub repo — you create it.**
   I did not create the remote, per your instruction. When ready:
   ```bash
   cd "/Users/apoorvarastogi/Desktop/Project Task/Legal Research RAG ChatBot"
   gh repo create <name> --public --source=. --remote=origin --push
   # or: git remote add origin <url> && git push -u origin main
   ```

3. **Agent prompt files (`claude.md`, `gemini.md`, `codex.md`).**
   PROJECT_PLAN.md Section 2 lists these inside the repo, but the actual files currently live one directory up (`/Users/apoorvarastogi/Desktop/Project Task/`). Not in scope for Phase 0; decide later whether to copy them into the repo or keep them external.

4. **PROJECT_PLAN.md not inside the repo.**
   The plan also lists `PROJECT_PLAN.md` at the repo root. The file currently lives at `/Users/apoorvarastogi/Desktop/Project Task/Project_Plan.md` (note the lowercase `lan`). Consider copying it into the repo as `PROJECT_PLAN.md` so the public GitHub repo carries the plan reviewers will need.

5. **`.DS_Store` files** are present on disk in the repo and in `Sources/`. They are correctly gitignored — verify with `git status` (should show clean).

6. **`requirements.txt` is unpinned.** I left versions unpinned to avoid guessing. Phase 8 (Dockerfile/deploy) should pin them with a `pip freeze` from a working venv.

7. **First commit is a root commit.** Verify with `git log --oneline` — expect a single line: `chore: scaffold repo structure`.

8. **No application logic was written.** As instructed. Stopping here.

---

## Final submission update — 2026-05-28

The originally scaffolded repo now has all planned phases implemented,
deployed, and documented. Live frontend:
https://rag-pipeline-silk.vercel.app. Live backend:
https://apoorvarastogi-legal-rag-bns-backend.hf.space. Demo video:
[demo/legal-rag-demo.webm](demo/legal-rag-demo.webm).
