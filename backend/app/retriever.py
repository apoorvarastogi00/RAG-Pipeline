"""Two-stage retrieval over the Chroma index built by ingest.py.

Phase 5 adds three things on top of the Phase 4 bi-encoder search:

1. **Reranking** — a wide candidate pool is pulled with bge-base, then
   re-scored by the ``bge-reranker-base`` cross-encoder; the top results win.
2. **Explicit-section detection** — if the query names a section
   ("Section 103", "s. 111", "BNSS 187"), that exact section is fetched by
   metadata and pinned to the top of the results, merged with semantic hits.
3. **Per-Act candidate pools** — dense candidates are pulled separately from
   BNS and BNSS so cross-document questions surface both Acts. A document
   named in the query ("under the BNSS …") restricts retrieval to that Act.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace

import chromadb
from sentence_transformers import CrossEncoder, SentenceTransformer

from backend.app import config


@dataclass(frozen=True)
class RetrievedChunk:
    """One Chroma hit, flattened. ``distance`` is cosine distance
    (≈ 1 − cosine similarity); ``rerank_score`` is the cross-encoder logit
    (higher = more relevant) and is ``None`` until reranking runs.
    ``forced`` marks chunks pulled by explicit-section detection."""
    chunk_id: str
    source: str
    section_number: str
    marginal_heading: str
    chapter: str
    chapter_title: str
    part: int
    text: str
    distance: float
    rerank_score: float | None = None
    forced: bool = False


# A section number anywhere in the corpus is 1–3 digits (BNS ≤ 358, BNSS ≤ 531).
# With an explicit source: "BNS 103", "BNS s.103", "BNSS section 187", "bnss s. 187".
_REF_WITH_SOURCE = re.compile(
    r"\b(BNS|BNSS)\s*(?:s\.?|sec(?:tion|\.)?)?\s*(\d{1,3})\b",
    re.IGNORECASE,
)
# Without a source: "section 103", "s.103", "sec 111".
_REF_GENERIC = re.compile(
    r"\b(?:s\.|section|sec\.?)\s*(\d{1,3})\b",
    re.IGNORECASE,
)
_HAS_BNS  = re.compile(r"\bBNS\b",  re.IGNORECASE)
_HAS_BNSS = re.compile(r"\bBNSS\b", re.IGNORECASE)


def detect_section_refs(query: str) -> list[tuple[str | None, str]]:
    """Return ordered, deduplicated (source_or_None, section_number) refs the
    query names explicitly. ``source`` is "BNS"/"BNSS" when the ref carries
    one, else None (caller fetches both Acts for that number)."""
    refs: list[tuple[str | None, str]] = []
    spans: list[tuple[int, int]] = []
    for m in _REF_WITH_SOURCE.finditer(query):
        key = (m.group(1).upper(), m.group(2))
        if key not in refs:
            refs.append(key)
        spans.append(m.span())
    for m in _REF_GENERIC.finditer(query):
        # skip if this number was already captured as part of a sourced ref
        if any(s <= m.start() and m.end() <= e for s, e in spans):
            continue
        key = (None, m.group(1))
        if key not in refs:
            refs.append(key)
    return refs


def detect_source_hint(query: str) -> str | None:
    """If the query names exactly one Act, return it; else None."""
    has_bns = _HAS_BNS.search(query) is not None
    has_bnss = _HAS_BNSS.search(query) is not None
    if has_bnss and not has_bns:
        return "BNSS"
    if has_bns and not has_bnss:
        return "BNS"
    return None


class Retriever:
    def __init__(
        self,
        collection: chromadb.Collection | None = None,
        model: SentenceTransformer | None = None,
        reranker: CrossEncoder | None = None,
        use_reranker: bool = config.USE_RERANKER,
    ) -> None:
        if collection is None:
            client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
            collection = client.get_collection(config.COLLECTION_NAME)
        if model is None:
            model = SentenceTransformer(config.EMBED_MODEL_NAME)
        self.collection = collection
        self.model = model
        self.use_reranker = use_reranker
        if use_reranker and reranker is None:
            reranker = CrossEncoder(config.RERANKER_MODEL_NAME)
        self.reranker = reranker

    # ------------------------------------------------------------ internals

    def _row_to_chunk(self, md: dict, doc: str, dist: float,
                      chunk_id: str, forced: bool = False) -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id=chunk_id,
            source=md["source"],
            section_number=md["section_number"],
            marginal_heading=(md.get("marginal_heading") or "").strip(),
            chapter=(md.get("chapter") or "").strip(),
            chapter_title=(md.get("chapter_title") or "").strip(),
            part=int(md.get("part", 1)),
            text=doc,
            distance=dist,
            forced=forced,
        )

    def _dense(self, query: str, n: int, where: dict | None) -> list[RetrievedChunk]:
        q_emb = self.model.encode(
            [config.BGE_QUERY_INSTRUCTION + query],
            normalize_embeddings=True,
        )
        r = self.collection.query(
            query_embeddings=q_emb.tolist(),
            n_results=n,
            where=where,
            include=["metadatas", "documents", "distances"],
        )
        ids, docs = r.get("ids", [[]])[0], r["documents"][0]
        mds, dists = r["metadatas"][0], r["distances"][0]
        return [self._row_to_chunk(mds[i], docs[i], float(dists[i]), ids[i])
                for i in range(len(mds))]

    def _fetch_section(self, source: str, number: str) -> list[RetrievedChunk]:
        """Pull every chunk (all parts) of one exact section by metadata."""
        r = self.collection.get(
            where={"$and": [{"source": source}, {"section_number": number}]},
            include=["metadatas", "documents"],
        )
        ids, docs, mds = r["ids"], r["documents"], r["metadatas"]
        out = [self._row_to_chunk(mds[i], docs[i], 0.0, ids[i], forced=True)
               for i in range(len(ids))]
        out.sort(key=lambda c: c.part)
        return out

    def _rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks or self.reranker is None:
            return chunks
        scores = self.reranker.predict([(query, c.text) for c in chunks])
        scored = [replace(c, rerank_score=float(s)) for c, s in zip(chunks, scores)]
        scored.sort(key=lambda c: c.rerank_score, reverse=True)
        return scored

    @staticmethod
    def _dedupe(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        seen: set[str] = set()
        out: list[RetrievedChunk] = []
        for c in chunks:
            if c.chunk_id not in seen:
                seen.add(c.chunk_id)
                out.append(c)
        return out

    # ------------------------------------------------------------ public API

    def search(
        self,
        query: str,
        k: int = config.RERANK_TOP_K,
        candidate_pool: int = config.CANDIDATE_POOL_PER_SOURCE,
        max_parts_per_section: int = 2,
    ) -> list[RetrievedChunk]:
        """Full Phase 5 pipeline: explicit-section + per-Act dense pool ->
        rerank -> pin forced sections -> diversity-capped top-k.

        ``max_parts_per_section`` caps how many parts of the same section the
        semantic results may contribute, so a long split section (e.g. BNS
        s.2 "Definitions", 10 parts) can't crowd out other relevant sections
        for a multi-section query. Explicitly-named sections bypass the cap —
        if the user asked for s.187, they get all of it."""
        source_hint = detect_source_hint(query)
        refs = detect_section_refs(query)

        # 1. Explicit sections (pinned). Respect a source hint; otherwise an
        #    unsourced "section 103" pulls BOTH Acts (collision-safe).
        forced: list[RetrievedChunk] = []
        for ref_src, num in refs:
            targets = [ref_src] if ref_src else (
                [source_hint] if source_hint else ["BNS", "BNSS"]
            )
            for src in targets:
                forced.extend(self._fetch_section(src, num))

        # 2. Dense candidate pool — per Act unless the query names one.
        candidates: list[RetrievedChunk] = []
        if source_hint:
            candidates += self._dense(query, candidate_pool, {"source": source_hint})
        else:
            candidates += self._dense(query, candidate_pool, {"source": "BNS"})
            candidates += self._dense(query, candidate_pool, {"source": "BNSS"})

        # 3. Rerank the union of dense candidates (forced sections are pinned
        #    separately so they can't be dropped by the cross-encoder).
        forced_ids = {c.chunk_id for c in forced}
        dense_only = [c for c in candidates if c.chunk_id not in forced_ids]
        reranked = (self._rerank(query, self._dedupe(dense_only))
                    if self.use_reranker else self._dedupe(dense_only))

        # 4. Forced sections first (all their parts), then fill from the
        #    reranked list with a per-section parts cap for diversity.
        result: list[RetrievedChunk] = list(forced)
        parts_seen: dict[tuple[str, str], int] = {}
        for c in result:
            key = (c.source, c.section_number)
            parts_seen[key] = parts_seen.get(key, 0) + 1
        for c in reranked:
            if len(result) >= k:
                break
            key = (c.source, c.section_number)
            if parts_seen.get(key, 0) >= max_parts_per_section:
                continue
            result.append(c)
            parts_seen[key] = parts_seen.get(key, 0) + 1
        return self._dedupe(result)[:k]

    def semantic_only(
        self,
        query: str,
        k: int = config.DEFAULT_TOP_K,
        where: dict | None = None,
    ) -> list[RetrievedChunk]:
        """Phase 4 behaviour — single dense search, no rerank, no explicit
        handling. Kept for before/after comparison and as a fallback."""
        return self._dense(query, k, where)
