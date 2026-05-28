# Phase 1 Report — BNS + BNSS PDF Parser

**Phase:** 1
**Agent:** Claude Code
**Module:** [backend/app/parser.py](backend/app/parser.py)
**Outputs:** [backend/data/sections.json](backend/data/sections.json), [backend/data/sections_sample.md](backend/data/sections_sample.md)
**Run:** `.venv/bin/python -m backend.app.parser` (from repo root)
**Commit:** `feat: add BNS and BNSS PDF parser`

---

## Result

```
BNS:  359 entries (1 long_title + 358 sections), section numbers 1..358
BNSS: 532 entries (1 long_title + 531 sections), section numbers 1..531
```

- **No section numbers are missing** in either act. Section count matches the
  real BNS (358) and BNSS (531) section totals.
- Every entry has `source` set to `"BNS"` or `"BNSS"`. **Section-number
  collisions are real:** `BNS s.103` ("Punishment for murder") and `BNSS s.103`
  ("Persons in charge of closed place to allow search") are unrelated.
- Marginal-heading coverage: **342/358 (95.5%) BNS** and **522/531 (98.3%)
  BNSS**.
- Section bodies are clean of every gazette-noise token I searched for —
  `THE GAZETTE`, `EXTRAORDINARY`, `[Part II`, `MINISTRY OF LA W`, mangled
  Devanagari (`vlk/kkj`, `Hkkx`, `jftLV`), end-of-doc colophon (`UPLOADED BY`,
  `DIWAKAR`, `MGIPMRND`, `DN: c=IN`, `Digitally signed`). All audits → 0 hits.

## Output schema

`sections.json` is a single merged list. Each entry:

```json
{
  "source": "BNS" | "BNSS",
  "section_number": "1" | "2" | … | "long_title",
  "marginal_heading": "Punishment for murder" | null,
  "chapter": "Chapter VI" | null,
  "chapter_title": "OF OFFENCES AFFECTING THE HUMAN BODY" | null,
  "text": "103.(1) Whoever commits murder shall be punished with death…"
}
```

The first entry per source is `section_number: "long_title"` capturing each
Act's "An Act to consolidate and amend …" paragraph.

## What the parser does, briefly

1. **Per-page text extraction** via `pypdf.PdfReader.extract_text()` — no OCR.
2. **Line cleaning** strips:
   - Gazette masthead and repeating page headers/footers (the `THE GAZETTE OF
     INDIA EXTRAORDINARY [Part II—…` strip, page numbers, the `Sec. N]` right
     column header, dash-rule and underscore-rule separators).
   - Mangled-Devanagari boilerplate from page 1 (`vlk/kkj.k`, `Hkkx II — [k.M
     1`, `jftLVªh`, `ubZ fnYyh`, etc.) — detected by compact-uppercase token
     match, which handles the gazette's habit of inserting stray spaces inside
     words like `P ART II` or `MINISTRY OF LA W AND JUSTICE`.
   - End-of-document colophon and digital-signature block (`UPLOADED BY THE
     MANAGER`, `GOVERNMENT OF INDIA PRESS`, `DIGITALLY SIGNED BY`, `DN: c=IN`,
     `MGIPMRND`, signer names).
   - Side-note Act citations like `40 of 2019.`, `2 of 1974.`.
3. **Section boundary detection** uses `^\s*(\d{1,3})\.\s*(?:\(|[A-Z])`, which
   handles all three observed patterns: `1.(1)`, `2.In this Sanhita`,
   `337. Whoever`.
4. **Chapter title handling** copes with two extraction artefacts:
   - **Drop caps**: gazette prints the first letter as a large initial in its
     own visual block (e.g. `C` / `ONSTITUTION OF CRIMINAL COURTS…`). The
     parser detects single-letter all-caps lines and glues them to the next
     piece.
   - **Multi-line titles**: BNSS Chapter VIII's title spans three extracted
     lines. The parser keeps appending all-uppercase continuation lines until
     it hits a section start / next chapter / mixed-case line.
5. **Marginal-heading extraction** finds every contiguous run of short,
   title-case lines ending with a period inside a section body. The LAST run
   is the section's own heading. The earlier runs (when present) are
   **redistributed to the immediately preceding sections** that don't yet
   have a heading. This is the only fix that gets the parser past pypdf's
   multi-column extraction artefact:
   - Gazette pages are two-column. pypdf emits all section bodies first, then
     a *cluster* of every marginal heading on the page at the end of the last
     section on that page. For example, BNS page 34 contains sections 102–109
     and ends with eight stacked headings (`Culpable homicide …`, `Punishment
     for murder`, `Punishment for murder by life-convict`, …, `Attempt to
     murder`). Without redistribution, BNS s.103 would have `heading=None`
     and BNS s.109 would carry s.108's heading as its own. With
     redistribution, each gets the right one.
6. **Schedule cutoff**: parsing stops at the first `(FIRST|SECOND|…) SCHEDULE`
   line. Both acts contain schedules at the end (Bharatiya Nyaya Sanhita
   schedules; BNSS First Schedule listing offences and their classifications).
   The schedules are excluded from `sections.json` because they are not
   section-numbered prose — they're tables, and would need a different
   chunking strategy for Phase 2. **Confirm with Apoorva** whether to include
   them later (see manual-check item 4).

## Sections with `marginal_heading = null`

These 25 sections have no heading assigned. Most are first sections on a new
gazette page — pypdf's heading cluster for that page ended up attached to the
last section of the *previous* page, so my redistribution pass found no
heading-like runs in the body and could not look across page boundaries.

| Source | Sections without heading |
|---|---|
| **BNS** (16) | 49, 63, 78, 181, 182, 193, 206, 213, 214, 230, 256, 257, 295, 337, 338, 342 |
| **BNSS** (9) | 4, 148, 157, 167, 211, 260, 385, 414, 452 |

These are NOT bugs in section detection — the section text itself is captured
correctly. Only the metadata `marginal_heading` is missing. If higher coverage
matters for Phase 4 citations, a follow-up could:
(a) cross attribute when a section has N+1 heading runs and N preceding
    sections (instead of stopping at the immediately preceding sections), or
(b) re-extract with a layout-aware library (`pdfplumber` with coordinates) so
    headings stay attached to their section column.

## What was skipped or known-ambiguous

- **Schedules at the end of both acts** — see point 6 above.
- A small number of **chapter titles still carry intra-word spaces** because
  the gazette prints them that way and I deliberately preserved the extracted
  letters rather than guessing word boundaries: `REPEAL AND SA VINGS`,
  `OF CRIMINAL INTIMIDA TION, INSUL T, ANNOY ANCE, DEFAMA TION, ETC.`, `OF
  OFFENCES RELA TING TO …`. The text is identifiable as English; downstream
  search will be unaffected, but a string match against `REPEAL AND SAVINGS`
  needs to be tolerant. **Phase 2** (chunker) can collapse `SA VINGS → SAVINGS`
  before chunking metadata is written, or we can normalise here — flag if you
  want me to.
- The same spaced-letter artefact appears in some body text (`(c) any
  penalty , or punishment` has a stray space before the comma). Real legal
  text — no fix unless it hurts retrieval.
- BNS section 1's text contains a hairline-bug from pypdf: the page-1 column
  break causes `(2)` to appear before `(3)` of section 1, then a marginal
  heading and gazette masthead, then `(3)` resumes. The masthead is filtered,
  but the order of sub-clauses (2) and (3) is from the source PDF. Verify
  this is faithful (see manual-check item 1).

---

## Manual checks for Apoorva

Please verify the following directly against the PDFs in `Sources/`:

### Required spot checks

1. **BNS s.1 — Section 1's body order.** Open the BNS PDF, page 1–2. Does
   the parsed body for BNS s.1 match the printed order of sub-clauses
   `(1)…(6)`? Note that `(2)` precedes `(3)` in column order on page 1.
2. **BNS s.103 = "Punishment for murder"** — open BNS PDF (around page 34),
   confirm `103. (1) Whoever commits murder shall be punished with death…` and
   marginal heading `Punishment for murder`.
3. **BNSS s.103 = "Persons in charge of closed place to allow search"** —
   open BNSS PDF (around page 64), confirm the search-procedure text. This
   proves the section-number collision is handled correctly.
4. **BNSS s.187 = "Procedure when investigation cannot be completed in
   twenty-four hours"** — open BNSS PDF (around page 86). The plan calls out
   `BNSS s.187` as a canonical example; confirm the body matches.
5. **BNS s.358 = "Repeal and savings"** — open BNS PDF, second-last page.
   Confirm s.358 ends with sub-clause (4) about "the General Clauses Act,
   1897" and does NOT contain the signer name, digital signature, or
   `UPLOADED BY THE MANAGER`. (Earlier drafts had those leaking in.)
6. **BNSS s.531 = "Repeal and savings"** — open BNSS PDF, last page. Same
   check.

### Schedule decision

7. **Schedules are excluded.** Open BNS PDF page ~100 and BNSS PDF page ~218+.
   Both acts have schedules listing offences and their classifications. The
   parser stops at the schedule heading. **Tell me whether you want them
   indexed** — they're useful for "is X a cognizable offence" questions but
   need a different parsing strategy (they're tables).

### Sections with `marginal_heading = null`

8. **Pick 2–3 from the missing list** (e.g. BNS s.49, BNS s.337, BNSS s.4)
   and check the printed marginal heading in the PDF. If the actual heading
   in the PDF is short and would be useful for citations, I can write a
   follow-up pass that walks across page boundaries to recover them.

### Chapter title cosmetics

9. **Decide on spaced-letter chapter titles** like `REPEAL AND SA VINGS`,
   `MISCELLANEOUS` (the BNSS Ch XXXIX title — that one came out fine).
   Should I collapse the gazette's stray spaces (e.g. `SA VINGS → SAVINGS`)
   in chapter titles before Phase 2 writes them into chunk metadata? My
   default would be yes, but only after you confirm.

---

## Final submission update — 2026-05-28

The parser output remains the source of the committed
[backend/data/sections.json](backend/data/sections.json). The deployed app uses
the same parsed BNS/BNSS section corpus available in the public GitHub repo.
