import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.tsx'
import { Wordmark } from './ui.tsx'
import type { ReactNode } from 'react'

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()
  const displayName = user?.full_name?.trim() || user?.email || 'Student'

  return (
    <div className="min-h-svh bg-paper">
      <header className="border-b border-line bg-card/80 backdrop-blur">
        <div className="flex w-full items-center justify-between gap-4 px-4 py-3 sm:pr-6">
          <Wordmark />
          <nav className="flex items-center gap-4 text-sm">
            <Link to="/documents" className="text-muted2 hover:text-ink">
              Library
            </Link>
            <Link to="/profile" className="text-muted2 hover:text-ink hover:underline">
              {displayName}
            </Link>
            <button
              type="button"
              onClick={logout}
              className="rounded-lg border border-line px-3 py-1.5 hover:border-forest"
            >
              Log out
            </button>
          </nav>
        </div>
      </header>
      <main className="w-full px-6 py-8">{children}</main>
    </div>
  )
}
