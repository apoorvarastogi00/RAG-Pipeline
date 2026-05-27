# Phase 2 Report — Section-aware chunking

**Phase:** 2
**Agent:** Claude Code
**Module:** [backend/app/chunker.py](backend/app/chunker.py)
**Input:** [backend/data/sections.json](backend/data/sections.json) (from Phase 1)
**Outputs:** [backend/data/chunks.json](backend/data/chunks.json), [backend/data/chunks_sample.md](backend/data/chunks_sample.md)
**Run:** `.venv/bin/python -m backend.app.chunker` (from repo root)
**Commit:** `feat: implement section-aware chunking`

---

## Result

```
Total chunks: 1162
  BNS:   473 chunks  (306 single-chunk sections, 53 sections split)
  BNSS:  689 chunks  (425 single-chunk sections, 107 sections split)

Average chunk length: 760 chars
Longest chunk: BNSS_359_p1 (4049 chars — table-formatted section, see below)
Shortest chunk: BNSS_79_p1   (62 chars — single-sentence section)
Chunks over the 1500-char budget: 7 of 1162 (0.6%)
Most-split section: BNS s.2 ("Definitions") — 10 parts
```

## Chunk schema

`chunks.json` is a single list of chunk dicts:

```json
{
  "chunk_id":         "BNS_103_p1",
  "source":           "BNS" | "BNSS",
  "section_number":   "103" | "long_title" | …,
  "marginal_heading": "Punishment for murder" | null,
  "chapter":          "Chapter VI" | null,
  "chapter_title":    "OF OFFENCES AFFECTING THE HUMAN BODY" | null,
  "part":             1,
  "text":             "103. (1) Whoever commits murder shall be punished…"
}
```

`chunk_id` is `{source}_{section_number}_p{part}` and is unique across the
whole file — safe to use as the ChromaDB document id in Phase 3.

## What the chunker does

1. **Default policy: one chunk per section.** If the section text fits within
   `CHAR_BUDGET = 1500` chars, it becomes one chunk with `part=1`. This holds
   for 306 of 358 BNS sections (85%) and 425 of 531 BNSS sections (80%).
2. **Why 1500 chars.** The embedding model is `BAAI/bge-base-en-v1.5`, max
   512 tokens. English legal text averages ~4 chars per WordPiece token, so
   1500 chars (~375 tokens) sits comfortably below the 512-token limit even
   on dense, citation-heavy passages where the tokenizer fragments words
   like "Bharatiya" / "Sanhita" / "Magistrate" into multiple subwords.
3. **Splitting (only when over budget) is structure-aware.** A two-pass
   approach:
   - **Pass 1 (primary boundaries):** split at line-starting `(N)` (top-level
     sub-clauses) and at `Explanation`, `Illustration`, `Illustrations`,
     `Provided` block markers. Pieces are greedy-packed up to the budget;
     each piece is kept atomic so we never split mid-sentence.
   - **Pass 2 (secondary, only if a Pass-1 chunk is still over budget):**
     re-split that chunk at `(a)` / `(i)` boundaries. This handles long
     enumerations like the 16-item Illustrations block under BNS s.303
     ("Theft") that have no `(N)` substructure but are clearly enumerated.
     Without the fallback, that one chunk alone was 4152 chars — well past
     what the embedding model can read.
4. **Metadata propagation.** Every part of a split section carries the same
   `source`, `marginal_heading`, `chapter`, `chapter_title` as the parent.
   Only `part` and `chunk_id` differ between siblings.
5. **`long_title` entries** become single chunks with `chunk_id`
   `BNS_long_title_p1` / `BNSS_long_title_p1`. They're small (one paragraph)
   and useful for grounding answers about the Acts' purpose.

## Distribution of chunk lengths

| Bucket (chars) | Count |
|---|---:|
| < 500 | 424 |
| 500 – 999 | 354 |
| 1000 – 1499 | 377 |
| 1500 – 1999 | 4 |
| 2000 – 2999 | 2 |
| ≥ 3000 | 1 |

The seven chunks above 1500 chars are listed below. They are the only places
where the embedding model will truncate input. Each represents content with
no further structural boundaries the chunker could exploit without breaking
the "no mid-sentence split" rule:

| chunk_id | chars | What it is |
|---|---:|---|
| `BNSS_359_p1` | 4049 | The "Compounding of offences" TABLE in BNSS s.359 — table rows extracted as multi-line text; no clean boundary inside. |
| `BNS_326_p1`  | 2421 | BNS s.326 "Mischief" intro paragraph — a single dense definitional sentence. |
| `BNSS_359_p2` | 2182 | Continuation of the BNSS s.359 table. |
| `BNSS_293_p1` | 1850 | BNSS s.293 "Disposal of case". |
| `BNSS_129_p1` | 1757 | BNSS s.129 "Security for good behaviour from habitual offenders". |
| `BNS_263_p1`  | 1713 | BNS s.263 "Resistance or obstruction to lawful apprehension…". |
| `BNS_260_p1`  | 1567 | BNS s.260 "Intentional omission to apprehend on part of public servant…". |

These will lose tail content during embedding (the bge model reads only the
first ~512 tokens). For Phase 5 we can revisit by either (a) prepending a
section-title prefix and trimming the most repetitive parts, or (b) running
the table-shaped `BNSS_359` sections through a custom table chunker.

## Sections that were split

53 BNS sections and 107 BNSS sections produced more than one chunk. The
top-10 most-split sections:

| Section | Parts | Why it's long |
|---|---:|---|
| BNS s.2  | 10 | "Definitions" — 39 definition clauses |
| BNS s.356 | 7 | "Defamation" — multiple sub-offences and Explanations |
| BNSS s.187 | 7 | "Procedure when investigation cannot be completed in 24 hours" |
| BNSS s.359 | 6 | Compounding-of-offences table |
| BNSS s.243 | 5 | "Trial for more than one offence" |
| BNS s.335 | 5 | "Making a false document" |
| BNS s.101 | 5 | "Culpable homicide" |
| BNSS s.2  | 7 | "Definitions" |
| BNS s.303 | 4 | "Theft" — long Illustrations block |
| BNSS s.480 | 4 | "Special provisions regarding bail" |

(All split sections preserve the (1), (2), … numbering exactly as in the
PDF; each chunk begins with a sub-clause boundary line — verify with
spot-checks below.)

---

## Manual checks for Apoorva

Please spot-check the following against the PDF and the sample file:

1. **Sample file**: open [backend/data/chunks_sample.md](backend/data/chunks_sample.md).
   It shows six chunks: BNS s.1 (split into 2 parts), BNSS s.2 (first of 7
   parts), one short BNS single-chunk section, one BNSS single-chunk section,
   and BNS's long-title entry. Confirm that:
   - Split boundaries are at sub-clause `(N)` starts, never mid-sentence.
   - Both parts of a split section carry identical `marginal_heading`,
     `chapter`, and `chapter_title`.
   - `chunk_id` reads naturally as a citation key (`BNS_1_p1`, `BNSS_2_p1`).
2. **The longest section (BNS s.2 "Definitions") was split into 10 parts.**
   Open the BNS PDF pages 2-4 and confirm that the 39 definition clauses are
   distributed across the 10 chunks in order with no content dropped. Sample
   command:
   ```bash
   .venv/bin/python -c "import json; \
     [print(c['chunk_id'], len(c['text']), c['text'][:60].replace(chr(10),' ')) \
      for c in json.loads(open('backend/data/chunks.json').read()) \
      if c['source']=='BNS' and c['section_number']=='2']"
   ```
3. **The section-number collision is preserved across chunks.** Search for
   `BNS_103_` and `BNSS_103_` — both should exist, with completely different
   text. Sample:
   ```bash
   .venv/bin/python -c "import json; \
     [print(c['chunk_id'], '|', c['marginal_heading']) \
      for c in json.loads(open('backend/data/chunks.json').read()) \
      if c['section_number']=='103']"
   ```
4. **`BNSS s.359` is a TABLE.** That chunk text reads as a flattened table.
   Phase 3 (ingest) will embed and store it as-is; retrieval will still find
   it for compounding-of-offences questions, but the table layout will not
   be preserved in the answer. **Decide** whether you want a special-case
   parser for table sections in Phase 5, or whether the current behaviour is
   acceptable for the assignment.
5. **No mid-sentence splits.** Every chunk's text starts with either the
   section number (`103.`), a sub-clause marker (`(1)`, `(2)`, `(a)`, `(b)`,
   `(i)`, …), an `Explanation`, `Illustration`, or `Provided` opener — never
   in the middle of a sentence. The sample file shows this; if you want a
   broader check:
   ```bash
   .venv/bin/python -c "import json, re; chunks=json.loads(open('backend/data/chunks.json').read()); \
     bad=[c['chunk_id'] for c in chunks if not re.match(r'^(\d+\.|\\(|Explanation|Illustration|Provided|long_title)', c['text'])]; \
     print('chunks starting mid-sentence:', len(bad)); print(bad[:5])"
   ```
6. **Decision left for you: `CHAR_BUDGET = 1500`.** If you'd rather have
   denser-but-fewer chunks (say 2000-char budget) or smaller-but-more chunks
   (say 1000-char), it's a one-line change at the top of
   [backend/app/chunker.py](backend/app/chunker.py). Phase 3 will need to
   re-run regardless, so flag this before we proceed.
