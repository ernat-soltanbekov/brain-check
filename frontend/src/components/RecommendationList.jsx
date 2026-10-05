import { Link } from '@tanstack/react-router'
import { ArrowUpRight } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { Loading, ErrorMessage, ModeBadge } from './UI'
export default function RecommendationList() {
  const { data, error, loading, reload } = useApi('/recommendations/')
  return (
    <section className="panel">
      <div className="section-heading">
        <h2>Your next move</h2>
        <span className="tiny-label">PERSONALIZED</span>
      </div>
      {loading ? (
        <Loading label="Finding your next practice…" />
      ) : error ? (
        <ErrorMessage error={error} retry={reload} />
      ) : (
        <>
          {data?.recommendations.map((r, i) => (
            <Link
              className="recommendation"
              key={r.quizId}
              to="/quiz/$id"
              params={{ id: String(r.quizId) }}
            >
              <span className="recommendation-number">0{i + 1}</span>
              <div>
                <strong>{r.title}</strong>
                <p>{r.reason}</p>
              </div>
              <ArrowUpRight size={18} />
            </Link>
          ))}
          {!data?.recommendations.length && (
            <p className="muted">Save a quiz to get recommendations.</p>
          )}
          <ModeBadge mode={data?.ai.mode} notice={data?.ai.notice} />
        </>
      )}
    </section>
  )
}
