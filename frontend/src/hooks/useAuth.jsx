import { createContext, useContext, useEffect, useState } from 'react'
import { api, getToken } from '../utils/apiClient'
import { storage, readJSON } from '../utils/storage'
const AuthContext = createContext(null)
export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => (getToken() ? readJSON('brain-check.user') : null))
  const [ready, setReady] = useState(!getToken())
  useEffect(() => {
    const expired = () => {
      setUser(null)
      storage.remove('brain-check.user')
    }
    window.addEventListener('session-expired', expired)
    if (getToken())
      api('/auth/me/', { timeout: 10000 })
        .then(setUser)
        .catch((error) => {
          if (error.status === 401) expired()
        })
        .finally(() => setReady(true))
    return () => window.removeEventListener('session-expired', expired)
  }, [])
  async function signIn(operation, values) {
    const result = await api(`/auth/${operation}/`, { method: 'POST', body: values, token: null })
    storage.set('brain-check.token', result.token)
    storage.set('brain-check.user', JSON.stringify(result.user))
    setUser(result.user)
    setReady(true)
  }
  async function signOut() {
    try {
      await api('/auth/logout/', { method: 'POST', timeout: 5000 })
    } catch {
      /* Always clear this device's session. */
    }
    storage.remove('brain-check.token')
    storage.remove('brain-check.user')
    setUser(null)
  }
  return (
    <AuthContext.Provider value={{ user, ready, signIn, signOut }}>{children}</AuthContext.Provider>
  )
}
export const useAuth = () => useContext(AuthContext)
