import { Link, Outlet, useRouter } from '@tanstack/react-router'
import {
  ArrowUpRight,
  BookOpen,
  Check,
  LayoutDashboard,
  LogOut,
  Menu,
  Shield,
  Target,
  UserRound,
  X,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { useApi } from '../hooks/useApi'
import { ModeBadge } from './UI'
const nav = [
  ['/', 'Overview', LayoutDashboard],
  ['/quizzes', 'Practice library', Target],
  ['/material', 'Study notes', BookOpen],
  ['/profile', 'My progress', UserRound],
]
export default function Layout() {
  const { user, signOut } = useAuth()
  const { data: health } = useApi('/health/')
  const [open, setOpen] = useState(false)
  const [mobile, setMobile] = useState(() => window.matchMedia('(max-width: 700px)').matches)
  const router = useRouter()
  useEffect(() => {
    const query = window.matchMedia('(max-width: 700px)')
    const resize = () => setMobile(query.matches)
    const escape = (event) => {
      if (event.key === 'Escape') setOpen(false)
    }
    query.addEventListener('change', resize)
    window.addEventListener('keydown', escape)
    return () => {
      query.removeEventListener('change', resize)
      window.removeEventListener('keydown', escape)
    }
  }, [])
  useEffect(() => {
    const onExpiry = () => router.navigate({ to: '/login' })
    window.addEventListener('session-expired', onExpiry)
    return () => window.removeEventListener('session-expired', onExpiry)
  }, [router])
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <button
        className="mobile-menu icon-button"
        aria-label={open ? 'Close navigation' : 'Open navigation'}
        aria-expanded={open}
        aria-controls="main-sidebar"
        onClick={() => setOpen(!open)}
      >
        {open ? <X /> : <Menu />}
      </button>
      <aside id="main-sidebar" className={`sidebar ${open ? 'open' : ''}`} inert={mobile && !open}>
        <Link to="/" className="brand" onClick={() => setOpen(false)}>
          <span className="brand-mark">
            <Check size={23} />
          </span>
          <span>
            brain-check<span className="brand-caption">A DAILY PRACTICE</span>
          </span>
        </Link>
        <p className="nav-caption">YOUR TRAINING GROUND</p>
        <nav aria-label="Main navigation">
          {nav.map(([to, text, Icon]) => (
            <Link
              key={to}
              to={to}
              activeOptions={{ exact: true }}
              activeProps={{ className: 'active' }}
              onClick={() => setOpen(false)}
            >
              <Icon size={19} />
              {text}
              <span className="nav-dot" />
            </Link>
          ))}
        </nav>
        <div className="sidebar-mantra">
          <div className="line-emblem">
            <Target size={30} />
          </div>
          <p>
            Discipline becomes
            <br />
            understanding.
          </p>
          <span>ONE SESSION AT A TIME.</span>
        </div>
        <div className="sidebar-bottom">
          <div className="identity">
            <span className="avatar">YS</span>
            <div>
              <strong>GhostOfAstana</strong>
              <small>Tomorrow School student</small>
            </div>
          </div>
          <div className="identity-foot">
            <Shield size={13} />
            <span>Daily martial practice · since 2008</span>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span className="breadcrumb">
            LEARN <span>/</span> PRACTICE <span>/</span> PROGRESS
          </span>
          <div className="topbar-actions">
            {health && <ModeBadge mode={health.modelMode} notice={health.notice} />}
            <span className="topbar-divider" />
            {user ? (
              <button
                className="text-button"
                onClick={async () => {
                  await signOut()
                  await router.navigate({ to: '/login' })
                  await router.invalidate()
                }}
                title="Sign out"
              >
                <span>{user.username}</span>
                <LogOut size={16} />
              </button>
            ) : (
              <Link to="/login" className="text-button">
                Sign in <ArrowUpRight size={16} />
              </Link>
            )}
          </div>
        </header>
        <main id="main" tabIndex={-1}>
          <Outlet />
        </main>
        <footer>
          <span>
            brain-check <span className="footer-dot">•</span> Built with intention in Astana
          </span>
          <span>Discipline. Evidence. Progress.</span>
        </footer>
      </div>
    </div>
  )
}
