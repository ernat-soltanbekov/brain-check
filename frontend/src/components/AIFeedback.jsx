import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import { api } from '../utils/apiClient'
import { ErrorMessage, ModeBadge } from './UI'
export default function AIFeedback({ attempt }) {
  const [analysis, setAnalysis] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(null)
  async function load() {
    setBusy(true)
    setError(null)
    try {
      setAnalysis(
        await api(`/quizzes/${attempt.quizId}/analyze/`, {
          method: 'POST',
          body: { attemptId: attempt.id },
        }),
      )
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }
  return (
    <section className="panel feedback">
      <div className="section-heading">
        <h2>
          <Sparkles size={20} /> Reflect & improve
        </h2>
        {analysis && <ModeBadge mode={analysis.ai.mode} notice={analysis.ai.notice} />}
      </div>
      <ErrorMessage error={error} />
      {analysis ? (
        <>
          <div className="feedback-grid">
            {['strengths', 'weaknesses', 'recommendations'].map((key) => (
              <div key={key}>
                <h3>{key}</h3>
                <ul>
                  {analysis[key].map((line, i) => (
                    <li key={i}>{line}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <p className="next-step">{analysis.nextSteps}</p>
          <p className="muted small">
            Verified metrics: {analysis.overallScore}% · {analysis.correctCount}/
            {analysis.totalQuestions} correct · {analysis.timeSpent}s total. Numbers computed by
            Django.
          </p>
        </>
      ) : (
        <>
          <p className="muted">
            Turn this session into a concrete next step. Your score is computed by the backend; the
            model adds coaching.
          </p>
          <button onClick={load} disabled={busy}>
            <Sparkles size={17} />
            {busy ? 'Reflecting on your answers…' : 'Analyze this session'}
          </button>
        </>
      )}
    </section>
  )
}
