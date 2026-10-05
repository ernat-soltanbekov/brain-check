import { CheckCircle2, CircleX, ArrowRight } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { ModeBadge } from './UI'
import AIFeedback from './AIFeedback'
export default function ResultsDashboard({ attempt }) {
  return (
    <>
      <div className="result-hero">
        <div className="score-ring" style={{ '--score': `${attempt.score}%` }}>
          <div>
            <strong>
              {attempt.score}
              <small>%</small>
            </strong>
            <span>OBJECTIVE SCORE</span>
          </div>
        </div>
        <div>
          <p className="eyebrow">SESSION COMPLETE</p>
          <h1>
            {attempt.score >= 70 ? 'Practice becomes progress.' : 'Every gap is a starting point.'}
          </h1>
          <p>
            {attempt.correct_count} of {attempt.total_questions} correct · {attempt.time_spent}s
            active time
          </p>
          <ModeBadge mode={attempt.ai_mode} />
          <p className="muted small">
            Short answers count as correct at a model grade of 0.70 or above.
            <br />
            Your final score is correct answers ÷ all questions × 100.
          </p>
        </div>
      </div>
      {['mock', 'fallback'].includes(attempt.ai_mode) && (
        <div className="notice">
          This attempt includes offline keyword grading. Its result is practice feedback, not a
          semantic model evaluation.
        </div>
      )}
      <AIFeedback attempt={attempt} />
      <section className="answer-review">
        <div className="section-heading">
          <h2>The answer breakdown</h2>
          <Link className="text-button" to="/quizzes">
            Back to practice <ArrowRight size={16} />
          </Link>
        </div>
        {attempt.answers.map((answer, index) => (
          <article className="answer-card" key={answer.questionId}>
            <div className="answer-title">
              {answer.verdict === 'correct' ? (
                <CheckCircle2 className="correct" />
              ) : (
                <CircleX className="incorrect" />
              )}
              <h3>
                <span>{String(index + 1).padStart(2, '0')}.</span> {answer.question}
              </h3>
              <span className={`verdict ${answer.verdict}`}>{answer.verdict}</span>
            </div>
            <div className="answer-columns">
              <div>
                <span className="tiny-label">YOUR ANSWER</span>
                <p>{answer.selectedAnswer || 'Skipped'}</p>
              </div>
              <div>
                <span className="tiny-label">EXPECTED CONCEPT</span>
                <p>{answer.expected}</p>
              </div>
            </div>
            <div className="answer-explanation">
              <p>{answer.justification}</p>
              <span>
                {answer.type === 'short_answer'
                  ? `Meaning grade: ${answer.score.toFixed(2)} / 1 · `
                  : ''}
                {answer.timeSpent}s
              </span>
              <ModeBadge mode={answer.ai_mode} />
            </div>
          </article>
        ))}
      </section>
    </>
  )
}
