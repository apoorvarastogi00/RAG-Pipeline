# Phase 7 Report — React Chat Frontend

**Phase:** 7
**Agent:** Claude Code (plan assigned this to Codex CLI; Apoorva routed it here)
**Scope:** `frontend/` only — **the backend was not touched.** UI codes strictly against the frozen Section 4 contract.
**Stack:** React 18 + Vite 5 (plain JSX, no UI library, no extra runtime deps)
**Commit:** `feat: add React chat interface`

---

## What was built

A single-page chat UI in [frontend/](frontend/):

```
frontend/
├── index.html
├── package.json            react 18, vite 5, @vitejs/plugin-react
├── vite.config.js          dev server on :5173
├── .env.example            VITE_API_BASE_URL=http://127.0.0.1:8000
└── src/
    ├── main.jsx
    ├── api.js              fetch client for POST /chat + GET /health
    ├── styles.css          dark legal-theme styling
    ├── App.jsx             thread state, input, loading, health banner
    └── components/
        ├── Message.jsx     user / assistant / error bubbles
        └── CitationCard.jsx expandable citation
```

### Features (all from the brief)

- **Message thread** — user messages right-aligned, assistant left-aligned,
  auto-scrolls to the newest message.
- **Input box** — submit on Enter or the "Ask" button; disabled while a
  request is in flight.
- **Loading state** — animated three-dot typing indicator in an assistant
  bubble while awaiting the response.
- **Error handling** — any non-2xx or network failure renders a distinct red
  error bubble showing the backend status/detail. Verified live (see below).
- **Citation cards** — each citation is an expandable card. Collapsed it shows
  a colour-coded **BNS**/**BNSS** badge + `s.NUMBER` + marginal heading.
  Expanded it reveals the chapter and the section snippet. (Colour-coding the
  Act badge directly addresses the section-number collision visually.)
- **`no_answer` handling** — when `no_answer: true`, the bubble shows a
  "Not found in the BNS / BNSS corpus" pill and **suppresses the citations
  block** (the retrieved-but-unrelated sections are not presented as support).
- **`retrieved_sections`** — shown in a collapsible "Retrieved N sections"
  disclosure below the answer, as chips with Act badges (transparency into
  what the retriever pulled vs. what the model actually cited).
- **Configurable API base URL** — `VITE_API_BASE_URL` (defaults to
  `http://127.0.0.1:8000`), read in [src/api.js](frontend/src/api.js). The
  same build can point at a deployed backend in Phase 8.
- **Health banner** — calls `GET /health` on load and shows an online/offline
  dot; the composer placeholder changes when the backend is offline.

### Strict contract adherence

[src/api.js](frontend/src/api.js) sends `{ query }` and consumes exactly
`{ answer, citations[], retrieved_sections[], no_answer }`. Every citation is
read as `{ source, section_number, marginal_heading, chapter, snippet }`;
every retrieved section as `{ source, section_number }`. No field outside the
Section 4 contract is referenced.

---

## How it was tested

The backend was running (`uvicorn backend.app.main:app`) and the Vite dev
server was running (`npm run dev`, http://localhost:5173) for all checks.

| # | Check | Result |
|---|---|---|
| 1 | `vite build` compiles | ✅ 34 modules, 0 errors, 147 kB JS (47 kB gzip) |
| 2 | Dev server serves the app | ✅ HTTP 200, correct `<title>`, `main.jsx` served |
| 3 | CORS preflight from `Origin: http://localhost:5173` | ✅ `access-control-allow-origin: *`, methods `GET, POST` |
| 4 | Live cross-origin POST reaches backend | ✅ request hit the handler (proven by the backend traceback) |
| 5 | **Error path** (backend returned HTTP 500) | ✅ `api.js` throws, `App` renders the red error bubble |
| 6 | **Render correctness** of every message shape | ✅ 9/9 server-side-render assertions pass (below) |

### Render-correctness test (browser-free)

I can't drive a real browser headlessly in this environment, so I verified the
React render logic with a server-side-render smoke test: the **real** Message
and CitationCard components were bundled with esbuild and rendered via
`react-dom/server` using the **actual captured Section-4 responses** from
Phases 4–5 (e.g. the cross-document murder+trial answer that cites BNS s.103,
BNS s.104, and BNSS s.248). All assertions passed:

```
PASS  success: answer text
PASS  success: BNS badge
PASS  success: BNSS cross-doc citation s.248
PASS  success: citations label
PASS  success: retrieved sections
PASS  no_answer: shows tag
PASS  no_answer: citations hidden
PASS  user: bubble
PASS  error: bubble + detail
9 passed, 0 failed
```

This confirms the components consume the real API shape and render every
state (success / no_answer / user / error) without runtime errors. The one
thing it does **not** cover is interactive behaviour and visual layout in a
real browser — see manual check #1.

### Note on the live LLM round-trip

During testing the backend began returning **HTTP 500** because the **Groq
free-tier daily token cap was hit** (`429 ... tokens per day (TPD): Limit
100000, Used 97149` — consumed by the Phase 4/5 test queries). This is an
external quota, not a frontend or backend bug, and it actually exercised the
frontend's error path (check #5). A fresh end-to-end answer in the browser
needs the daily quota to reset (Groq resets TPD daily) or a higher-tier key.

---

## Manual checks for Apoorva

1. **Visual + interactive browser check (the one I couldn't do).** Once the
   Groq quota has reset:
   ```bash
   # terminal 1 — backend
   cd "Legal Research RAG ChatBot"
   .venv/bin/python -m uvicorn backend.app.main:app --port 8000

   # terminal 2 — frontend
   cd "Legal Research RAG ChatBot/frontend"
   cp .env.example .env        # optional; defaults to 127.0.0.1:8000
   npm install                 # first time only
   npm run dev                 # opens http://localhost:5173
   ```
   In the browser, confirm: a suggestion chip sends a query; the typing
   indicator shows; the answer renders; citation cards expand/collapse;
   BNS vs BNSS badges are colour-distinct; the "Retrieved N sections"
   disclosure works.
2. **Test the UI WITHOUT spending Groq tokens** (handy while rate-limited).
   Point the frontend at a 12-line mock that replays a real response:
   ```bash
   # save as /tmp/mock_backend.py, then: python /tmp/mock_backend.py
   from http.server import BaseHTTPRequestHandler, HTTPServer
   import json
   RESP = json.load(open("/tmp/phase5/cross1.json"))  # a real Section-4 response
   class H(BaseHTTPRequestHandler):
       def _send(self, body):
           self.send_response(200)
           self.send_header("Content-Type", "application/json")
           self.send_header("Access-Control-Allow-Origin", "*")
           self.send_header("Access-Control-Allow-Methods", "GET, POST")
           self.send_header("Access-Control-Allow-Headers", "content-type")
           self.end_headers(); self.wfile.write(json.dumps(body).encode())
       def do_OPTIONS(self): self._send({})
       def do_GET(self): self._send({"status": "ok"})
       def do_POST(self): self._send(RESP)
   HTTPServer(("127.0.0.1", 8000), H).serve_forever()
   ```
   (If `/tmp/phase5/cross1.json` is gone, any object matching the Section 4
   shape works.) This lets you exercise the full UI render path offline.
3. **`no_answer` styling** — ask something out of corpus (e.g. "Who won the
   2022 World Cup?"). Confirm the amber "Not found in the BNS / BNSS corpus"
   pill appears and **no citation cards** are shown.
4. **Backend-offline behaviour** — stop the backend, reload the page. The
   header dot should turn red ("backend offline") and the composer should
   show the offline placeholder; sending should produce the error bubble.
5. **Deployed base URL (Phase 8)** — set `VITE_API_BASE_URL` to the Render
   backend URL before `npm run build`; the static bundle will target it. No
   code change needed.
6. **Heads-up unrelated to the frontend: Groq daily token budget.** The
   free-tier TPD limit (100k) was nearly exhausted by phase testing. Phase 6
   (eval harness, ~35 questions) will need substantially more than that in a
   single run — budget for a quota reset, a paid Groq tier, or running the
   evals in batches across days.
