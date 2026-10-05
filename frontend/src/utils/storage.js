// Private browsing and storage quotas must not prevent studying.
const memory = new Map()
export const storage = {
  get(key) {
    try {
      return sessionStorage.getItem(key) ?? memory.get(key) ?? null
    } catch {
      return memory.get(key) ?? null
    }
  },
  set(key, value) {
    memory.set(key, value)
    try {
      sessionStorage.setItem(key, value)
    } catch {
      /* Memory-only session. */
    }
  },
  remove(key) {
    memory.delete(key)
    try {
      sessionStorage.removeItem(key)
    } catch {
      /* Already memory-only. */
    }
  },
}
export function readJSON(key, fallback = null) {
  try {
    return JSON.parse(storage.get(key)) ?? fallback
  } catch {
    return fallback
  }
}
