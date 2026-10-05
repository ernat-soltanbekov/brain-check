import { createRootRoute, Link } from '@tanstack/react-router'
import Layout from '../components/Layout'
import { ErrorMessage } from '../components/UI'
export const Route = createRootRoute({
  component: Layout,
  notFoundComponent: () => (
    <div className="empty-state">
      <h1>This page is off the map.</h1>
      <Link to="/">Return to your overview</Link>
    </div>
  ),
  errorComponent: ({ error, reset }) => <ErrorMessage error={error} retry={reset} />,
})
