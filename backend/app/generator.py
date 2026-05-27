"""Build a grounded context from retrieved chunks and call Groq.

The prompt forces the model to:
  * answer ONLY from the provided context,
  * cite as ``BNS s.NUMBER`` / ``BNSS s.NUMBER`` — never a bare number,
  * emit a literal ``NO_ANSWER`` sentinel when the corpus does not cover
    the question, so the API layer can flip ``no_answer=true``.
"""
from __future__ import annotations

import os
import re
from typing import Iterable

from groq import Groq

from backend.app import config
from backend.app.retriever import RetrievedChunk

SYSTEM_PROMPT = """\
You are a legal research assistant for two Indian Acts of Parliament:

- Bharatiya Nyaya Sanhita (BNS), 2023 — criminal offences; replaces the
  Indian Penal Code.
- Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023 — criminal procedure;
  replaces the Code of Criminal Procedure.

RULES — follow ALL of them:

1. Answer ONLY using the provided context passages. Do NOT use outside
   knowledge or the older IPC/CrPC. If the context does not contain the
   answer, refuse (see rule 4).

2. Cite every legal reference in this exact form: "BNS s.NUMBER" or
   "BNSS s.NUMBER" — for example, "BNS s.103" or "BNSS s.187". Never use
   a bare "s.103" or "section 103" without the BNS/BNSS prefix, because
   both Acts have overlapping section numbers (BNS s.103 is "Punishment
   for murder"; BNSS s.103 is about searches — completely different).
   Cite each relevant section at least once, inline next to the claim it
   supports.

3. Be concise, faithful to the statutory text, and quote short phrases
   from the context when it materially helps. Do not invent specifics
   (durations, fines, punishments) that are not in the context.

4. If the user's question cannot be answered from the provided context,
   respond with EXACTLY this two-line format and nothing else:

       NO_ANSWER
       <one sentence stating what is missing from the corpus>

   The first line must be the bare token ``NO_ANSWER`` on its own line.
"""

# Recognises citations in the form BNS s.103 / BNSS s.103 / BNS s. 103
# (case-insensitive on the source; the source itself is canonicalised
# back to upper-case BNS / BNSS).
CITATION_RE = re.compile(
    r"\b(BNS|BNSS)\s*s\.?\s*(\d{1,3})\b",
    re.IGNORECASE,
)


def build_context(chunks: Iterable[RetrievedChunk]) -> str:
    """Render retrieved chunks into a single context string, each prefixed
    with its source/section so the model can cite correctly."""
    blocks: list[str] = []
    for c in chunks:
        head = c.marginal_heading or "(no marginal heading captured)"
        chapter = f"; {c.chapter}" if c.chapter else ""
        blocks.append(
            f"[{c.source} s.{c.section_number} — {head}{chapter}]\n{c.text}"
        )
    return "\n\n---\n\n".join(blocks)


def extract_cited(answer: str) -> list[tuple[str, str]]:
    """Return ordered, deduplicated (source, section_number) pairs that
    the model actually cited in the answer."""
    seen: list[tuple[str, str]] = []
    for m in CITATION_RE.finditer(answer):
        key = (m.group(1).upper(), m.group(2))
        if key not in seen:
            seen.append(key)
    return seen


def parse_answer(raw: str) -> tuple[str, bool]:
    """Split off the NO_ANSWER sentinel and return (display_text, no_answer).

    Convention: ``no_answer = True`` only when the model says the WHOLE
    question can't be answered from the corpus (NO_ANSWER on the first
    non-empty line). A stray ``NO_ANSWER`` line emitted mid-answer (the
    model partially answered, then flagged that some sub-part is missing)
    is stripped from the visible text but does NOT flip the flag — Phase 5
    will address those partial-answer cases at the retrieval layer."""
    stripped = raw.strip()
    first_line, _, rest = stripped.partition("\n")
    if first_line.strip().upper() == "NO_ANSWER":
        return rest.strip(), True
    cleaned = "\n".join(
        ln for ln in stripped.splitlines() if ln.strip().upper() != "NO_ANSWER"
    ).strip()
    return cleaned, False


def call_groq(
    question: str,
    context: str,
    model_name: str = config.GROQ_MODEL_NAME,
    temperature: float = 0.1,
) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY not set. Load it from backend/.env before calling "
            "the generator (the FastAPI app does this on startup)."
        )
    client = Groq(api_key=api_key)
    user = (
        "CONTEXT:\n\n"
        f"{context}\n\n"
        "---\n\n"
        f"QUESTION: {question}\n\n"
        "Apply the citation format and no-answer rules from your system "
        "prompt. Cite each section you rely on inline."
    )
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user},
        ],
        temperature=temperature,
        max_tokens=1024,
    )
    return (resp.choices[0].message.content or "").strip()
