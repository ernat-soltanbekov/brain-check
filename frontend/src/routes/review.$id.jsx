import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { Save } from 'lucide-react'
import { requireAuth } from '../utils/guards'
import { api } from '../utils/apiClient'
import { useApi } from '../hooks/useApi'
import { Loading, ErrorMessage, ModeBadge, PageHeading } from '../components/UI'
export const Route = createFileRoute('/review/$id')({ beforeLoad: requireAuth, component: Review })
function Review() {
  const { id } = Route.useParams(),
    { data, loading, error, reload } = useApi(`/quizzes/${id}/review/`)
  return loading ? (
    <Loading />
  ) : error ? (
    <ErrorMessage error={error} retry={reload} />
  ) : (
    <Editor key={`${data.id}.${data.version}`} quiz={data} />
  )
}
function Editor({ quiz }) {
  const [draft, setDraft] = useState(quiz),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(null)
  const navigate = useNavigate()
  function editQuestion(index, key, value) {
    setDraft((s) => ({
      ...s,
      questions: s.questions.map((q, i) => (i === index ? { ...q, [key]: value } : q)),
    }))
  }
  async function save(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api(`/quizzes/${quiz.id}/`, {
        method: 'PATCH',
        body: {
          title: draft.title,
          version: quiz.version,
          status: 'published',
          questions: draft.questions.map(({ type, text, options, expected, source_quote }) => ({
            type,
            text,
            options,
            expected,
            source_quote,
          })),
        },
      })
      await navigate({ to: '/quiz/$id', params: { id: String(quiz.id) } })
    } catch (e) {
      setError(e)
      setBusy(false)
    }
  }
  return (
    <form onSubmit={save}>
      <PageHeading
        eyebrow="REVIEW BEFORE YOU PRACTICE"
        title="Make the questions yours."
        text="Check the source, refine the wording, and verify every expected answer."
      />
      <div className="notice">
        <ModeBadge mode={quiz.ai_mode} />
        {quiz.ai_notice}
      </div>
      <ErrorMessage error={error} />
      <fieldset disabled={busy || !quiz.editable}>
        <label className="field title-field">
          Quiz title
          <input
            required
            maxLength={180}
            value={draft.title}
            onChange={(e) => setDraft({ ...draft, title: e.target.value })}
          />
        </label>
        {draft.questions.map((q, index) => (
          <section className="panel editor-question" key={q.id}>
            <p className="eyebrow">
              QUESTION {index + 1} · {q.type.replace('_', ' ')}
            </p>
            <label className="field">
              Question text
              <textarea
                required
                maxLength={2000}
                rows={2}
                value={q.text}
                onChange={(e) => editQuestion(index, 'text', e.target.value)}
              />
            </label>
            {q.type === 'multiple_choice' && (
              <div className="form-grid">
                {q.options.map((option, optionIndex) => (
                  <label className="field" key={optionIndex}>
                    Option {String.fromCharCode(65 + optionIndex)}
                    <input
                      required
                      maxLength={2000}
                      value={option}
                      onChange={(e) =>
                        editQuestion(
                          index,
                          'options',
                          q.options.map((o, i) => (i === optionIndex ? e.target.value : o)),
                        )
                      }
                    />
                  </label>
                ))}
              </div>
            )}
            <label className="field">
              Expected answer
              {q.type === 'multiple_choice' ? (
                <select
                  value={q.expected}
                  onChange={(e) => editQuestion(index, 'expected', e.target.value)}
                >
                  {!q.options.includes(q.expected) && (
                    <option value={q.expected}>Select a valid option</option>
                  )}
                  {q.options.map((o) => (
                    <option key={o} value={o}>
                      {o}
                    </option>
                  ))}
                </select>
              ) : (
                <textarea
                  required
                  rows={2}
                  maxLength={2000}
                  value={q.expected}
                  onChange={(e) => editQuestion(index, 'expected', e.target.value)}
                />
              )}
            </label>
            {q.source_quote && (
              <blockquote className="source-quote">
                <span className="tiny-label">SOURCE EVIDENCE</span>
                <p>{q.source_quote}</p>
              </blockquote>
            )}
          </section>
        ))}
        <button disabled={busy || !quiz.editable}>
          <Save size={18} />
          {busy ? 'Saving…' : 'Save quiz & start practice'}
        </button>
      </fieldset>
      {!quiz.editable && (
        <div className="notice">
          This quiz already has attempts and cannot be edited. Generate a new quiz to make changes.
        </div>
      )}
    </form>
  )
}
