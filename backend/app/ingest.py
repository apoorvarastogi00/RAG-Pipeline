"""Phase 3 — end-to-end ingest pipeline.

  parse PDFs (if needed) -> chunk (if needed) -> embed -> upsert into Chroma

Idempotent:
  - sections.json / chunks.json are regenerated only if missing.
  - The Chroma collection is upserted by ``chunk_id``; re-running yields no
    duplicates (Chroma overwrites existing ids in place).

Run from the repo root:
    .venv/bin/python -m backend.app.ingest

Or programmatically:
    from backend.app.ingest import build_index, query
    coll, model = build_index()
    hits = query(coll, model, "punishment for murder", k=5)
"""
from __future__ import annotations

import json
from typing import Iterable

import chromadb
from sentence_transformers import SentenceTransformer

from backend.app import config
from backend.app.chunker import chunk_all
from backend.app.parser import parse_act, _redistribute_headings


# ------------------------------------------------------------- pipeline ----

def _ensure_sections() -> list[dict]:
    if config.SECTIONS_PATH.exists():
        return json.loads(config.SECTIONS_PATH.read_text())
    print("sections.json missing — running parser…")
    all_entries: list[dict] = []
    for src, path in config.PDFS.items():
        entries = parse_act(src, path)
        _redistribute_headings(entries)
        all_entries.extend(entries)
    for e in all_entries:
        e.pop("_heading_candidates", None)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.SECTIONS_PATH.write_text(
        json.dumps(all_entries, ensure_ascii=False, indent=2)
    )
    return all_entries


def _ensure_chunks(entries: list[dict]) -> list[dict]:
    if config.CHUNKS_PATH.exists():
        return json.loads(config.CHUNKS_PATH.read_text())
    print("chunks.json missing — running chunker…")
    chunks = chunk_all(entries)
    config.CHUNKS_PATH.write_text(json.dumps(chunks, ensure_ascii=False, indent=2))
    return chunks


def _metadata_for(chunk: dict) -> dict:
    """Chroma metadata values must be str / int / float / bool — never None.
    Nullable section fields collapse to ``""`` here; the FastAPI response
    will translate them back if needed."""
    return {
        "source":           chunk["source"],
        "section_number":   chunk["section_number"],
        "marginal_heading": chunk["marginal_heading"] or "",
        "chapter":          chunk["chapter"] or "",
        "chapter_title":    chunk["chapter_title"] or "",
        "part":             int(chunk["part"]),
    }


def _embedding_input(chunk: dict) -> str:
    """Body text augmented with a compact context header so that semantic
    similarity catches the section/chapter even when the user query uses
    different wording. Documents stored in Chroma are still the raw body
    (in ``documents``); this only affects the vector."""
    parts = [f"{chunk['source']} section {chunk['section_number']}"]
    if chunk["marginal_heading"]:
        parts.append(chunk["marginal_heading"])
    if chunk["chapter_title"]:
        parts.append(chunk["chapter_title"])
    header = ". ".join(parts)
    return f"{header}.\n\n{chunk['text']}"


# ------------------------------------------------------------- build/query --

def build_index(
    chunks: list[dict] | None = None,
    model: SentenceTransformer | None = None,
    client: chromadb.api.client.Client | None = None,
) -> tuple[chromadb.Collection, SentenceTransformer]:
    """Embed every chunk and upsert into Chroma. Returns ``(collection, model)``
    so callers can immediately query without re-loading the encoder."""
    if chunks is None:
        chunks = _ensure_chunks(_ensure_sections())
    if model is None:
        print(f"Loading {config.EMBED_MODEL_NAME} …")
        model = SentenceTransformer(config.EMBED_MODEL_NAME)
    if client is None:
        config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))

    coll = client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": config.CHROMA_DISTANCE_SPACE},
    )

    ids       = [c["chunk_id"] for c in chunks]
    documents = [c["text"]     for c in chunks]
    metadatas = [_metadata_for(c) for c in chunks]
    inputs    = [_embedding_input(c) for c in chunks]

    print(f"Embedding {len(inputs)} chunks…")
    embeddings = model.encode(
        inputs,
        batch_size=config.EMBED_BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    coll.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings.tolist(),
    )
    print(f"Upserted {len(ids)} chunks into '{config.COLLECTION_NAME}' "
          f"(collection now has {coll.count()})")
    return coll, model


def query(
    coll: chromadb.Collection,
    model: SentenceTransformer,
    text: str,
    k: int = config.DEFAULT_TOP_K,
    where: dict | None = None,
) -> dict:
    """Run a single similarity search. Pass ``where={"source": "BNS"}`` to
    restrict to one Act."""
    q_emb = model.encode(
        [config.BGE_QUERY_INSTRUCTION + text],
        normalize_embeddings=True,
    )
    return coll.query(
        query_embeddings=q_emb.tolist(),
        n_results=k,
        where=where,
        include=["metadatas", "documents", "distances"],
    )


# ----------------------------------------------------------------- runner --

SAMPLE_QUERIES: list[tuple[str, str]] = [
    ("BNS",  "What is the punishment for murder?"),
    ("BNS",  "What is the punishment for theft?"),
    ("BNSS", "How long can the police detain a person before producing them in court?"),
    ("BNSS", "What is the procedure for arrest without a warrant?"),
]


def _print_query_results(coll, model, queries: Iterable[tuple[str, str]],
                         k: int = config.DEFAULT_TOP_K) -> None:
    for expected_src, q in queries:
        r = query(coll, model, q, k=k)
        print(f"\nQUERY ({expected_src}-flavoured): {q}")
        for i, (md, dist) in enumerate(zip(r["metadatas"][0], r["distances"][0]), 1):
            head = md["marginal_heading"] or "(no heading)"
            print(f"  [{i}] {md['source']} s.{md['section_number']:>3}_p{md['part']} "
                  f"| dist={dist:.3f} | {head[:70]}")


def main() -> None:
    coll, model = build_index()
    print("\n=== Sample similarity queries ===")
    _print_query_results(coll, model, SAMPLE_QUERIES)


if __name__ == "__main__":
    main()
