import { useState } from 'react'
import { useNavigate, Link } from '@tanstack/react-router'
import { Sparkles, ArrowRight } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../utils/apiClient'
import { ErrorMessage } from './UI'
export default function GenerateForm() {
  const { data } = useApi('/material/')
  const [topic, setTopic] = useState('embeddings'),
    [difficulty, setDifficulty] = useState('beginner')
  const [count, setCount] = useState(5),
    [adaptive, setAdaptive] = useState(false)
  const [types, setTypes] = useState(['multiple_choice', 'short_answer'])
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(null)
  const navigate = useNavigate()
  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const quiz = await api('/quizzes/generate/', {
        method: 'POST',
        body: { topic, difficulty, count: Number(count), types, adaptive },
      })
      await navigate({ to: '/review/$id', params: { id: String(quiz.id) } })
    } catch (e) {
      setError(e)
      setBusy(false)
    }
  }
  return (
    <form className="panel generate-form" onSubmit={submit}>
      <div className="section-heading">
        <h2>
          <Sparkles size={20} /> Build a quiz from your notes
        </h2>
        <Link to="/material" className="text-button">
          Add study notes <ArrowRight size={16} />
        </Link>
      </div>
      <p className="muted">
        Questions are grounded in your saved material. Review and edit the draft before saving.
      </p>
      <ErrorMessage error={error} />
      <fieldset disabled={busy}>
        <div className="form-grid">
          <label className="field">
            Topic
            <input
              list="topics"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              maxLength={100}
              required
            />
            <datalist id="topics">
              {[...new Set(data?.results.map((m) => m.topic))].map((t) => (
                <option key={t} value={t} />
              ))}
            </datalist>
          </label>
          <label className="field">
            Difficulty
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              disabled={adaptive}
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </label>
          <label className="field">
            Questions
            <input
              type="number"
              min={types.length || 1}
              max={10}
              value={count}
              onChange={(e) => setCount(e.target.value)}
              required
            />
          </label>
        </div>
        <div className="form-options">
          {[
            ['multiple_choice', 'Multiple choice'],
            ['short_answer', 'Short answer'],
          ].map(([value, label]) => (
            <label className="checkbox-label" key={value}>
              <input
                type="checkbox"
                checked={types.includes(value)}
                onChange={(e) =>
                  setTypes((old) =>
                    e.target.checked ? [...old, value] : old.filter((x) => x !== value),
                  )
                }
              />
              {label}
            </label>
          ))}
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={adaptive}
              onChange={(e) => setAdaptive(e.target.checked)}
            />
            Adapt to my last five attempts
          </label>
        </div>
        <button disabled={busy || !types.length}>
          <Sparkles size={17} />
          {busy ? 'Generating your draft…' : 'Generate draft'}
        </button>
      </fieldset>
    </form>
  )
}
