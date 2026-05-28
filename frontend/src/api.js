// Thin client for the frozen Section 4 API contract.
//   POST /chat   { query }  -> { answer, citations[], retrieved_sections[], no_answer }
//   GET  /health            -> { status }
// Base URL is configurable so the same build points at local / deployed backends.

export const BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:7860'
).replace(/\/+$/, '')

export async function postChat(query, { signal } = {}) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
    signal,
  })
  if (!res.ok) {
    let detail = ''
    try {
      const body = await res.json()
      detail = typeof body?.detail === 'string' ? body.detail : JSON.stringify(body?.detail ?? '')
    } catch {
      /* non-JSON error body */
    }
    throw new Error(`Backend returned ${res.status}${detail ? ` — ${detail}` : ''}`)
  }
  return res.json()
}

export async function checkHealth({ signal } = {}) {
  const res = await fetch(`${BASE_URL}/health`, { signal })
  if (!res.ok) throw new Error(`Health check failed (${res.status})`)
  return res.json()
}
