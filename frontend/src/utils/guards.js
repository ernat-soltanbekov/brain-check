import { redirect } from '@tanstack/react-router'
import { getToken } from './apiClient'
export function requireAuth() {
  if (!getToken()) throw redirect({ to: '/login' })
}
