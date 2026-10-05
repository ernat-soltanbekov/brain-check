import { Component } from 'react'
export default class ErrorBoundary extends Component {
  state = { error: null }
  static getDerivedStateFromError(error) {
    return { error }
  }
  render() {
    return this.state.error ? (
      <main className="fatal">
        <h1>Let’s get back on track.</h1>
        <p>The page could not load. Saved answers are still in this browser session.</p>
        <button onClick={() => window.location.reload()}>Reload the application</button>
      </main>
    ) : (
      this.props.children
    )
  }
}
