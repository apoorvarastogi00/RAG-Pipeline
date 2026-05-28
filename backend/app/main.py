"""FastAPI app — `POST /chat` and `GET /health`.

The `/chat` response shape matches PROJECT_PLAN.md Section 4 EXACTLY and is
frozen as the Phase 7 (frontend) API contract:

    {
      "answer":             "string",
      "citations":          [{"source", "section_number", "marginal_heading",
                              "chapter", "snippet"}, ...],
      "retrieved_sections": [{"source", "section_number"}, ...],
      "no_answer":          bool
    }

Run locally:
    .venv/bin/python -m uvicorn backend.app.main:app --reload --port 7860

Open http://127.0.0.1:7860/docs for the Swagger UI.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.app import config
from backend.app.generator import (
    build_context,
    call_groq,
    extract_cited,
    parse_answer,
)
from backend.app.retriever import RetrievedChunk, Retriever

# Load the Groq key from backend/.env before any client is instantiated.
load_dotenv(config.ROOT / "backend" / ".env")


# --------------------------------------------------------------- API schema

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000,
                       description="User's natural-language legal question.")


class Citation(BaseModel):
    source: str
    section_number: str
    marginal_heading: str
    chapter: str
    snippet: str


class RetrievedSection(BaseModel):
    source: str
    section_number: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieved_sections: list[RetrievedSection]
    no_answer: bool


class HealthResponse(BaseModel):
    status: str


# ------------------------------------------------------------ app lifespan

_retriever: Retriever | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Warm up the embedding model and Chroma client once at startup so
    every `/chat` call shares them."""
    global _retriever
    _retriever = Retriever()
    yield


app = FastAPI(
    title="Legal Research RAG Chatbot",
    description="Grounded RAG over BNS, 2023 and BNSS, 2023.",
    version="0.4.0",
    lifespan=lifespan,
)

# CORS — open for now; the Vite dev server in Phase 7 runs on a different
# port. Tighten in Phase 8 (deployment) before going public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ----------------------------------------------------------- helpers

SNIPPET_CHARS = 320


def _snippet(chunk: RetrievedChunk) -> str:
    flat = " ".join(chunk.text.split())
    return flat[:SNIPPET_CHARS] + ("…" if len(flat) > SNIPPET_CHARS else "")


def _build_response(question: str, chunks: list[RetrievedChunk]) -> ChatResponse:
    context = build_context(chunks)
    raw = call_groq(question, context)
    answer, no_answer = parse_answer(raw)

    # retrieved_sections: dedupe by (source, section_number) in retrieval order
    seen: set[tuple[str, str]] = set()
    retrieved: list[RetrievedSection] = []
    for c in chunks:
        key = (c.source, c.section_number)
        if key not in seen:
            seen.add(key)
            retrieved.append(RetrievedSection(
                source=c.source, section_number=c.section_number,
            ))

    # citations: only sections the model actually cited, in citation order
    by_section: dict[tuple[str, str], RetrievedChunk] = {}
    for c in chunks:
        by_section.setdefault((c.source, c.section_number), c)

    citations: list[Citation] = []
    for src, num in extract_cited(answer):
        c = by_section.get((src, num))
        if c is None:
            # Model cited something we didn't retrieve — surface it as best
            # we can; downstream callers can flag.
            citations.append(Citation(
                source=src, section_number=num,
                marginal_heading="", chapter="",
                snippet="(citation not present in retrieved context)",
            ))
            continue
        citations.append(Citation(
            source=c.source,
            section_number=c.section_number,
            marginal_heading=c.marginal_heading,
            chapter=c.chapter,
            snippet=_snippet(c),
        ))

    return ChatResponse(
        answer=answer,
        citations=citations,
        retrieved_sections=retrieved,
        no_answer=no_answer,
    )


# ----------------------------------------------------------- endpoints

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    assert _retriever is not None, "Retriever not initialised (lifespan)"
    # Phase 5 two-stage retrieval: per-Act dense pool + explicit-section
    # pinning, reranked down to RERANK_TOP_K.
    chunks = _retriever.search(req.query, k=config.RERANK_TOP_K)
    return _build_response(req.query, chunks)
