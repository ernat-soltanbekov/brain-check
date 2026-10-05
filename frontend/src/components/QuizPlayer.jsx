import { useEffect, useRef, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { ArrowLeft, ArrowRight, Check, Clock3, Send } from 'lucide-react'
import { api } from '../utils/apiClient'
import { useQuizSession } from '../hooks/useQuizSession'
import { ErrorMessage, ModeBadge } from './UI'
export default function QuizPlayer({ quiz }) {
  const { session, update, clear } = useQuizSession()
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(null),
    [confirm, setConfirm] = useState(false)
  const locked = useRef(false),
    lastTick = useRef(Date.now())
  const navigate = useNavigate()
  useEffect(() => {
    const timer = setInterval(() => {
      const now = Date.now(),
        seconds = Math.floor((now - lastTick.current) / 1000)
      if (!seconds) return
      lastTick.current = now
      if (document.hidden || locked.current) return
      update((s) => ({
        ...s,
        answers: s.answers.map((a, i) =>
          i === s.index ? { ...a, timeSpent: Math.min(86400, a.timeSpent + seconds) } : a,
        ),
      }))
    }, 1000)
    const reset = () => {
      lastTick.current = Date.now()
    }
    document.addEventListener('visibilitychange', reset)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', reset)
    }
  }, [])
  const question = quiz.questions[session.index]
  const answered = session.answers.filter((a) => a.selectedAnswer.trim()).length
  const totalTime = session.answers.reduce((sum, a) => sum + a.timeSpent, 0)
  async function submit() {
    if (locked.current) return
    locked.current = true
    setBusy(true)
    setError(null)
    // Freeze the entire payload and key. A timed-out response may already be saved.
    const pending = session.pending || {
      key: crypto.randomUUID(),
      body: { quizId: quiz.id, answers: session.answers },
    }
    update((s) => ({ ...s, pending }))
    try {
      const result = await api(`/quizzes/${quiz.id}/submit/`, {
        method: 'POST',
        body: pending.body,
        headers: { 'Idempotency-Key': pending.key },
      })
      clear()
      await navigate({ to: '/results/$id', params: { id: String(result.id) } })
    } catch (e) {
      setError(e)
      setBusy(false)
      locked.current = false
    }
  }
  return (
    <div className="player">
      <div className="player-meta">
        <span className="difficulty">{quiz.difficulty}</span>
        <ModeBadge mode={quiz.ai_mode} notice={quiz.ai_notice} />
        <span className="timer">
          <Clock3 size={17} />
          {Math.floor(totalTime / 60)}:{String(totalTime % 60).padStart(2, '0')}
        </span>
      </div>
      <h1>{quiz.title}</h1>
      <div className="progress-label">
        <span>
          Question {session.index + 1} of {quiz.questions.length}
        </span>
        <span>{answered} answered</span>
      </div>
      <progress max={quiz.questions.length} value={answered} aria-label="Answered questions" />
      <div className="question-panel">
        <p className="eyebrow">
          {question.type === 'multiple_choice' ? 'CHOOSE ONE ANSWER' : 'EXPLAIN IN YOUR OWN WORDS'}
        </p>
        <h2>{question.text}</h2>
        {question.type === 'multiple_choice' ? (
          <fieldset disabled={busy || !!session.pending}>
            <legend className="sr-only">Choose one answer</legend>
            {question.options.map((option, index) => (
              <label
                className={`option ${session.answers[session.index].selectedAnswer === option ? 'selected' : ''}`}
                key={option}
              >
                <input
                  type="radio"
                  name={`question-${question.id}`}
                  value={option}
                  checked={session.answers[session.index].selectedAnswer === option}
                  onChange={() =>
                    update((s) => ({
                      ...s,
                      answers: s.answers.map((a, i) =>
                        i === s.index ? { ...a, selectedAnswer: option } : a,
                      ),
                    }))
                  }
                />
                <span className="option-letter">{String.fromCharCode(65 + index)}</span>
                <span>{option}</span>
                {session.answers[session.index].selectedAnswer === option && <Check size={18} />}
              </label>
            ))}
          </fieldset>
        ) : (
          <label className="field">
            Your answer
            <textarea
              maxLength={4000}
              rows={5}
              disabled={busy || !!session.pending}
              value={session.answers[session.index].selectedAnswer}
              onChange={(e) => {
                const value = e.target.value
                update((s) => ({
                  ...s,
                  answers: s.answers.map((a, i) =>
                    i === s.index ? { ...a, selectedAnswer: value } : a,
                  ),
                }))
              }}
              placeholder="Focus on the concept. Your own words are welcome."
            />
          </label>
        )}
        <div className="player-navigation">
          <button
            className="secondary"
            disabled={busy || session.index === 0}
            onClick={() => update((s) => ({ ...s, index: s.index - 1 }))}
          >
            <ArrowLeft size={17} /> Previous
          </button>
          {session.index < quiz.questions.length - 1 ? (
            <button disabled={busy} onClick={() => update((s) => ({ ...s, index: s.index + 1 }))}>
              Next question <ArrowRight size={17} />
            </button>
          ) : (
            <button disabled={busy} onClick={() => setConfirm(true)}>
              Review & submit <Send size={16} />
            </button>
          )}
        </div>
      </div>
      <nav className="question-dots" aria-label="Question navigation">
        {quiz.questions.map((q, index) => (
          <button
            key={q.id}
            aria-label={`Question ${index + 1}`}
            aria-current={index === session.index ? 'step' : undefined}
            className={`${index === session.index ? 'current' : ''} ${session.answers[index].selectedAnswer ? 'answered' : ''}`}
            disabled={busy}
            onClick={() => update((s) => ({ ...s, index }))}
          >
            {index + 1}
          </button>
        ))}
      </nav>
      <p className="muted small centered">
        Your answers stay in this browser session when you refresh. Active time pauses when the tab
        is hidden.
      </p>
      {confirm && (
        <section className="panel submit-panel" aria-label="Submit confirmation">
          <h2>Ready to check your understanding?</h2>
          <p>
            {answered} of {quiz.questions.length} answered. {quiz.questions.length - answered}{' '}
            skipped answers will count as incorrect.
          </p>
          {session.pending && (
            <p className="notice">
              Submission is frozen for safe retry. The same key prevents duplicate attempts.
            </p>
          )}
          <ErrorMessage error={error} />
          <button onClick={submit} disabled={busy}>
            <Send size={17} />
            {busy
              ? 'Checking your answers…'
              : session.pending
                ? 'Retry saved submission'
                : 'Submit answers'}
          </button>
        </section>
      )}
    </div>
  )
}
