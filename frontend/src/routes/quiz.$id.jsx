import { createFileRoute, Link } from '@tanstack/react-router'
import { requireAuth } from '../utils/guards'
import { useApi } from '../hooks/useApi'
import { useAuth } from '../hooks/useAuth'
import { QuizSessionProvider } from '../hooks/useQuizSession'
import QuizPlayer from '../components/QuizPlayer'
import { Loading, ErrorMessage } from '../components/UI'
export const Route = createFileRoute('/quiz/$id')({ beforeLoad: requireAuth, component: QuizPage })
function QuizPage() {
  const { id } = Route.useParams(),
    { user } = useAuth()
  const { data, loading, error, reload } = useApi(`/quizzes/${encodeURIComponent(id)}/`)
  if (loading) return <Loading />
  if (error) return <ErrorMessage error={error} retry={reload} />
  if (data.status === 'draft')
    return (
      <div className="panel">
        <h1>Review your draft first.</h1>
        <Link to="/review/$id" params={{ id }}>
          Review and save quiz
        </Link>
      </div>
    )
  return (
    <QuizSessionProvider
      key={`${user?.id}.${data.id}.${data.version}`}
      quiz={data}
      userId={user?.id}
    >
      <QuizPlayer quiz={data} />
    </QuizSessionProvider>
  )
}
