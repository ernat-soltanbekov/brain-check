import { createFileRoute } from '@tanstack/react-router'
import { requireAuth } from '../utils/guards'
import { useApi } from '../hooks/useApi'
import ResultsDashboard from '../components/ResultsDashboard'
import { Loading, ErrorMessage } from '../components/UI'
export const Route = createFileRoute('/results/$id')({
  beforeLoad: requireAuth,
  component: Results,
})
function Results() {
  const { id } = Route.useParams()
  const { data, loading, error, reload } = useApi(`/attempts/${encodeURIComponent(id)}/`)
  return loading ? (
    <Loading />
  ) : error ? (
    <ErrorMessage error={error} retry={reload} />
  ) : (
    <ResultsDashboard key={data.id} attempt={data} />
  )
}
