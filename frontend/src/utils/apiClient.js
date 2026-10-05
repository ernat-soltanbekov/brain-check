import { storage } from './storage'
export const getToken = () => storage.get('brain-check.token')
export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}
export function errorMessage(data) {
  if (typeof data === 'string') return data
  if (Array.isArray(data)) return data.map(errorMessage).join(' ')
  if (data && typeof data === 'object')
    return Object.entries(data)
      .map(
        ([key, value]) =>
          `${key === 'detail' || key === 'non_field_errors' ? '' : `${key}: `}${errorMessage(value)}`,
      )
      .join(' ')
  return 'The request could not be completed.'
}
export async function api(
  path,
  { method = 'GET', body, token = getToken(), signal, headers = {}, timeout = 170000 } = {},
) {
  const controller = new AbortController()
  const abort = () => controller.abort()
  signal?.addEventListener('abort', abort, { once: true })
  if (signal?.aborted) controller.abort()
  const timer = setTimeout(abort, timeout)
  try {
    const multipart = body instanceof FormData
    const response = await fetch(`/api${path}`, {
      method,
      signal: controller.signal,
      headers: {
        ...(multipart ? {} : { 'Content-Type': 'application/json' }),
        ...(token ? { Authorization: `Token ${token}` } : {}),
        ...headers,
      },
      body: body === undefined ? undefined : multipart ? body : JSON.stringify(body),
    })
    const data =
      response.status === 204
        ? null
        : await response
            .json()
            .catch(() => ({ detail: 'The server returned an unreadable response.' }))
    if (!response.ok) {
      if (response.status === 401 && token === getToken()) {
        storage.remove('brain-check.token')
        window.dispatchEvent(new Event('session-expired'))
      }
      throw new ApiError(errorMessage(data), response.status)
    }
    return data
  } catch (error) {
    if (error.name === 'AbortError')
      throw new ApiError(
        'The request timed out or was cancelled. Your answers are preserved; retry safely.',
        0,
      )
    if (error instanceof ApiError) throw error
    throw new ApiError('Cannot reach the server. Check your connection and try again.', 0)
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', abort)
  }
}
export async function allPages(path, signal) {
  let next = path,
    rows = []
  while (next) {
    const page = await api(next, { signal })
    rows = [...rows, ...page.results]
    next = page.next ? page.next.slice(page.next.indexOf('/api') + 4) : null
    if (rows.length >= 300) break
  }
  return rows
}
