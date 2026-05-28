import CitationCard from './CitationCard.jsx'

// Renders one item in the thread. Three shapes:
//   { role: 'user', text }
//   { role: 'assistant', answer, citations, retrieved_sections, no_answer }
//   { role: 'error', text }
export default function Message({ message }) {
  if (message.role === 'user') {
    return (
      <div className="row row--user">
        <div className="bubble bubble--user">{message.text}</div>
      </div>
    )
  }

  if (message.role === 'error') {
    return (
      <div className="row row--assistant">
        <div className="bubble bubble--error">
          <strong>Couldn’t reach the backend.</strong>
          <div className="error-detail">{message.text}</div>
        </div>
      </div>
    )
  }

  // assistant
  const { answer, citations = [], retrieved_sections = [], no_answer } = message
  return (
    <div className="row row--assistant">
      <div className="bubble bubble--assistant">
        {no_answer && (
          <div className="noanswer-tag">Not found in the BNS / BNSS corpus</div>
        )}
        <div className="answer-text">{answer}</div>

        {!no_answer && citations.length > 0 && (
          <div className="citations">
            <div className="citations__label">
              Citations ({citations.length})
            </div>
            {citations.map((c, i) => (
              <CitationCard key={`${c.source}-${c.section_number}-${i}`} citation={c} />
            ))}
          </div>
        )}

        {retrieved_sections.length > 0 && (
          <details className="retrieved">
            <summary>Retrieved {retrieved_sections.length} sections</summary>
            <div className="retrieved__chips">
              {retrieved_sections.map((s, i) => (
                <span key={`${s.source}-${s.section_number}-${i}`} className="chip">
                  <span className={`badge badge--${s.source.toLowerCase()}`}>{s.source}</span>
                  s.{s.section_number}
                </span>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  )
}
