import { useState } from 'react'
import { Link, useRouter } from '@tanstack/react-router'
import { ArrowRight, Check, Shield } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { ErrorMessage } from './UI'
export default function AuthForm({ register = false }) {
  const { signIn } = useAuth(),
    router = useRouter()
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(null)
  async function login(values) {
    setBusy(true)
    setError(null)
    try {
      await signIn(register ? 'register' : 'login', values)
      await router.invalidate()
      await router.navigate({ to: '/' })
    } catch (e) {
      setError(e)
      setBusy(false)
    }
  }
  return (
    <div className="auth-layout">
      <div className="auth-story">
        <span className="brand-mark">
          <Check size={27} />
        </span>
        <p className="eyebrow">BEGIN WITH INTENTION</p>
        <h1>
          Show up.
          <br />
          Put in the work.
          <br />
          <em>Grow.</em>
        </h1>
        <p>
          A private training ground for your next chapter.
          <br />
          Built on discipline. Grounded in your notes.
        </p>
        <div className="auth-signature">
          <Shield size={20} />
          <span>
            GHOSTOFASTANA
            <br />
            <small>ASTANA · TOMORROW SCHOOL</small>
          </span>
        </div>
      </div>
      <form
        className="auth-form"
        onSubmit={(event) => {
          event.preventDefault()
          login(Object.fromEntries(new FormData(event.currentTarget)))
        }}
      >
        <p className="eyebrow">BRAIN-CHECK</p>
        <h2>{register ? 'Start your daily practice.' : 'Back to your practice.'}</h2>
        <p className="muted">
          {register
            ? 'Create an account to keep your notes and progress together.'
            : 'Sign in to pick up where you left off.'}
        </p>
        <ErrorMessage error={error} />
        <fieldset disabled={busy}>
          <label className="field">
            Username
            <input
              name="username"
              autoComplete="username"
              required
              minLength={3}
              maxLength={30}
              pattern="[A-Za-z0-9_]+"
            />
          </label>
          <label className="field">
            Password
            <input
              name="password"
              type="password"
              autoComplete={register ? 'new-password' : 'current-password'}
              required
              minLength={register ? 10 : 1}
              maxLength={128}
            />
          </label>
          {register && (
            <p className="muted small">
              Use at least 10 characters. Avoid common passwords or your username.
            </p>
          )}
          <button className="full-width" disabled={busy}>
            {busy ? 'One moment…' : register ? 'Create account' : 'Sign in'}
            <ArrowRight size={18} />
          </button>
        </fieldset>
        <p className="auth-switch">
          {register ? 'Already practicing?' : 'New here?'}{' '}
          <Link to={register ? '/login' : '/register'}>
            {register ? 'Sign in' : 'Create an account'}
          </Link>
        </p>
        {!register && (
          <div className="demo-access">
            <p className="tiny-label">EXPLORING THE LOCAL DEMO?</p>
            <p>
              <code>demo</code> / <code>Practice!Since2008</code>
            </p>
            <button
              type="button"
              className="secondary full-width"
              disabled={busy}
              onClick={() => login({ username: 'demo', password: 'Practice!Since2008' })}
            >
              Explore demo workspace <ArrowUpRightIcon />
            </button>
          </div>
        )}
      </form>
    </div>
  )
}
function ArrowUpRightIcon() {
  return <ArrowRight size={16} />
}
