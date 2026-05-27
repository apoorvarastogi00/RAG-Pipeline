"""Phase 1 — parse BNS and BNSS gazette PDFs into structured section entries.

Output (in ``backend/data/``):
  - ``sections.json`` — merged list. Every entry carries ``source`` ("BNS"|"BNSS").
  - ``sections_sample.md`` — 6 hand-picked sections rendered for manual review.

Run from the repo root:
    .venv/bin/python -m backend.app.parser
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "Sources"
DATA_DIR = ROOT / "backend" / "data"

PDFS: list[tuple[str, Path]] = [
    ("BNS",  SRC_DIR / "250883_english_01042024.pdf"),
    ("BNSS", SRC_DIR / "250884_2_english_01042024.pdf"),
]

# ---------------------------------------------------------- boilerplate noise

# Substring tokens — checked against the whitespace-stripped, uppercased line.
# These are distinctive enough that any occurrence is noise (page headers,
# colophon, mangled Devanagari masthead). DO NOT add common English words
# here — they will collide with section bodies (e.g. EXTRAORDINARY appears in
# "extraordinary original criminal jurisdiction" in BNSS s.415).
BOILERPLATE_SUBSTRINGS: tuple[str, ...] = (
    "THEGAZETTEOFINDIA",
    "PUBLISHEDBYAUTHORITY",
    "MINISTRYOFLAWANDJUSTICE",
    "LEGISLATIVEDEPARTMENT",
    "SEPARATEPAGINGISGIVEN",
    "VLK/KKJ.K",
    "IZKF/KDKJ",
    "XXXGID",
    "CG-DL-",
    "REGISTEREDNO",
    "NEWDELHI,MONDAY",
    "BEITENACTEDBYPARLIAMENT",
    "RECEIVEDTHEASSENTOFTHEPRESIDENT",
    "ISHEREBYPUBLISHEDFORGENERALINFORMATION",
    "NO.45OF2023",
    "NO.46OF2023",
    # Mangled-Devanagari runs that print on page 1 / in repeating headers
    # (`Hkkx`, `jftLVªh`, `ubZ fnYyh`, `fnlEcj`) — distinctive enough that
    # any occurrence in a line is noise.
    "HKKX",
    "JFTLV",
    "UBZFNYYH",
    "FNLECJ",
    # End-of-document colophon / digital-signature block
    "UPLOADEDBYTHEMANAGER",
    "GOVERNMENTOFINDIAPRESS",
    "CONTROLLEROFPUBLIC",
    "JOINTSECRETARY&",         # disambiguates from a section body using "Joint Secretary" as a role
    "DIGITALLYSIGNEDBY",
    "DN:C=IN",
    "POSTALCODE=",
    "PSEUDONYM=",
    "SERIALNUMBER=",
    "2.5.4.20=",
    "MGIPMRND",
    "DATE:2023.12.25",         # gazette signing timestamp
)

# Whole-line tokens — only filter when the entire compacted line equals one of
# these. Used for short generic words that would false-positive as substrings.
BOILERPLATE_WHOLELINE: tuple[str, ...] = (
    "EXTRAORDINARY",
    "PARTII",
    "PARTII-SECTION1",
    "PARTII—SECTION1",
    "PAUSHA",
    # End-of-document signer names (BNS colophon — these PDFs only)
    "DIWAKARSINGH",
    "DIWAKARSINGH,",
    "KSHITIZ",
    "MOHAN",
)

# Line-start patterns — filter when the (whitespace-collapsed) line begins
# with one of these. Used for prefixes that may include trailing content.
BOILERPLATE_PREFIXES: tuple[str, ...] = (
    "NEW DELHI, THE",
    "[25TH DECEMBER",
    "P ART II",
    "PART II",
    "[PART II",      # column-break marker on some pages
    "HKKX",
    "JFTLV",
    "UBZ FNYYH",
)

DEVA_RE             = re.compile(r"[ऀ-ॿ]")
PAGE_NUMBER_RE      = re.compile(r"^\s*\d{1,4}\s*$")
SECTION_START_RE    = re.compile(r"^\s*(\d{1,3})\.\s*(?:\(|[A-Z])")
CHAPTER_RE          = re.compile(r"^\s*CHAPTER\s+([IVXLCDM]+)\s*$")
ACT_TITLE_RE        = re.compile(r"^THE\b.*SANHITA.*2023\s*$", re.IGNORECASE)
LONG_TITLE_RE       = re.compile(r"^An\s+Act\s+to\b", re.IGNORECASE)
FOLLOWS_RE          = re.compile(r"^follows\s*:\s*[—–-]+\s*$", re.IGNORECASE)
SCHEDULE_RE         = re.compile(
    r"^(THE\s+)?(FIRST|SECOND|THIRD|FOURTH|FIFTH)\s+SCHEDULE\s*$", re.IGNORECASE
)
# Marginal citation of another Act, printed as a sidenote (e.g. "40 of 2019.")
ACT_CITATION_RE     = re.compile(r"^\s*\d{1,4}\s+of\s+\d{4}\s*\.?\s*$")
# A long horizontal rule typeset as dashes ("— — —— —")
DASH_RULE_RE        = re.compile(r"^\s*[—–-][\s—–-]*$")
# "Sec. 1]" right-column header
SEC_HEADER_RE       = re.compile(r"^\s*Sec\.\s*\d+\s*\]\s*$")
# Underscore-only ruler used between gazette columns
UNDERSCORE_RULE_RE  = re.compile(r"^\s*_+\s*$")

# Lines beginning with these words are section body content, never marginal
# headings — even though some are short and end with a period.
BODY_MARKER_PREFIXES: tuple[str, ...] = (
    "Explanation",
    "Illustration",
    "Illustrations",
    "Provided",
    "Note",
    "SCHEDULE",
)


# ----------------------------------------------------------------- cleanup --

def _normalize_whitespace(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _is_boilerplate(line: str) -> bool:
    deva = len(DEVA_RE.findall(line))
    if deva and deva / max(len(line), 1) > 0.1:
        return True
    if PAGE_NUMBER_RE.match(line):
        return True
    if ACT_CITATION_RE.match(line):
        return True
    if DASH_RULE_RE.match(line):
        return True
    if UNDERSCORE_RULE_RE.match(line):
        return True
    if SEC_HEADER_RE.match(line):
        return True
    upper = line.upper()
    for prefix in BOILERPLATE_PREFIXES:
        if upper.startswith(prefix):
            return True
    compact = re.sub(r"\s+", "", upper)
    if compact in BOILERPLATE_WHOLELINE:
        return True
    for token in BOILERPLATE_SUBSTRINGS:
        if token in compact:
            return True
    return False


def _clean_pages(reader: PdfReader) -> list[str]:
    out: list[str] = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        for raw in txt.splitlines():
            line = _normalize_whitespace(raw)
            if not line or _is_boilerplate(line):
                continue
            out.append(line)
    return out


# --------------------------------------------------------- chapter title --

def _collect_chapter_title(lines: list[str], start: int) -> tuple[Optional[str], int]:
    """Gazette PDFs often print the first letter of a chapter title as a drop
    cap, which pypdf extracts as a single-letter line. Some titles also span
    two lines. We collect consecutive lines that are either a single uppercase
    letter or wholly uppercase, until we hit a section / chapter / mixed-case
    line, then join (no space between drop-cap and the following piece)."""
    parts: list[str] = []
    j = start
    while j < len(lines):
        cand = lines[j]
        if SECTION_START_RE.match(cand) or CHAPTER_RE.match(cand):
            break
        if len(cand) == 1 and cand.isalpha() and cand.isupper():
            parts.append(cand)
            j += 1
            continue
        letters = [c for c in cand if c.isalpha()]
        if letters and all(c.isupper() for c in letters):
            parts.append(cand)
            j += 1
            continue
        break
    if not parts:
        return None, j
    if len(parts[0]) == 1 and len(parts) > 1:
        head = parts[0] + parts[1]
        rest = parts[2:]
    else:
        head = parts[0]
        rest = parts[1:]
    title = head if not rest else head + " " + " ".join(rest)
    return title, j


# -------------------------------------------------------- marginal heading --

def _heading_line_ok(line: str, *, is_first: bool) -> bool:
    if not line or len(line) > 40:
        return False
    if line.startswith(("(", "—", "–", "-")):
        return False
    if line[0].isdigit():
        return False
    if "—" in line or "––" in line:
        return False
    for prefix in BODY_MARKER_PREFIXES:
        if line.startswith(prefix):
            return False
    if is_first and not line[0].isupper():
        return False
    return True


def _prev_ends_a_clause(body: list[str], i: int) -> bool:
    """True iff the line before index i ends with a clause/sentence terminator,
    or i is the first body line. Used to gate where a heading run can start —
    a short ``India.`` mid-sentence (preceded by ``...guilty within``) is not
    a heading."""
    if i == 0:
        return True
    prev = body[i - 1].rstrip()
    return bool(prev) and prev[-1] in ".;:"


def _collect_heading_runs(body: list[str]) -> list[tuple[str, set[int]]]:
    """Return every contiguous run of short title-case lines ending with a
    period (each run is one logical heading), in body order. The caller
    decides which run is the section's own heading and what to do with the
    rest.

    Single-line runs are weak signal — they require the preceding line to end
    a clause so a mid-paragraph ``India.`` isn't picked up. Multi-line runs
    are unambiguous and skip that gate.
    """
    runs: list[tuple[str, set[int]]] = []
    i = 0
    while i < len(body):
        if _heading_line_ok(body[i], is_first=True):
            run = [i]
            terminated = body[i].rstrip().endswith(".")
            j = i + 1
            while not terminated and j < len(body) and (j - i) < 9:
                if _heading_line_ok(body[j], is_first=False):
                    run.append(j)
                    terminated = body[j].rstrip().endswith(".")
                    j += 1
                else:
                    break
            if terminated:
                ok = len(run) > 1 or _prev_ends_a_clause(body, i)
                if ok:
                    joined = " ".join(body[k].strip() for k in run)
                    heading = joined.rstrip(".").strip()
                    if heading and len(heading.split()) <= 25:
                        runs.append((heading, set(run)))
            i = run[-1] + 1
        else:
            i += 1
    return runs


# -------------------------------------------------------------- assemble ----

def _finalize(section: dict, source: str, chapter: Optional[str],
              chapter_title: Optional[str]) -> dict:
    body = section["body"]
    runs = _collect_heading_runs(body)
    drop: set[int] = set()
    for _, idx_set in runs:
        drop |= idx_set
    text = "\n".join(ln for k, ln in enumerate(body) if k not in drop).strip()
    return {
        "source": source,
        "section_number": section["number"],
        "marginal_heading": runs[-1][0] if runs else None,
        # Stored only so _redistribute_headings can read them in a second
        # pass; popped out before serialising.
        "_heading_candidates": [h for h, _ in runs],
        "chapter": chapter,
        "chapter_title": chapter_title,
        "text": text,
    }


def _redistribute_headings(entries: list[dict]) -> None:
    """When pypdf extracts a multi-column gazette page, all section bodies
    appear first and then a stacked cluster of every marginal heading on
    that page lands at the end of the LAST section on the page. We detect
    that here: if a section has N heading-like runs (N > 1), the LAST run
    is its own heading and the first N-1 runs are the headings of the
    immediately preceding N-1 sections (in document order). Reassign those
    extras to the preceding sections that have ``marginal_heading is None``.
    """
    by_section: dict[tuple[str, int], dict] = {}
    for e in entries:
        if e["section_number"].isdigit():
            by_section[(e["source"], int(e["section_number"]))] = e

    for e in entries:
        runs = e.pop("_heading_candidates", None)
        if not runs or not e["section_number"].isdigit():
            continue
        own_num = int(e["section_number"])
        extras = runs[:-1]
        for i, extra in enumerate(extras):
            target_num = own_num - len(extras) + i
            target = by_section.get((e["source"], target_num))
            if target is not None and target["marginal_heading"] is None:
                target["marginal_heading"] = extra


def parse_act(source: str, path: Path) -> list[dict]:
    reader = PdfReader(str(path))
    lines = _clean_pages(reader)

    entries: list[dict] = []
    chapter: Optional[str] = None
    chapter_title: Optional[str] = None
    current: Optional[dict] = None
    long_title_lines: list[str] = []
    long_title_done = False

    i = 0
    while i < len(lines):
        line = lines[i]

        if ACT_TITLE_RE.match(line):
            i += 1
            continue

        if not long_title_done and LONG_TITLE_RE.match(line):
            j = i
            while j < len(lines):
                lj = lines[j]
                if (lj.startswith("BE it enacted")
                        or CHAPTER_RE.match(lj)
                        or SECTION_START_RE.match(lj)
                        or ACT_TITLE_RE.match(lj)):
                    break
                long_title_lines.append(lj)
                j += 1
            long_title_done = True
            i = j
            continue

        if FOLLOWS_RE.match(line):
            i += 1
            continue

        m = CHAPTER_RE.match(line)
        if m:
            if current is not None:
                entries.append(_finalize(current, source, chapter, chapter_title))
                current = None
            chapter = f"Chapter {m.group(1)}"
            chapter_title, i = _collect_chapter_title(lines, i + 1)
            continue

        m = SECTION_START_RE.match(line)
        if m:
            if current is not None:
                entries.append(_finalize(current, source, chapter, chapter_title))
            current = {"number": m.group(1), "body": [line]}
            i += 1
            continue

        if SCHEDULE_RE.match(line):
            # Stop indexing at schedules — they're not section-numbered prose.
            if current is not None:
                entries.append(_finalize(current, source, chapter, chapter_title))
                current = None
            break

        if current is not None:
            current["body"].append(line)
        i += 1

    if current is not None:
        entries.append(_finalize(current, source, chapter, chapter_title))

    long_title_entry = {
        "source": source,
        "section_number": "long_title",
        "marginal_heading": "Long title",
        "chapter": None,
        "chapter_title": None,
        "text": " ".join(long_title_lines).strip(),
    }
    return [long_title_entry] + entries


# ------------------------------------------------------------------ output --

def _write_sample(entries: list[dict], path: Path) -> None:
    by_source: dict[str, list[dict]] = {}
    for e in entries:
        by_source.setdefault(e["source"], []).append(e)

    picks: list[tuple[str, dict]] = []
    for src in ("BNS", "BNSS"):
        non_lt = [e for e in by_source.get(src, []) if e["section_number"] != "long_title"]
        if non_lt:
            picks.append((f"{src} first section", non_lt[0]))
            picks.append((f"{src} last section",  non_lt[-1]))

    # one section featuring an Explanation block (prefer BNS)
    for src in ("BNS", "BNSS"):
        for e in by_source.get(src, []):
            if e["section_number"] == "long_title":
                continue
            if "Explanation" in e["text"]:
                picks.append((f"{src} section with Explanation", e))
                break
        else:
            continue
        break

    # longest section overall
    longest: Optional[dict] = None
    for e in entries:
        if e["section_number"] == "long_title":
            continue
        if longest is None or len(e["text"]) > len(longest["text"]):
            longest = e
    if longest is not None:
        picks.append((f"{longest['source']} longest section", longest))

    lines = ["# sections_sample.md — Phase 1 manual review", ""]
    for label, e in picks:
        lines.append(f"## {label} — {e['source']} s.{e['section_number']}")
        lines.append("")
        lines.append(f"- **source:** {e['source']}")
        lines.append(f"- **section_number:** {e['section_number']}")
        lines.append(f"- **marginal_heading:** {e['marginal_heading']}")
        lines.append(f"- **chapter:** {e['chapter']}")
        lines.append(f"- **chapter_title:** {e['chapter_title']}")
        lines.append(f"- **text length (chars):** {len(e['text'])}")
        lines.append("")
        lines.append("```text")
        lines.append(e["text"])
        lines.append("```")
        lines.append("")
    path.write_text("\n".join(lines))


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_entries: list[dict] = []
    for source, path in PDFS:
        if not path.exists():
            raise FileNotFoundError(f"Missing PDF for {source}: {path}")
        entries = parse_act(source, path)
        _redistribute_headings(entries)
        all_entries.extend(entries)
        nums = [int(e["section_number"]) for e in entries
                if e["section_number"].isdigit()]
        rng = f"{min(nums)}..{max(nums)}" if nums else "—"
        captured = sum(1 for e in entries
                       if e["section_number"].isdigit()
                       and e["marginal_heading"] is not None)
        print(f"{source}: {len(entries)} entries "
              f"(long_title + {len(entries) - 1} sections), range {rng}, "
              f"headings captured {captured}/{len(entries) - 1}")

    # Strip the internal field before writing.
    for e in all_entries:
        e.pop("_heading_candidates", None)

    out_json = DATA_DIR / "sections.json"
    out_json.write_text(json.dumps(all_entries, ensure_ascii=False, indent=2))
    sample_path = DATA_DIR / "sections_sample.md"
    _write_sample(all_entries, sample_path)
    print(f"wrote {out_json}")
    print(f"wrote {sample_path}")


if __name__ == "__main__":
    main()
