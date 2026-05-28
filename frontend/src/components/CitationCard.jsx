import { useState } from 'react'

// One expandable citation. Collapsed: source badge + section + heading.
// Expanded: chapter (if any) + snippet from the cited section.
export default function CitationCard({ citation }) {
  const [open, setOpen] = useState(false)
  const { source, section_number, marginal_heading, chapter, snippet } = citation

  return (
    <div className={`citation ${open ? 'citation--open' : ''}`}>
      <button
        type="button"
        className="citation__head"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className={`badge badge--${source.toLowerCase()}`}>{source}</span>
        <span className="citation__ref">s.{section_number}</span>
        <span className="citation__heading">
          {marginal_heading || <em>(no marginal heading)</em>}
        </span>
        <span className="citation__chevron" aria-hidden>{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="citation__body">
          {chapter && <div className="citation__chapter">{chapter}</div>}
          <p className="citation__snippet">{snippet}</p>
        </div>
      )}
    </div>
  )
}
