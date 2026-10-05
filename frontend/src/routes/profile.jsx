import { createFileRoute, Link } from '@tanstack/react-router'
import { ArrowUpRight, Shield, TrendingUp } from 'lucide-react'
import { requireAuth } from '../utils/guards'
import { useApi } from '../hooks/useApi'
import PerformanceChart from '../components/PerformanceChart'
import RecommendationList from '../components/RecommendationList'
import { PageHeading, Loading, ErrorMessage, EmptyState, ModeBadge } from '../components/UI'
export const Route = createFileRoute('/profile')({ beforeLoad: requireAuth, component: Profile })
function Profile() {
  const { data, error, loading, reload } = useApi('/profile/history/')
  const level = useApi('/profile/difficulty/')
  return (
    <>
      <PageHeading
        eyebrow="THE LONG GAME"
        title="Your progress, with perspective."
        text="Measure understanding. Find the gaps. Keep showing up."
      />
      <section className="profile-banner">
        <span className="large-avatar">YS</span>
        <div>
          <p className="eyebrow">THE PERSON BEHIND THE PRACTICE</p>
          <h2>Yernat Soltanbekov</h2>
          <p>
            Military experience · Martial arts practitioner since 2008 · Tomorrow School student
          </p>
          <p className="small">
            Technical background. Candidate for the Astana Hub team, МИИЦР РК.
          </p>
        </div>
        <Shield size={34} />
      </section>
      <div className="profile-grid">
        <section className="panel">
          <div className="section-heading">
            <h2>
              <TrendingUp size={20} /> Progression
            </h2>
            <span className="tiny-label">{data?.totalAttempts || 0} SESSIONS</span>
          </div>
          {loading ? <Loading /> : <PerformanceChart attempts={data?.attempts || []} />}
          <ErrorMessage error={error} retry={reload} />
        </section>
        <section className="panel level-panel">
          <p className="eyebrow">CURRENT DIFFICULTY</p>
          {level.loading ? (
            <Loading label="Finding your level…" />
          ) : level.error ? (
            <ErrorMessage error={level.error} retry={level.reload} />
          ) : (
            <>
              <h2>{level.data?.difficulty}</h2>
              <p>{level.data?.reason}</p>
              <span className="muted small">
                Based on {level.data?.attemptsUsed} recent attempts
                {level.data?.averageScore != null ? ` · ${level.data.averageScore}% average` : ''}.
              </span>
              <ModeBadge mode={level.data?.ai.mode} />
            </>
          )}
          <Link to="/quizzes" className="text-button">
            Build an adaptive quiz <ArrowUpRight size={16} />
          </Link>
        </section>
      </div>
      <RecommendationList />
      <div className="section-heading">
        <h2>Your practice log</h2>
        <span className="tiny-label">LATEST 100 SESSIONS</span>
      </div>
      {data?.attempts.length ? (
        <div className="history-list">
          {data.attempts.map((a) => (
            <Link
              key={a.id}
              to="/results/$id"
              params={{ id: String(a.id) }}
              className="history-row"
            >
              <span className="history-score">
                {a.score}
                <small>%</small>
              </span>
              <div>
                <strong>{a.title}</strong>
                <p>
                  {new Date(a.created_at).toLocaleDateString('en-GB')} · {a.difficulty} ·{' '}
                  {a.time_spent}s
                </p>
              </div>
              <ModeBadge mode={a.ai_mode} />
              <ArrowUpRight size={19} />
            </Link>
          ))}
        </div>
      ) : (
        !loading && (
          <EmptyState title="Your first session is waiting.">
            Take a quiz to begin your practice log.
          </EmptyState>
        )
      )}
    </>
  )
}
