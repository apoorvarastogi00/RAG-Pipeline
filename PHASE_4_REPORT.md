# Phase 4 Report — Retrieval + Generation Endpoint

**Phase:** 4
**Agent:** Claude Code
**Modules:** [backend/app/retriever.py](backend/app/retriever.py), [backend/app/generator.py](backend/app/generator.py), [backend/app/main.py](backend/app/main.py)
**LLM:** Llama 3.3 70B via Groq (`llama-3.3-70b-versatile`)
**Run locally:** `.venv/bin/python -m uvicorn backend.app.main:app --port 7860`
**Swagger UI:** http://127.0.0.1:7860/docs
**Commit:** `feat: add retrieval and generation endpoint`

---

## > THE API CONTRACT IS NOW FROZEN <

Phase 7 (frontend, Codex CLI) codes against the response shape below. Do
not change field names, casing, or types without coordinating with the
frontend agent.

### `POST /chat`

**Request**
```json
{ "query": "string (1..2000 chars)" }
```

**Response**
```json
{
  "answer": "string — grounded answer, with inline 'BNS s.NUMBER' / 'BNSS s.NUMBER' citations",
  "citations": [
    {
      "source":           "BNS" | "BNSS",
      "section_number":   "103",
      "marginal_heading": "Punishment for murder",
      "chapter":          "Chapter VI",
      "snippet":          "300-char preview of the cited section's text…"
    }
  ],
  "retrieved_sections": [
    { "source": "BNS",  "section_number": "103" },
    { "source": "BNSS", "section_number": "187" }
  ],
  "no_answer": false
}
```

### `GET /health`

```json
{ "status": "ok" }
```

### Frozen invariants

- Every `citations[i].source` is exactly `"BNS"` or `"BNSS"` (uppercase).
- Every `retrieved_sections[i]` has both fields populated; deduplicated by
  `(source, section_number)` in retrieval-distance order.
- `citations` is the subset of retrieved sections the model actually cited,
  in citation order. May be empty.
- `no_answer = true` iff the model produced the literal first-line sentinel
  `NO_ANSWER`. A stray mid-answer `NO_ANSWER` (partial-answer case) is
  stripped from `answer` but leaves the flag `false`.

---

## Architecture

```
HTTP /chat ─▶ Retriever.search(query, k=5)
                │  - encode query with BGE s2p instruction
                │  - cosine search over Chroma (legal_sections, 1162 chunks)
                ▼
              build_context(chunks)
                │  - one block per chunk, prefixed:
                │    "[BNS s.103 — Punishment for murder; Chapter VI]"
                ▼
              call_groq(system, user)
                │  - Llama 3.3 70B via Groq
                │  - temperature 0.1, max_tokens 1024
                ▼
              parse_answer(raw)
                │  - splits off NO_ANSWER sentinel
                │  - strips stray mid-answer NO_ANSWER lines
                ▼
              extract_cited(answer)  → list[(source, section_number)]
                ▼
              ChatResponse  ─▶ HTTP 200
```

The Groq key is read once at startup via `python-dotenv` from
`backend/.env`. It is never logged and never returned to the client.

## Prompt design (the rules baked into `SYSTEM_PROMPT`)

1. Answer ONLY from the provided context — no IPC / CrPC fall-back.
2. Cite EVERY reference as `BNS s.NUMBER` or `BNSS s.NUMBER`. Bare
   `section 103` / `s.103` is forbidden because of the BNS/BNSS s.103
   collision (proven by the source-disambiguation check in
   [PHASE_3_REPORT.md](PHASE_3_REPORT.md)).
3. Be concise; quote short phrases when useful; never invent durations,
   fines, or punishments not in the context.
4. If the question is unanswerable from the corpus, respond with EXACTLY:
   ```
   NO_ANSWER
   <one sentence stating what's missing>
   ```

---

## Live test — three questions through `POST /chat`

All three ran against the actual running server with the real Groq backend.
Server start-up: ~2 s. Per-query latency: ~1–2 s on a warm process.

### Q1 (BNS) — "What is the punishment for murder under the BNS?"

```json
{
    "answer": "The punishment for murder under the BNS is stated in BNS s.103, which provides that whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine. Additionally, BNS s.104 specifies that if the person committing murder is already under sentence of imprisonment for life, they shall be punished with death or with imprisonment for life, which shall mean the remainder of that person's natural life, as per BNS s.104. Furthermore, BNS s.103(2) outlines a specific scenario where a group of five or more persons acting in concert commits murder on certain grounds, and each member of such group shall be punished with death or with imprisonment for life, and shall also be liable to fine, as stated in BNS s.103(2).",
    "citations": [
        { "source": "BNS", "section_number": "103", "marginal_heading": "Punishment for murder",            "chapter": "Chapter VI", "snippet": "103.(1) Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine. (2) When a group of five or more persons acting in concert commits murder on the ground of race, caste or community, sex, place of birth, language, personal belief or any other similar ground each mem…" },
        { "source": "BNS", "section_number": "104", "marginal_heading": "Punishment for murder by life-convict", "chapter": "Chapter VI", "snippet": "104.Whoever, being under sentence of imprisonment for life, commits murder, shall be punished with death or with imprisonment for life, which shall mean the remainder of that person's natural life." }
    ],
    "retrieved_sections": [
        { "source": "BNS",  "section_number": "104" },
        { "source": "BNS",  "section_number": "103" },
        { "source": "BNS",  "section_number": "110" },
        { "source": "BNSS", "section_number": "470" },
        { "source": "BNS",  "section_number": "108" }
    ],
    "no_answer": false
}
```

✅ Cites `BNS s.103` and `BNS s.104` correctly (never bare). The answer
captures both the base offence and the life-convict variant.

### Q2 (BNSS) — "What is the procedure when investigation cannot be completed in 24 hours?"

```json
{
    "answer": "When an investigation cannot be completed in 24 hours, the officer in charge of the police station or the police officer making the investigation, if he is not below the rank of sub-inspector, shall forthwith transmit to the nearest Magistrate a copy of the entries in the diary relating to the case, and shall at the same time forward the accused to such Magistrate, as per BNSS s.187 (1). The Magistrate to whom an accused person is forwarded under this section may authorise the detention of the accused in such custody as such Magistrate thinks fit, for a term not exceeding fifteen days in the whole, or in parts, at any time during the initial forty days or sixty days out of detention period of sixty days or ninety days, as provided in BNSS s.187 (2). If a Magistrate is not available, the officer in charge of the police station or the police officer making the investigation may transmit to the nearest Executive Magistrate a copy of the entry in the diary relating to the case, and shall, at the same time, forward the accused to such Executive Magistrate, as per BNSS s.187 (6). The Executive Magistrate may authorise the detention of the accused person in such custody as he may think fit for a term not exceeding seven days in the aggregate, as per BNSS s.187 (6).",
    "citations": [
        { "source": "BNSS", "section_number": "187", "marginal_heading": "Procedure when investigation cannot be completed in twenty-four hours", "chapter": "Chapter XIII", "snippet": "(10) Where any order stopping further investigation into an offence has been made under sub-section (9), the Sessions Judge may, if he is satisfied, on an application made to him or otherwise, that further investigation into the offence ought to be made, vacate the order made under sub-section ( 9) and direct further i…" }
    ],
    "retrieved_sections": [
        { "source": "BNSS", "section_number": "187" }
    ],
    "no_answer": false
}
```

✅ All five retrieved chunks came from `BNSS s.187` (different parts —
exactly what was expected for a long, sub-clause-rich procedural section).
Citation correctly uses the `BNSS s.NUMBER` form.

### Q3 (cross-document) — "What is the punishment for murder and how is the trial conducted?"

```json
{
    "answer": "The punishment for murder is stated in BNS s.103, which provides that whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine. Additionally, BNS s.104 provides a specific punishment for murder by a life-convict, which is death or imprisonment for life, meaning the remainder of that person's natural life. \n\nHowever, the context does not provide information on how the trial for murder is conducted. \n\nThe context is missing information on the procedure for conducting a trial, which would be found in the Bharatiya Nagarik Suraksha Sanhita (BNSS), but the provided context only includes sections from the Bharatiya Nyaya Sanhita (BNS).",
    "citations": [
        { "source": "BNS", "section_number": "103", "marginal_heading": "Punishment for murder",            "chapter": "Chapter VI", "snippet": "103.(1) Whoever commits murder shall be punished…" },
        { "source": "BNS", "section_number": "104", "marginal_heading": "Punishment for murder by life-convict", "chapter": "Chapter VI", "snippet": "104.Whoever, being under sentence of imprisonment for life, commits murder…" }
    ],
    "retrieved_sections": [
        { "source": "BNS", "section_number": "104" },
        { "source": "BNS", "section_number": "103" },
        { "source": "BNS", "section_number": "105" },
        { "source": "BNS", "section_number": "110" },
        { "source": "BNS", "section_number": "109" }
    ],
    "no_answer": false
}
```

⚠️ **Phase 5 work item, surfaced cleanly here.** The retriever returned
five BNS chunks for a cross-document question that ALSO needs BNSS trial
procedure. The model honestly answered the half it had context for and
flagged the rest as missing — `no_answer=false` because a real partial
answer was given. Phase 5's reranker + explicit multi-document retrieval
will fix this by deliberately fetching from BOTH Acts when the query has
two angles.

### Bonus — true `no_answer=true` path (sanity check, not one of the 3)

Query: `"What is the capital of France?"`

```json
{
  "no_answer": true,
  "answer": "The context provided does not contain any information about the capital of France, as it only includes sections from the Bharatiya Nyaya Sanhita (BNS) and Bharatiya Nagarik Suraksha Sanhita (BNSS)…",
  …
}
```

`NO_ANSWER` sentinel triggers `no_answer=true`, the sentinel itself is
stripped from `answer`. The frontend should hide / dim `citations` when
this flag is set (they're the retrieved-but-unrelated sections).

---

## Manual checks for Apoorva

1. **Start the server, then open Swagger UI.**
   ```bash
   cd "Legal Research RAG ChatBot"
   .venv/bin/python -m uvicorn backend.app.main:app --port 7860
   # open http://127.0.0.1:7860/docs
   ```
   Hit `POST /chat` from the "Try it out" panel with each of the three
   queries above and confirm the response keys match the frozen contract.
2. **Confirm the section-103 disambiguation works through the API.** Use
   Swagger or curl:
   ```bash
   curl -s -X POST http://127.0.0.1:7860/chat \
     -H 'Content-Type: application/json' \
     -d '{"query":"What does section 103 of the BNSS say?"}' \
     | python -m json.tool | head -30
   ```
   Expect citations to refer to `BNSS s.103` ("Persons in charge of closed
   place to allow search"), NOT BNS s.103 ("Punishment for murder").
3. **Try a clearly out-of-corpus question.** Anything not Indian criminal
   law (e.g. "Who won the FIFA World Cup in 2022?"). Expect:
   - `no_answer: true`
   - `answer` doesn't contain the literal token `NO_ANSWER`
   - `citations` may be non-empty (model name-dropped retrieved-but-
     unrelated sections); the frontend should suppress them.
4. **Frontend agent: code against the response shape, not the raw text.**
   Every citation has all five keys; every retrieved-section has both.
   No nullable fields. Empty strings are valid (e.g.
   `marginal_heading: ""` for the ~5% of sections where Phase 1 couldn't
   recover the heading).
5. **Known Phase 5 work items surfaced here:**
   - Cross-document queries currently retrieve from whichever Act the
     query semantically resembles most, not both. Phase 5 should detect
     two-angle queries and fan out to BNS + BNSS independently before
     combining results.
   - When the query says "section 103" explicitly, we should fetch
     directly by metadata (`where={"section_number": "103"}`) before
     resorting to dense similarity. Plan calls this "explicit-section
     detection".
   - The bge-base retriever sometimes ranks `BNS s.304 (Snatching)` above
     `BNS s.303 (Theft)` for the query "punishment for theft" — a
     cross-encoder reranker (`BAAI/bge-reranker-base`) will reorder this.

6. **CORS** is currently `allow_origins=["*"]` for the Vite dev server in
   Phase 7. Tighten to a specific origin in Phase 8 before deploying.

7. **Latency** on warm process: ~1–2 s per query, dominated by the Groq
   call. The retriever + embedder add ~50 ms. Cold start (loading bge
   weights into memory) is ~1 s extra; the lifespan hook does this once at
   startup so the first user request is already warm.
