import { useEffect, useState, useCallback } from 'react'
import { api } from '../utils/apiClient'
export function useApi(path) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [revision, setRevision] = useState(0)
  const reload = useCallback(() => setRevision((x) => x + 1), [])
  useEffect(() => {
    if (!path) {
      setState({ data: null, error: null, loading: false })
      return
    }
    let active = true
    const controller = new AbortController()
    setState({ data: null, error: null, loading: true })
    api(path, { signal: controller.signal })
      .then((data) => {
        if (active) setState({ data, error: null, loading: false })
      })
      .catch((error) => {
        if (active) setState({ data: null, error, loading: false })
      })
    return () => {
      active = false
      controller.abort()
    }
  }, [path, revision])
  return { ...state, reload }
}
