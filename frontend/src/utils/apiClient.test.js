import { beforeEach, afterEach, describe, it, expect, vi } from 'vitest'
import { api, errorMessage, ApiError } from './apiClient'
import { storage, readJSON } from './storage'
beforeEach(() => {
  storage.remove('brain-check.token')
  vi.stubGlobal('fetch', vi.fn())
})
afterEach(() => vi.unstubAllGlobals())
describe('API boundary', () => {
  it('sends authentication and the idempotency key with JSON', async () => {
    storage.set('brain-check.token', 'test-token')
    fetch.mockResolvedValue({ ok: true, status: 201, json: async () => ({ id: 7 }) })
    expect(
      await api('/quizzes/7/submit/', {
        method: 'POST',
        body: { answers: [] },
        headers: { 'Idempotency-Key': 'example' },
      }),
    ).toEqual({ id: 7 })
    expect(fetch.mock.calls[0][1].headers).toMatchObject({
      Authorization: 'Token test-token',
      'Idempotency-Key': 'example',
    })
  })
  it('does not set a JSON content type on file uploads', async () => {
    fetch.mockResolvedValue({ ok: true, status: 201, json: async () => ({ id: 1 }) })
    await api('/material/', { method: 'POST', body: new FormData() })
    expect(fetch.mock.calls[0][1].headers['Content-Type']).toBeUndefined()
  })
  it('clears an expired session and broadcasts the change', async () => {
    storage.set('brain-check.token', 'expired')
    const listener = vi.fn()
    window.addEventListener('session-expired', listener)
    fetch.mockResolvedValue({ ok: false, status: 401, json: async () => ({ detail: 'Expired' }) })
    await expect(api('/auth/me/')).rejects.toMatchObject({ status: 401 })
    expect(storage.get('brain-check.token')).toBeNull()
    expect(listener).toHaveBeenCalledOnce()
    window.removeEventListener('session-expired', listener)
  })
  it('converts connection failures into a useful message', async () => {
    fetch.mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(api('/quizzes/')).rejects.toThrow('Cannot reach the server')
  })
  it('provides safe retry guidance for timeout', async () => {
    fetch.mockRejectedValue(new DOMException('Aborted', 'AbortError'))
    await expect(api('/quizzes/')).rejects.toThrow('Your answers are preserved')
  })
  it('keeps validation messages readable', () =>
    expect(errorMessage({ answers: ['Duplicate question'], detail: 'Retry' })).toBe(
      'answers: Duplicate question Retry',
    ))
  it('handles a non-JSON server error', async () => {
    fetch.mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => {
        throw new Error('HTML')
      },
    })
    await expect(api('/quizzes/')).rejects.toThrow('unreadable response')
  })
  it('accepts an empty successful response', async () => {
    fetch.mockResolvedValue({ ok: true, status: 204 })
    expect(await api('/auth/logout/', { method: 'POST' })).toBeNull()
  })
})
describe('resilient session storage', () => {
  it('tolerates malformed persisted JSON', () => {
    storage.set('bad-json', '{bad')
    expect(readJSON('bad-json', 'safe')).toBe('safe')
  })
  it('continues in memory when session storage is unavailable', () => {
    vi.stubGlobal('sessionStorage', {
      getItem() {
        throw new Error('blocked')
      },
      setItem() {
        throw new Error('quota')
      },
      removeItem() {
        throw new Error('blocked')
      },
    })
    storage.set('offline-state', 'retained')
    expect(storage.get('offline-state')).toBe('retained')
    storage.remove('offline-state')
    expect(storage.get('offline-state')).toBeNull()
  })
})
