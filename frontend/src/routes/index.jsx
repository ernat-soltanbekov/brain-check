import { createFileRoute, Link } from '@tanstack/react-router'
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  ChartNoAxesCombined,
  Flame,
  Target,
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useApi } from '../hooks/useApi'
import QuizCard from '../components/QuizCard'
import PerformanceChart from '../components/PerformanceChart'
import { ErrorMessage, Loading } from '../components/UI'
export const Route = createFileRoute('/')({ component: Home })
function Home() {
  const { user } = useAuth()
  const { data: history, error, loading, reload } = useApi(user ? '/profile/history/' : null)
  const { data: quizzes } = useApi(user ? '/quizzes/?status=published' : null)
  const attempts = history?.attempts || []
  const average = attempts.length
    ? Math.round(attempts.reduce((sum, a) => sum + a.score, 0) / attempts.length)
    : null
  return (
    <>
      <div className="welcome-row">
        <div>
          <p className="eyebrow">THE DAILY PRACTICE</p>
          <h1>{user ? `Welcome back, ${user.username}.` : 'A stronger mind starts here.'}</h1>
        </div>
        <span className="date-label">
          {new Intl.DateTimeFormat('en-GB', {
            day: 'numeric',
            month: 'long',
            year: 'numeric',
            timeZone: 'Asia/Almaty',
          }).format(new Date())}
        </span>
      </div>
      <section className="hero">
        <div className="hero-copy">
          <span className="hero-tag">
            <span /> DISCIPLINE, APPLIED TO LEARNING
          </span>
          <h2>
            Train the mind.
            <br />
            <em>Trust the process.</em>
          </h2>
          <p>
            Your notes. Better questions. A clearer understanding.
            <br />
            Make every session a deliberate step forward.
          </p>
          <Link className="button light" to={user ? '/quizzes' : '/login'}>
            Start a practice session <ArrowUpRight size={20} />
          </Link>
          <div className="hero-note">
            <span>01</span> UNDERSTAND <i /> <span>02</span> PRACTICE <i /> <span>03</span> REFINE
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="orbit orbit-three" />
          <div className="orbit-center">
            <Target size={48} strokeWidth={1} />
          </div>
          <span className="art-north">N</span>
          <span className="art-coordinates">ASTANA · KAZAKHSTAN</span>
          <span className="art-cross cross-one">+</span>
          <span className="art-cross cross-two">+</span>
          <div className="orbit-dot" />
        </div>
      </section>
      <ErrorMessage error={error} retry={reload} />
      {loading && user ? (
        <Loading />
      ) : (
        <div className="stats-grid">
          <div className="stat">
            <span className="stat-icon">
              <Target size={20} />
            </span>
            <div>
              <p>Sessions completed</p>
              <strong>{history?.totalAttempts ?? '—'}</strong>
              <small>{user ? 'Every repetition counts' : 'Your progress, recorded'}</small>
            </div>
          </div>
          <div className="stat">
            <span className="stat-icon peach">
              <ChartNoAxesCombined size={20} />
            </span>
            <div>
              <p>Average accuracy</p>
              <strong>
                {average ?? '—'}
                {average !== null && <span>%</span>}
              </strong>
              <small>Across your recent sessions</small>
            </div>
          </div>
          <div className="stat">
            <span className="stat-icon lavender">
              <BookOpen size={20} />
            </span>
            <div>
              <p>Topics practiced</p>
              <strong>{user ? new Set(attempts.map((a) => a.topic)).size : '—'}</strong>
              <small>Understanding over memorization</small>
            </div>
          </div>
        </div>
      )}
      <div className="section-heading">
        <div>
          <p className="eyebrow">YOUR NEXT REPETITION</p>
          <h2>Step onto the training ground</h2>
        </div>
        <Link to="/quizzes" className="text-button">
          View all quizzes <ArrowRight size={17} />
        </Link>
      </div>
      {quizzes ? (
        <div className="quiz-grid">
          {quizzes.results.slice(0, 3).map((quiz, i) => (
            <QuizCard key={quiz.id} quiz={quiz} index={i} />
          ))}
        </div>
      ) : (
        <div className="guest-topics">
          {['Python foundations', 'Embeddings & RAG', 'Prompting & Go'].map((topic, i) => (
            <Link to="/login" key={topic}>
              <span>0{i + 1}</span>
              <h3>{topic}</h3>
              <ArrowUpRight size={24} />
            </Link>
          ))}
        </div>
      )}
      <div className="home-lower">
        <section className="panel">
          <div className="section-heading">
            <h2>The long game</h2>
            <span className="tiny-label">RECENT PROGRESS</span>
          </div>
          <PerformanceChart attempts={attempts} />
        </section>
        <section className="practice-note">
          <Flame size={24} />
          <p className="eyebrow">A NOTE ON PRACTICE</p>
          <blockquote>
            “The discipline of showing up becomes the freedom to move forward.”
          </blockquote>
          <p>
            Military experience. Martial arts every morning since 2008. The same patient repetition,
            now applied to technology.
          </p>
          <span>YERNAT SOLTANBEKOV · GHOSTOFASTANA</span>
        </section>
      </div>
    </>
  )
}
