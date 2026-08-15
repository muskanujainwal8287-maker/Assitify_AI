import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AppShell } from '../components/AppShell.tsx'
import { Button, Card, ErrorBanner, Spinner } from '../components/ui.tsx'
import { useAuth } from '../context/AuthContext.tsx'
import { authApi } from '../lib/api.ts'
import { errorMessage, formatDate } from '../lib/format.ts'
import type { User } from '../types/api.ts'

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 border-b border-line py-4 last:border-b-0 sm:grid-cols-[10rem_1fr] sm:items-baseline sm:gap-6">
      <dt className="text-sm text-muted2">{label}</dt>
      <dd className="break-all text-base text-ink">{value || '—'}</dd>
    </div>
  )
}

export function ProfilePage() {
  const { user, logout } = useAuth()
  const [profile, setProfile] = useState<User | null>(user)
  const [loading, setLoading] = useState(!user)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    authApi
      .me()
      .then((next) => {
        if (!cancelled) setProfile(next)
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const displayName = profile?.full_name?.trim() || profile?.email || 'Student'

  return (
    <AppShell>
      <Link to="/documents" className="mb-6 inline-block text-sm text-muted2 hover:text-ink">
        ← Back to library
      </Link>

      <div className="mx-auto flex w-full max-w-2xl flex-col items-center text-center">
        <div className="mb-8">
          <p className="text-sm uppercase tracking-[0.2em] text-copper">Account</p>
          <h1 className="font-serif text-4xl">{displayName}</h1>
        </div>

        {error ? (
          <div className="mb-6 w-full text-left">
            <ErrorBanner message={error} />
          </div>
        ) : null}

        {loading && !profile ? (
          <Spinner label="Loading profile" />
        ) : profile ? (
          <Card className="w-full text-left">
            <dl>
              <DetailRow label="Full name" value={profile.full_name?.trim() || '—'} />
              <DetailRow label="Email" value={profile.email} />
              <DetailRow label="Mobile" value={profile.mobile_number} />
              <DetailRow label="Joined" value={formatDate(profile.created_at)} />
            </dl>
            <div className="mt-6 flex justify-center">
              <Button type="button" variant="ghost" onClick={logout}>
                Log out
              </Button>
            </div>
          </Card>
        ) : null}
      </div>
    </AppShell>
  )
}
