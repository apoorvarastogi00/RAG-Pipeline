# Backend image — FastAPI + RAG over BNS/BNSS.
#
# IMPORTANT: build context is the REPOSITORY ROOT, not backend/.
#   docker build -f backend/Dockerfile -t legal-rag-backend .
# (render.yaml sets dockerContext: . accordingly.) This is so the `backend`
# Python package resolves as `backend.app.*` and the committed data artifacts
# under backend/data/ are available at image-build time.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.hf_cache \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

# --- Python dependencies -----------------------------------------------------
# Install the CPU-only torch wheel first so the later `-r requirements.txt`
# sees torch already satisfied and does NOT pull the multi-GB CUDA build.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --upgrade pip \
    && pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r backend/requirements.txt

# --- Application code + committed data ---------------------------------------
# sections.json and chunks.json are committed, so the index is rebuilt from
# chunks.json WITHOUT re-parsing the PDFs. Sources/ is copied only as a
# fallback for regenerating the JSON artifacts if they were ever missing.
COPY backend ./backend
COPY Sources ./Sources

# --- Bake the vector index + model cache into the image ----------------------
# `ingest` reads the committed chunks.json (idempotent; no PDF re-parse) and
# embeds all chunks into backend/data/chroma/, while downloading + caching the
# embedding model. The second line warms the reranker cache. Result: zero
# model downloads and zero embedding work at container start — fast, stable
# cold starts. No GROQ_API_KEY is needed here (ingest never calls the LLM).
RUN python -m backend.app.ingest \
    && python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-base')"

# Render injects $PORT; default to 8000 for local `docker run`.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
