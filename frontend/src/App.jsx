import { useEffect, useRef, useState } from 'react'
import { postChat, checkHealth, BASE_URL } from './api.js'
import Message from './components/Message.jsx'

const SUGGESTIONS = [
  { icon: '§', label: 'Punishment for murder', query: 'What is the punishment for murder?' },
  { icon: 'BN', label: 'Explain BNSS s.187', query: 'Explain BNSS s. 187' },
  {
    icon: 'TR',
    label: 'Murder and trial procedure',
    query: 'What is the punishment for murder and how is the trial conducted?',
  },
  {
    icon: 'Δ',
    label: 'Murder vs culpable homicide',
    query: 'Difference between murder and culpable homicide?',
  },
]

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [health, setHealth] = useState('checking') // checking | ok | down
  const threadRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    checkHealth()
      .then(() => setHealth('ok'))
      .catch(() => setHealth('down'))
  }, [])

  useEffect(() => {
    // Keep the latest message in view.
    const el = threadRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, loading])

  useEffect(() => {
    function onKeyDown(e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  async function send(text) {
    const query = text.trim()
    if (!query || loading) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: query }])
    setLoading(true)
    try {
      const data = await postChat(query)
      setMessages((m) => [...m, { role: 'assistant', ...data }])
    } catch (err) {
      setMessages((m) => [...m, { role: 'error', text: err.message }])
    } finally {
      setLoading(false)
    }
  }

  function onSubmit(e) {
    e.preventDefault()
    send(input)
  }

  const empty = messages.length === 0
  const shortcut = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
    ? '⌘ K'
    : 'Ctrl K'

  const composer = (
    <form className={`composer ${empty ? 'composer--hero' : ''}`} onSubmit={onSubmit}>
      <span className="composer__search" aria-hidden>⌕</span>
      <input
        ref={inputRef}
        className="composer__input"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={health === 'down' ? 'Backend offline' : 'Ask about offences, procedure, bail, trial, or citations'}
        disabled={loading}
        autoFocus
      />
      <span className="composer__shortcut">{shortcut}</span>
      <button className="composer__send" type="submit" disabled={loading || !input.trim()} aria-label="Ask">
        {loading ? '…' : '→'}
      </button>
    </form>
  )

  return (
    <div className="app">
      <header className="header">
        <div className="header__title">
          <span className="brand-mark">LR</span>
          <div>
            <h1>LegalResearch.AI</h1>
            <span className="header__subtitle">BNS and BNSS research copilot</span>
          </div>
        </div>
        <div className="context-pill">BNS + BNSS, 2023</div>
        <div className={`status status--${health}`} title={BASE_URL}>
          <span className="status__dot" />
          {health === 'ok' ? 'Live backend' : health === 'down' ? 'Backend offline' : 'Connecting'}
        </div>
      </header>

      <main className="thread" ref={threadRef}>
        {empty && (
          <div className="welcome">
            <div className="metadata">
              <span>Dataset: Bharatiya Nyaya Sanhita and BNSS</span>
              <span>Updated: 2026</span>
              <span>Section-cited answers</span>
            </div>
            <div className="hero-card">
              <p className="eyebrow">Indian criminal law research</p>
              <h2>Legal Research Copilot</h2>
              <p>
                Ask a question and get a grounded answer with Act-qualified
                section citations from the BNS and BNSS.
              </p>
              {composer}
              <div className="suggestions" aria-label="Suggested prompts">
                {SUGGESTIONS.map((s) => (
                  <button key={s.query} className="suggestion" onClick={() => send(s.query)} disabled={health === 'down'}>
                    <span className="suggestion__icon">{s.icon}</span>
                    <span>{s.label}</span>
                    <span className="suggestion__arrow" aria-hidden>→</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <Message key={i} message={m} />
        ))}

        {loading && (
          <div className="row row--assistant">
            <div className="bubble bubble--assistant">
              <div className="typing">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}
      </main>

      {!empty && composer}
    </div>
  )
}
