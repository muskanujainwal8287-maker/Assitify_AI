import { useEffect, useState, type SubmitEvent } from 'react'
import { Link } from 'react-router-dom'
import { AppShell } from '../components/AppShell.tsx'
import { Button, Card, ErrorBanner, Spinner, fieldClass } from '../components/ui.tsx'
import { useAuth } from '../context/AuthContext.tsx'
import { authApi } from '../lib/api.ts'
import { errorMessage, formatDate } from '../lib/format.ts'
import type { User } from '../types/api.ts'

export function ProfilePage() {
  const { user, logout, updateProfile } = useAuth()
  const [profile, setProfile] = useState<User | null>(user)
  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [mobile, setMobile] = useState(user?.mobile_number ?? '')
  const [loading, setLoading] = useState(!user)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    authApi
      .me()
      .then((next) => {
        if (cancelled) return
        setProfile(next)
        setFullName(next.full_name ?? '')
        setEmail(next.email)
        setMobile(next.mobile_number)
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

  async function onSave(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSaved(false)
    setSaving(true)
    try {
      const next = await updateProfile({
        full_name: fullName.trim(),
        email: email.trim(),
        mobile_number: mobile.trim(),
      })
      setProfile(next)
      setFullName(next.full_name ?? '')
      setEmail(next.email)
      setMobile(next.mobile_number)
      setSaved(true)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const displayName = fullName.trim() || email.trim() || profile?.email || 'Student'
  const dirty =
    fullName.trim() !== (profile?.full_name ?? '').trim() ||
    email.trim() !== (profile?.email ?? '') ||
    mobile.trim() !== (profile?.mobile_number ?? '')

  return (
    <AppShell>
      <Link to="/documents" className="mb-6 inline-block text-sm text-muted2 hover:text-ink">
        ← Back to library
      </Link>

      <div className="mx-auto flex w-full max-w-2xl flex-col items-center text-center">
        <div className="mb-8">
          <p className="text-sm uppercase tracking-[0.2em] text-copper">Account Details</p>
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
            <form onSubmit={onSave} className="space-y-4">
              <label className="block text-sm">
                Full name
                <input
                  className={`${fieldClass} mt-1`}
                  value={fullName}
                  onChange={(event) => {
                    setFullName(event.target.value)
                    setSaved(false)
                  }}
                  autoComplete="name"
                />
              </label>
              <label className="block text-sm">
                Email
                <input
                  className={`${fieldClass} mt-1`}
                  type="email"
                  value={email}
                  onChange={(event) => {
                    setEmail(event.target.value)
                    setSaved(false)
                  }}
                  autoComplete="email"
                  required
                />
              </label>
              <label className="block text-sm">
                Mobile
                <input
                  className={`${fieldClass} mt-1`}
                  value={mobile}
                  onChange={(event) => {
                    setMobile(event.target.value)
                    setSaved(false)
                  }}
                  inputMode="numeric"
                  autoComplete="tel"
                  required
                />
              </label>
              <div className="grid gap-1 border-t border-line pt-4 sm:grid-cols-[10rem_1fr] sm:items-baseline sm:gap-6">
                <dt className="text-sm text-muted2">Joined</dt>
                <dd className="break-all text-base text-ink">{formatDate(profile.created_at)}</dd>
              </div>
              {saved ? <p className="text-sm text-forest">Profile saved.</p> : null}
              <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                <Button type="submit" disabled={saving || !dirty}>
                  {saving ? 'Saving…' : 'Save changes'}
                </Button>
                <Button type="button" variant="ghost" onClick={logout}>
                  Log out
                </Button>
              </div>
            </form>
          </Card>
        ) : null}
      </div>
    </AppShell>
  )
}
