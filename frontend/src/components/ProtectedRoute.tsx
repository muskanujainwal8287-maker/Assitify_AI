import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.tsx'
import { PageSpinner } from './ui.tsx'
import type { ReactNode } from 'react'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { token, ready } = useAuth()
  if (!ready) return <PageSpinner label="Checking session" />
  if (!token) return <Navigate to="/login" replace />
  return children
}

export function GuestRoute({ children }: { children: ReactNode }) {
  const { token, ready } = useAuth()
  if (!ready) return <PageSpinner label="Checking session" />
  if (token) return <Navigate to="/documents" replace />
  return children
}
