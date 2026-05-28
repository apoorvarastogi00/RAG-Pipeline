import { useEffect, useRef, useState } from 'react'
import { postChat, checkHealth, BASE_URL } from './api.js'
import Message from './components/Message.jsx'

const SUGGESTIONS = [
  'What is the punishment for murder under the BNS?',
  'Explain BNSS s. 187',
  'What is the punishment for murder and how is the trial conducted?',
  'Difference between murder and culpable homicide?',
]

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [health, setHealth] = useState('checking') // checking | ok | down
  const threadRef = useRef(null)

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

  return (
    <div className="app">
      <header className="header">
        <div className="header__title">
          <h1>Legal Research RAG</h1>
          <span className="header__subtitle">Bharatiya Nyaya Sanhita (BNS) · Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023</span>
        </div>
        <div className={`status status--${health}`} title={BASE_URL}>
          <span className="status__dot" />
          {health === 'ok' ? 'backend online' : health === 'down' ? 'backend offline' : 'connecting…'}
        </div>
      </header>

      <main className="thread" ref={threadRef}>
        {empty && (
          <div className="welcome">
            <h2>Ask about Indian criminal law</h2>
            <p>
              Answers are grounded only in the BNS (offences) and BNSS (procedure), 2023.
              Every citation is tagged with its Act because the two share section numbers.
            </p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="suggestion" onClick={() => send(s)} disabled={health === 'down'}>
                  {s}
                </button>
              ))}
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

      <form className="composer" onSubmit={onSubmit}>
        <input
          className="composer__input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={health === 'down' ? 'Backend offline — start the API first' : 'Ask a question about the BNS or BNSS…'}
          disabled={loading}
          autoFocus
        />
        <button className="composer__send" type="submit" disabled={loading || !input.trim()}>
          {loading ? '…' : 'Ask'}
        </button>
      </form>
    </div>
  )
}
