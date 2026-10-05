import { AlertCircle, ArrowUpRight, LoaderCircle } from 'lucide-react'
export function Loading({ label = 'Preparing your workspace…' }) {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={22} />
      {label}
    </div>
  )
}
export function ErrorMessage({ error, retry }) {
  return error ? (
    <div className="error-box" role="alert">
      <AlertCircle size={20} />
      <div>
        {error.message || String(error)}
        {retry && (
          <button className="text-button" onClick={retry}>
            Try again <ArrowUpRight size={14} />
          </button>
        )}
      </div>
    </div>
  ) : null
}
export function ModeBadge({ mode, notice }) {
  return (
    <span className={`mode-badge ${mode === 'live' ? 'live' : ''}`} title={notice}>
      <span />
      {{
        live: 'Live model',
        mock: 'Offline practice',
        fallback: 'Fallback mode',
        configured: 'Model configured',
        deterministic: 'Exact scoring',
        curated: 'Reference quiz',
        manual: 'Your quiz',
      }[mode] || mode}
    </span>
  )
}
export function PageHeading({ eyebrow, title, text, action }) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        {text && <p className="muted">{text}</p>}
      </div>
      {action}
    </div>
  )
}
export function EmptyState({ title, children }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  )
}
