"""Phase 6 evaluation harness.

Runs the current Phase 5 retriever against eval_questions.json and writes
evals/EVAL_RESULTS.md. The default mode is local and reproducible; pass
``--full`` to additionally call Groq for answer generation and LLM judging.

Metrics:
  - retrieval hit-rate: fraction of expected sections present in top-k
  - answer correctness:
      * default mode uses expected-section coverage as a local proxy for
        whether the answer can be correctly grounded
      * --full mode uses a generated answer plus an LLM judge

Run from the repo root:
    .venv/bin/python evals/run_evals.py
    .venv/bin/python evals/run_evals.py --full
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from textwrap import shorten

from dotenv import load_dotenv
from groq import Groq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import config
from backend.app.generator import build_context, call_groq, parse_answer
from backend.app.retriever import Retriever

QUESTIONS_PATH = ROOT / "evals" / "eval_questions.json"
RESULTS_PATH = ROOT / "evals" / "EVAL_RESULTS.md"
JUDGE_MODEL = config.GROQ_MODEL_NAME


@dataclass(frozen=True)
class EvalCase:
    question: str
    expected_sections: list[dict[str, str]]
    reference_answer: str
    category: str


@dataclass(frozen=True)
class EvalResult:
    question: str
    category: str
    expected: list[tuple[str, str]]
    retrieved: list[tuple[str, str]]
    retrieval_hit_rate: float
    correct: bool
    no_answer: bool
    answer: str
    mode: str


def _load_questions() -> list[EvalCase]:
    raw = json.loads(QUESTIONS_PATH.read_text())
    return [
        EvalCase(
            question=item["question"],
            expected_sections=item.get("expected_sections", []),
            reference_answer=item["reference_answer"],
            category=item["category"],
        )
        for item in raw
    ]


def _dedupe_sections(sections: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: list[tuple[str, str]] = []
    for source, number in sections:
        key = (source, str(number))
        if key not in seen:
            seen.append(key)
    return seen


def _expected(case: EvalCase) -> list[tuple[str, str]]:
    return _dedupe_sections([
        (item["source"], str(item["section_number"]))
        for item in case.expected_sections
    ])


def _retrieval_hit_rate(
    expected: list[tuple[str, str]],
    retrieved: list[tuple[str, str]],
) -> float:
    if not expected:
        return 1.0
    retrieved_set = set(retrieved)
    hits = sum(1 for section in expected if section in retrieved_set)
    return hits / len(expected)


def _format_sections(sections: list[tuple[str, str]]) -> str:
    if not sections:
        return "-"
    return ", ".join(f"{source} s.{number}" for source, number in sections)


def _judge_answer(
    client: Groq,
    case: EvalCase,
    answer: str,
    no_answer: bool,
) -> bool:
    if case.reference_answer == "NO_ANSWER":
        return no_answer
    if no_answer:
        return False

    prompt = f"""\
You are grading a legal RAG answer.

Question:
{case.question}

Reference answer:
{case.reference_answer}

Generated answer:
{answer}

Mark YES if the generated answer contains the core legal information in the
reference answer and does not contradict it. Minor wording differences are OK.
Mark NO if it misses a key legal point, invents a conflicting rule, or refuses
despite answerable context.

Reply with exactly YES or NO.
"""
    resp = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=8,
    )
    verdict = (resp.choices[0].message.content or "").strip().upper()
    return verdict.startswith("YES")


def _proxy_correctness(case: EvalCase, retrieval_hit_rate: float) -> bool:
    """Local answer-correctness proxy used by the default eval mode.

    For answerable questions, all expected statutory sections need to be in the
    retrieved context before a grounded answer can be correct. For out-of-scope
    questions, the dataset expects NO_ANSWER and contains no expected sections.
    """
    if case.reference_answer == "NO_ANSWER":
        return not case.expected_sections
    return retrieval_hit_rate == 1.0


def _evaluate_case(
    case: EvalCase,
    retriever: Retriever,
    judge_client: Groq | None,
    full: bool,
) -> EvalResult:
    chunks = retriever.search(case.question, k=config.RERANK_TOP_K)
    retrieved = _dedupe_sections([
        (chunk.source, chunk.section_number)
        for chunk in chunks
    ])
    expected = _expected(case)
    hit_rate = _retrieval_hit_rate(expected, retrieved)

    if full:
        assert judge_client is not None
        context = build_context(chunks)
        raw = call_groq(case.question, context, temperature=0.0)
        answer, no_answer = parse_answer(raw)
        correct = _judge_answer(judge_client, case, answer, no_answer)
        mode = "full"
    else:
        answer = ""
        no_answer = case.reference_answer == "NO_ANSWER"
        correct = _proxy_correctness(case, hit_rate)
        mode = "retrieval_proxy"

    return EvalResult(
        question=case.question,
        category=case.category,
        expected=expected,
        retrieved=retrieved,
        retrieval_hit_rate=hit_rate,
        correct=correct,
        no_answer=no_answer,
        answer=answer,
        mode=mode,
    )


def _summarise(results: list[EvalResult]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[EvalResult]] = defaultdict(list)
    for result in results:
        grouped[result.category].append(result)

    summary: dict[str, dict[str, float]] = {}
    for category, rows in grouped.items():
        summary[category] = {
            "count": len(rows),
            "retrieval": sum(r.retrieval_hit_rate for r in rows) / len(rows),
            "correctness": sum(1 for r in rows if r.correct) / len(rows),
        }

    summary["TOTAL"] = {
        "count": len(results),
        "retrieval": sum(r.retrieval_hit_rate for r in results) / len(results),
        "correctness": sum(1 for r in results if r.correct) / len(results),
    }
    return summary


def _render_markdown(results: list[EvalResult]) -> str:
    summary = _summarise(results)
    order = ["easy_lookup", "multi_section", "cross_document", "out_of_scope", "TOTAL"]

    lines = [
        "# Evaluation Results",
        "",
        f"Questions: {len(results)}",
        f"Top-k: {config.RERANK_TOP_K}",
        f"Mode: `{results[0].mode}`",
        f"Generator/Judge model in `--full` mode: `{config.GROQ_MODEL_NAME}`",
        "",
        "## Summary",
        "",
        "| Category | Count | Retrieval Hit-Rate | Answer Correctness |",
        "|---|---:|---:|---:|",
    ]
    for category in order:
        stats = summary[category]
        label = f"**{category}**" if category == "TOTAL" else category
        lines.append(
            f"| {label} | {int(stats['count'])} | "
            f"{stats['retrieval']:.1%} | {stats['correctness']:.1%} |"
        )

    lines.extend([
        "",
        "## Per-question Results",
        "",
        "| # | Category | Retrieval | Correct | Expected | Retrieved | Question |",
        "|---:|---|---:|---|---|---|---|",
    ])

    for i, result in enumerate(results, 1):
        question = result.question.replace("|", "\\|")
        retrieved = _format_sections(result.retrieved).replace("|", "\\|")
        expected = _format_sections(result.expected).replace("|", "\\|")
        lines.append(
            f"| {i} | {result.category} | {result.retrieval_hit_rate:.0%} | "
            f"{'yes' if result.correct else 'no'} | {expected} | {retrieved} | "
            f"{question} |"
        )

    weak = [
        r for r in results
        if r.retrieval_hit_rate < 1.0 or not r.correct
    ]
    lines.extend([
        "",
        "## Questions to Inspect",
        "",
    ])
    if not weak:
        lines.append("All questions passed retrieval and correctness checks.")
    else:
        for result in weak:
            answer_preview = (
                shorten(" ".join(result.answer.split()), width=180)
                if result.answer else "(not generated in retrieval_proxy mode)"
            )
            lines.append(
                f"- **{result.category}** `{result.retrieval_hit_rate:.0%}` "
                f"{'correct' if result.correct else 'incorrect'}: "
                f"{result.question} Expected: {_format_sections(result.expected)}. "
                f"Retrieved: {_format_sections(result.retrieved)}. "
                f"Answer: {answer_preview}"
            )

    lines.append("")
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 6 evals.")
    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "Call Groq for answer generation and LLM judging. The default "
            "mode runs a local retrieval-proxy eval to avoid API quota noise."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    load_dotenv(ROOT / "backend" / ".env")
    if args.full and not os.environ.get("GROQ_API_KEY"):
        raise RuntimeError(
            "GROQ_API_KEY is required for --full. Copy backend/.env.example to "
            "backend/.env and set GROQ_API_KEY."
        )

    cases = _load_questions()
    retriever = Retriever()
    judge_client = (
        Groq(api_key=os.environ["GROQ_API_KEY"])
        if args.full else None
    )

    results: list[EvalResult] = []
    for i, case in enumerate(cases, 1):
        print(f"[{i:02d}/{len(cases)}] {case.category}: {case.question}")
        result = _evaluate_case(case, retriever, judge_client, args.full)
        results.append(result)
        print(
            "    retrieval="
            f"{result.retrieval_hit_rate:.0%} correct={result.correct} "
            f"expected={_format_sections(result.expected)}"
        )

    markdown = _render_markdown(results)
    RESULTS_PATH.write_text(markdown)
    print()
    print(markdown)


if __name__ == "__main__":
    main()
