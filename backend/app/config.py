"""Project-wide paths and model names. Import everything else from here so
filenames / models can be moved in one place.

The parser and chunker were written before this module and use their own
``ROOT``/``DATA_DIR`` constants — they all resolve to the same paths.
"""
from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------- paths

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "Sources"
DATA_DIR = ROOT / "backend" / "data"

PDFS: dict[str, Path] = {
    "BNS":  SRC_DIR / "250883_english_01042024.pdf",
    "BNSS": SRC_DIR / "250884_2_english_01042024.pdf",
}

SECTIONS_PATH = DATA_DIR / "sections.json"
CHUNKS_PATH   = DATA_DIR / "chunks.json"
CHROMA_DIR    = DATA_DIR / "chroma"

# --------------------------------------------------------------------- models

# Embedding model — open-source, runs locally via sentence-transformers.
# bge-base-en-v1.5 returns 768-dim vectors and is one of the best small
# encoders for English retrieval (MTEB leaderboard, summer 2024).
EMBED_MODEL_NAME    = "BAAI/bge-base-en-v1.5"

# Cross-encoder used in Phase 5 for reranking the top-k retrieved chunks.
RERANKER_MODEL_NAME = "BAAI/bge-reranker-base"

# Generator (Phase 4). Open-weight Llama 3.3 70B served by Groq.
GROQ_MODEL_NAME     = "llama-3.3-70b-versatile"

# bge-base recommends prefixing *queries* (not documents) with this
# instruction for short-query-to-long-passage retrieval. Source: model card.
BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

# --------------------------------------------------------------------- chroma

COLLECTION_NAME = "legal_sections"

# bge-base-en-v1.5 outputs cosine-normalized vectors; tell HNSW to use cosine
# distance so distance ≈ 1 - similarity.
CHROMA_DISTANCE_SPACE = "cosine"

# --------------------------------------------------------------------- ingest

EMBED_BATCH_SIZE = 32
DEFAULT_TOP_K    = 5

# --------------------------------------------------------------- retrieval

# Phase 5 two-stage retrieval. We pull a wide candidate pool per Act with the
# bi-encoder, then a cross-encoder reranks the union and we keep the top
# RERANK_TOP_K. Pulling per-Act guarantees both BNS and BNSS are represented
# for cross-document questions, instead of one Act crowding out the other.
CANDIDATE_POOL_PER_SOURCE = 15   # dense candidates fetched per Act
RERANK_TOP_K              = 7    # final results returned after reranking
USE_RERANKER              = True
