import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { Plus, Search } from 'lucide-react'
import { requireAuth } from '../utils/guards'
import { useApi } from '../hooks/useApi'
import QuizCard from '../components/QuizCard'
import GenerateForm from '../components/GenerateForm'
import { PageHeading, Loading, ErrorMessage, EmptyState } from '../components/UI'
export const Route = createFileRoute('/quizzes')({ beforeLoad: requireAuth, component: Quizzes })
function Quizzes() {
  const [generate, setGenerate] = useState(false),
    [topic, setTopic] = useState(''),
    [search, setSearch] = useState(''),
    [page, setPage] = useState(1)
  const { data, error, loading, reload } = useApi(
    `/quizzes/?topic=${encodeURIComponent(topic)}&search=${encodeURIComponent(search)}&page=${page}`,
  )
  return (
    <>
      <PageHeading
        eyebrow="THE TRAINING GROUND"
        title="Practice library"
        text="Build confidence through deliberate, grounded practice."
        action={
          <button onClick={() => setGenerate(!generate)}>
            <Plus size={18} />
            {generate ? 'Close builder' : 'Build a quiz'}
          </button>
        }
      />
      {generate && <GenerateForm />}
      <div className="library-filters">
        <label className="search-field">
          <Search size={18} />
          <input
            aria-label="Search quizzes"
            placeholder="Search your practice library…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
          />
        </label>
        <label className="field compact">
          Topic
          <select
            value={topic}
            onChange={(e) => {
              setTopic(e.target.value)
              setPage(1)
            }}
          >
            <option value="">All topics</option>
            {['python data structures', 'embeddings', 'rag', 'prompting', 'go concurrency'].map(
              (t) => (
                <option value={t} key={t}>
                  {t}
                </option>
              ),
            )}
          </select>
        </label>
      </div>
      <ErrorMessage error={error} retry={reload} />
      {loading ? (
        <Loading />
      ) : data?.results.length ? (
        <>
          <div className="quiz-grid">
            {data.results.map((quiz, i) => (
              <QuizCard key={quiz.id} quiz={quiz} index={i} />
            ))}
          </div>
          <div className="pagination">
            <button
              className="secondary"
              disabled={!data.previous}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <span>
              Page {page} · {data.count} quizzes
            </span>
            <button
              className="secondary"
              disabled={!data.next}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </>
      ) : (
        !error && (
          <EmptyState title="A fresh page for your practice.">
            Add notes and generate your first quiz, or try another search.
          </EmptyState>
        )
      )}
    </>
  )
}
