"""Phase 2 — section-aware chunking.

Reads ``backend/data/sections.json`` and produces:
  - ``backend/data/chunks.json`` — one chunk per section by default; sections
    over the character budget are split at top-level sub-clause / explanation
    / illustration / proviso boundaries (never mid-sentence). Every chunk
    carries ``source`` and all parent-section metadata, plus a 1-indexed
    ``part`` field.
  - ``backend/data/chunks_sample.md`` — six chunks selected for manual review.

Run from the repo root:
    .venv/bin/python -m backend.app.chunker
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "backend" / "data"
SECTIONS_PATH = DATA_DIR / "sections.json"
CHUNKS_PATH = DATA_DIR / "chunks.json"
SAMPLE_PATH = DATA_DIR / "chunks_sample.md"

# Per-chunk character budget. ``BAAI/bge-base-en-v1.5`` has a 512-token max
# context; English averages ~4 chars/token under BERT WordPiece, so 1500 chars
# (~375 tokens) leaves comfortable headroom for the legal vocabulary's longer
# subword splits and for any context prefix the ingester adds later.
CHAR_BUDGET = 1500

# Primary structural boundaries: top-level sub-clauses ``(1)`` ``(2)``, plus
# Explanation / Illustration / Provided blocks. Pass 1 splits only at these,
# so nested ``(a)`` / ``(i)`` clauses stay attached to their parent ``(N)``.
SUB_CLAUSE_RE   = re.compile(r"^\(\d+\)")
EXPLANATION_RE  = re.compile(r"^Explanation\b", re.IGNORECASE)
ILLUSTRATION_RE = re.compile(r"^Illustrations?\b", re.IGNORECASE)
PROVIDED_RE     = re.compile(r"^Provided\b", re.IGNORECASE)
PRIMARY_BOUNDARIES = (SUB_CLAUSE_RE, EXPLANATION_RE, ILLUSTRATION_RE, PROVIDED_RE)

# Secondary boundaries: lettered ``(a)`` / roman ``(i)`` sub-clauses. Used
# only as a fallback when a primary-split chunk is still over budget (long
# enumerations like the 16-item Illustrations block under BNS s.303 "Theft").
SUB_LETTER_RE = re.compile(r"^\([a-z]{1,3}\)")
SUB_ROMAN_RE  = re.compile(r"^\([ivxlcdm]+\)", re.IGNORECASE)
SECONDARY_BOUNDARIES = PRIMARY_BOUNDARIES + (SUB_LETTER_RE, SUB_ROMAN_RE)


def _split_into_pieces(text: str, boundaries: tuple[re.Pattern, ...]) -> list[str]:
    """Cut ``text`` at every line whose first non-whitespace token matches a
    boundary. Each returned piece begins with a boundary line (except the
    first piece, which holds the section opener)."""
    pieces: list[list[str]] = [[]]
    for line in text.splitlines():
        if any(p.match(line) for p in boundaries) and pieces[-1]:
            pieces.append([])
        pieces[-1].append(line)
    return ["\n".join(p).strip() for p in pieces if any(ln.strip() for ln in p)]


def _greedy_pack(pieces: list[str], budget: int) -> list[str]:
    """Concatenate sequential pieces while the running total stays ≤ budget.
    A single oversized piece becomes its own chunk — we won't break the
    "no mid-sentence split" rule just to honour the budget."""
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for p in pieces:
        sep = 1 if cur else 0
        if cur and cur_len + sep + len(p) > budget:
            chunks.append("\n".join(cur))
            cur = [p]
            cur_len = len(p)
        else:
            cur.append(p)
            cur_len += sep + len(p)
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def _split_text(text: str, budget: int) -> list[str]:
    if len(text) <= budget:
        return [text]
    pieces = _split_into_pieces(text, PRIMARY_BOUNDARIES)
    if len(pieces) <= 1:
        # No structural boundaries inside this section — keep as one chunk
        # rather than chop mid-sentence.
        return [text]
    primary_chunks = _greedy_pack(pieces, budget)
    # For any chunk still over budget (typically a long Illustrations block),
    # fall back to the secondary boundaries.
    out: list[str] = []
    for c in primary_chunks:
        if len(c) <= budget:
            out.append(c)
            continue
        sub = _split_into_pieces(c, SECONDARY_BOUNDARIES)
        if len(sub) <= 1:
            out.append(c)
            continue
        out.extend(_greedy_pack(sub, budget))
    return out


def chunk_section(entry: dict, budget: int = CHAR_BUDGET) -> list[dict]:
    pieces = _split_text(entry["text"], budget)
    return [
        {
            "chunk_id": f"{entry['source']}_{entry['section_number']}_p{i}",
            "source": entry["source"],
            "section_number": entry["section_number"],
            "marginal_heading": entry["marginal_heading"],
            "chapter": entry["chapter"],
            "chapter_title": entry["chapter_title"],
            "part": i,
            "text": piece,
        }
        for i, piece in enumerate(pieces, start=1)
    ]


def chunk_all(entries: list[dict], budget: int = CHAR_BUDGET) -> list[dict]:
    out: list[dict] = []
    for e in entries:
        out.extend(chunk_section(e, budget))
    return out


# ------------------------------------------------------------------- sample --

def _write_sample(chunks: list[dict], path: Path) -> None:
    by_section: dict[tuple[str, str], list[dict]] = {}
    for c in chunks:
        by_section.setdefault((c["source"], c["section_number"]), []).append(c)

    picks: list[tuple[str, dict]] = []

    def _first_split(src: str) -> list[dict] | None:
        for (s, sec), parts in by_section.items():
            if s == src and sec != "long_title" and len(parts) >= 2:
                return parts
        return None

    bns_split = _first_split("BNS")
    if bns_split:
        picks.append((f"BNS split section — part 1 of {len(bns_split)}", bns_split[0]))
        picks.append((f"BNS split section — part {len(bns_split)} of {len(bns_split)}", bns_split[-1]))

    bnss_split = _first_split("BNSS")
    if bnss_split:
        picks.append((f"BNSS split section — part 1 of {len(bnss_split)}", bnss_split[0]))

    def _single_chunk(src: str, min_len: int = 400, max_len: int = 1500):
        for (s, sec), parts in by_section.items():
            if s == src and sec != "long_title" and len(parts) == 1:
                if min_len <= len(parts[0]["text"]) <= max_len:
                    return parts[0]
        return None

    bns_single = _single_chunk("BNS")
    if bns_single:
        picks.append(("BNS single-chunk section", bns_single))

    bnss_single = _single_chunk("BNSS")
    if bnss_single:
        picks.append(("BNSS single-chunk section", bnss_single))

    bns_long_title = by_section.get(("BNS", "long_title"))
    if bns_long_title:
        picks.append(("BNS long title", bns_long_title[0]))

    lines = ["# chunks_sample.md — Phase 2 manual review", ""]
    for label, c in picks:
        lines.append(f"## {label} — {c['chunk_id']}")
        lines.append("")
        for k in ("chunk_id", "source", "section_number", "part",
                  "marginal_heading", "chapter", "chapter_title"):
            lines.append(f"- **{k}:** {c[k]}")
        lines.append(f"- **text length (chars):** {len(c['text'])}")
        lines.append("")
        lines.append("```text")
        lines.append(c["text"])
        lines.append("```")
        lines.append("")
    path.write_text("\n".join(lines))


# ------------------------------------------------------------------ runner --

def main() -> None:
    entries = json.loads(SECTIONS_PATH.read_text())
    chunks = chunk_all(entries)
    CHUNKS_PATH.write_text(json.dumps(chunks, ensure_ascii=False, indent=2))
    _write_sample(chunks, SAMPLE_PATH)

    by_source: dict[str, int] = {}
    parts_per_section: dict[tuple[str, str], int] = {}
    for c in chunks:
        by_source[c["source"]] = by_source.get(c["source"], 0) + 1
        key = (c["source"], c["section_number"])
        parts_per_section[key] = parts_per_section.get(key, 0) + 1

    sections_split: dict[str, int] = {"BNS": 0, "BNSS": 0}
    for (src, _), n in parts_per_section.items():
        if n > 1:
            sections_split[src] = sections_split.get(src, 0) + 1

    longest = max(chunks, key=lambda c: len(c["text"]))
    avg_len = sum(len(c["text"]) for c in chunks) / len(chunks)
    print(f"Total chunks: {len(chunks)}")
    for src in ("BNS", "BNSS"):
        print(f"  {src}: {by_source.get(src, 0)} chunks; sections split: "
              f"{sections_split.get(src, 0)}")
    print(f"Average chunk length: {avg_len:.0f} chars")
    print(f"Longest chunk: {longest['chunk_id']} ({len(longest['text'])} chars)")
    print(f"Wrote {CHUNKS_PATH}")
    print(f"Wrote {SAMPLE_PATH}")


if __name__ == "__main__":
    main()
