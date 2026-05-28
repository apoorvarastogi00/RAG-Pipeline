import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dev server runs on 5173; the backend is reached via VITE_API_BASE_URL
// (see .env.example), so no proxy is needed — the FastAPI app already sends
// permissive CORS headers.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
})
