"""Top-k similarity search over the Chroma collection built by ingest.py.

The retriever owns the embedding model and the Chroma client. Phase 5 will
extend it with explicit-section detection and cross-encoder reranking.
"""
from __future__ import annotations

from dataclasses import dataclass

import chromadb
from sentence_transformers import SentenceTransformer

from backend.app import config


@dataclass(frozen=True)
class RetrievedChunk:
    """One Chroma hit, flattened. ``distance`` is cosine distance
    (≈ 1 − cosine similarity)."""
    chunk_id: str
    source: str
    section_number: str
    marginal_heading: str
    chapter: str
    chapter_title: str
    part: int
    text: str
    distance: float


class Retriever:
    def __init__(
        self,
        collection: chromadb.Collection | None = None,
        model: SentenceTransformer | None = None,
    ) -> None:
        if collection is None:
            client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
            collection = client.get_collection(config.COLLECTION_NAME)
        if model is None:
            model = SentenceTransformer(config.EMBED_MODEL_NAME)
        self.collection = collection
        self.model = model

    def search(
        self,
        query: str,
        k: int = config.DEFAULT_TOP_K,
        where: dict | None = None,
    ) -> list[RetrievedChunk]:
        """Run an embedding-based similarity search. ``where`` is forwarded
        as a Chroma metadata filter, e.g. ``{"source": "BNS"}``."""
        q_emb = self.model.encode(
            [config.BGE_QUERY_INSTRUCTION + query],
            normalize_embeddings=True,
        )
        r = self.collection.query(
            query_embeddings=q_emb.tolist(),
            n_results=k,
            where=where,
            include=["metadatas", "documents", "distances"],
        )
        ids = r.get("ids", [[]])[0]
        docs = r["documents"][0]
        mds = r["metadatas"][0]
        dists = r["distances"][0]
        out: list[RetrievedChunk] = []
        for i, md in enumerate(mds):
            out.append(RetrievedChunk(
                chunk_id=ids[i] if i < len(ids) else "",
                source=md["source"],
                section_number=md["section_number"],
                marginal_heading=(md.get("marginal_heading") or "").strip(),
                chapter=(md.get("chapter") or "").strip(),
                chapter_title=(md.get("chapter_title") or "").strip(),
                part=int(md.get("part", 1)),
                text=docs[i],
                distance=float(dists[i]),
            ))
        return out
