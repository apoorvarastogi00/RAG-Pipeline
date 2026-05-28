# Phase 6 Report — Eval Harness

**Phase:** 6
**Agent:** Claude Code
**Dataset assist:** Gemini CLI draft, corrected and wired by Claude Code
**Files:** [evals/eval_questions.json](evals/eval_questions.json), [evals/run_evals.py](evals/run_evals.py), [evals/EVAL_RESULTS.md](evals/EVAL_RESULTS.md)
**Commit:** `test: add evaluation harness`

---

## What changed

Phase 6 adds a repeatable evaluation harness for the Phase 5 retriever.

The dataset has **35 questions**, matching the plan:

| Category | Count | Purpose |
|---|---:|---|
| `easy_lookup` | 12 | Single-section statutory lookups |
| `multi_section` | 10 | Questions requiring more than one section |
| `cross_document` | 7 | Questions requiring both BNS and BNSS |
| `out_of_scope` | 6 | Non-corpus and adversarial questions |

Each entry has:

```json
{
  "question": "...",
  "expected_sections": [{"source": "BNS", "section_number": "103"}],
  "reference_answer": "...",
  "category": "easy_lookup"
}
```

`evals/run_evals.py` reports:

1. **Retrieval hit-rate** — fraction of expected sections present in top-k.
2. **Answer correctness** — default local proxy: all expected sections must be
   present for answerable questions; out-of-scope questions expect no sections.
3. **Optional full mode** — `--full` calls Groq for answer generation and an
   LLM judge against `reference_answer`.

Default mode is intentionally local because Groq quota/rate limits should not
block a basic eval run. The full mode remains available:

```bash
.venv/bin/python evals/run_evals.py --full
```

During this phase, the full Groq run was attempted and reached question 21
before Groq returned a `429` daily token limit for `llama-3.3-70b-versatile`.
The saved result file therefore uses the completed local `retrieval_proxy`
mode.

---

## Metrics summary

Saved in [evals/EVAL_RESULTS.md](evals/EVAL_RESULTS.md).

| Category | Count | Retrieval Hit-Rate | Answer Correctness |
|---|---:|---:|---:|
| easy_lookup | 12 | 83.3% | 83.3% |
| multi_section | 10 | 85.0% | 70.0% |
| cross_document | 7 | 78.6% | 71.4% |
| out_of_scope | 6 | 100.0% | 100.0% |
| **TOTAL** | **35** | **85.7%** | **80.0%** |

Interpretation:

- Phase 5 retrieval is strong on common criminal-law lookups and many
  multi-section/cross-document questions.
- The failures are mostly precise procedural headings where the query wording
  does not contain a section number and the dense/reranker stack prefers nearby
  concepts.
- Out-of-scope rows are marked correct in the default proxy mode because the
  dataset expects `NO_ANSWER`; the actual refusal behavior should be checked in
  `--full` mode when Groq quota is available.

---

## Manual checks for Apoorva

Check these by hand because they are the weakest retrieval rows:

1. **BNSS s.479 undertrial detention** — query:
   "What is the maximum period an undertrial prisoner can be detained?"
   Retrieved 0% of expected sections. Consider adding heading-aware keyword
   boosting for exact marginal-heading matches.
2. **BNSS s.43 arrest how made** — query:
   "How is an arrest made according to the Sanhita?"
   Retrieved nearby arrest sections but missed the exact "Arrest how made"
   section.
3. **BNSS s.285 summary trials** — query:
   "Explain the difference between summary trials by a second-class Magistrate
   and the general procedure for summary trials."
   Retrieved BNSS s.284 but missed BNSS s.285.
4. **BNSS s.483 special bail powers** — query:
   "Can a person be released on bail for a non-bailable offence, and what are
   the special powers of the High Court?"
   Retrieved BNSS s.480 but missed BNSS s.483.
5. **BNSS s.482 anticipatory bail** — query:
   "How is bail dealt with when the person apprehends arrest, and can a bail
   bond be cancelled?"
   Retrieved BNSS s.492 but missed BNSS s.482.
6. **BNSS s.38 advocate during interrogation** — cross-document query with
   BNS s.140. Retrieved BNS s.140 but missed the procedural right.
7. **BNS s.259 / BNSS s.206 trial contrary to law** — cross-document query.
   Retrieved nearby trial/procedure sections but missed both expected sections.

Also rerun one or two out-of-scope questions through `/chat` when Groq quota is
available, especially the IPC adversarial row:

```bash
curl -s -X POST http://127.0.0.1:7860/chat \
  -H 'Content-Type: application/json' \
  -d '{"query":"What does Section 379 of the IPC say about theft?"}' \
  | python -m json.tool
```

Expected behavior: the model should refuse older IPC-specific questions unless
the answer is grounded explicitly in the BNS/BNSS context.

---

## Next retrieval improvements

The failures point to practical Phase 7/8 candidates:

- Add a lightweight lexical/BM25 fallback over marginal headings and
  `source section_number` strings.
- Boost exact marginal-heading phrases before reranking.
- For out-of-scope/adversarial questions, add a cheap pre-generation classifier
  or confidence threshold so unrelated dense hits do not force weak context
  into the generator.
