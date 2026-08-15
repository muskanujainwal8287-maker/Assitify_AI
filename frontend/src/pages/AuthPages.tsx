import { useState, type InputHTMLAttributes, type SubmitEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.tsx'
import { errorMessage } from '../lib/format.ts'
import { Button, ErrorBanner, Wordmark, fieldClass } from '../components/ui.tsx'

const authFieldClass = `${fieldClass} mt-1 py-2 text-sm`

function EyeIcon({ open }: { open: boolean }) {
  if (open) {
    return (
      <svg viewBox="0 0 24 24" className="h-4.5 w-4.5" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
        <path d="M3 3l18 18" strokeLinecap="round" />
        <path d="M10.6 10.6a2 2 0 002.8 2.8" strokeLinecap="round" />
        <path
          d="M9.9 5.2A10.5 10.5 0 0112 5c5 0 9.3 3.1 11 7.5a11.6 11.6 0 01-4.1 5.1M6.1 6.1A11.6 11.6 0 001 12.5C2.7 16.9 7 20 12 20a10.5 10.5 0 005.1-1.3"
          strokeLinecap="round"
        />
      </svg>
    )
  }
  return (
    <svg viewBox="0 0 24 24" className="h-4.5 w-4.5" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path d="M1 12.5C2.7 8.1 7 5 12 5s9.3 3.1 11 7.5C21.3 16.9 17 20 12 20S2.7 16.9 1 12.5z" />
      <circle cx="12" cy="12.5" r="3" />
    </svg>
  )
}

function PasswordField({
  label = 'Password',
  ...props
}: Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'className'> & { label?: string }) {
  const [visible, setVisible] = useState(false)

  return (
    <label className="block text-base">
      {label}
      <span className="relative mt-1 block">
        <input
          {...props}
          className={`${authFieldClass} mt-0 pr-10`}
          type={visible ? 'text' : 'password'}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute inset-y-0 right-0 flex items-center px-3 text-muted2 transition hover:text-ink"
          aria-label={visible ? 'Hide password' : 'Show password'}
          tabIndex={-1}
        >
          <EyeIcon open={visible} />
        </button>
      </span>
    </label>
  )
}

function AuthHero() {
  return (
    <aside className="hidden items-center justify-center bg-[#d1e4f3] px-20 py-20 lg:flex">
      <img
        src="/assistify-logo.png"
        alt="AssistifyAI"
        className="w-195 max-w-[145%]"
      />
    </aside>
  )
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setBusy(true)
    const trimmed = identifier.trim()
    const payload = trimmed.includes('@')
      ? { email: trimmed, password }
      : { mobile_number: trimmed, password }
    try {
      await login(payload)
      navigate('/documents', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <AuthHero />
      <main className="flex items-start justify-start bg-[#779ebd] px-8 pt-20 pb-10">
        <form onSubmit={onSubmit} className="w-full max-w-lg space-y-6">
          <div className="lg:hidden">
            <Wordmark to="/login" variant="auth" />
          </div>
          <div>
            <h1 className="font-serif text-7xl">Welcome back</h1>
            <p className="mt-5 text-base text-muted">Log in with email or mobile number</p>
          </div>
          {error ? <ErrorBanner message={error} /> : null}
          <label className="block text-base">
            Email or Mobile Number
            <input
              className={authFieldClass}
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <PasswordField
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
          <Button type="submit" disabled={busy} className="w-full py-2.5 text-sm">
            {busy ? 'Signing in…' : 'Log in'}
          </Button>
          <div className="flex items-center justify-between gap-4 text-base">
            <p className="text-muted">
              New here?{' '}
              <Link to="/register" className="text-forest hover:underline">
                Create an account
              </Link>
            </p>
            <span className="shrink-0 text-forest">Forgot password?</span>
          </div>
        </form>
      </main>
    </div>
  )
}

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [mobile, setMobile] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await register({
        email: email.trim(),
        mobile_number: mobile.trim(),
        password,
        full_name: fullName.trim(),
      })
      navigate('/documents', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <AuthHero />
      <main className="flex items-start justify-start bg-[#779ebd] px-10 pt-16 pb-10">
        <form onSubmit={onSubmit} className="w-full max-w-lg space-y-6">
          <div className="lg:hidden">
            <Wordmark to="/login" variant="auth" />
          </div>
          <div>
            <h1 className="font-serif text-5xl">Create your account</h1>
            <p className="mt-5 text-base text-muted">Your documents stay scoped to this login.</p>
          </div>
          {error ? <ErrorBanner message={error} /> : null}
          <label className="block text-base">
            Full name
            <input
              className={authFieldClass}
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              autoComplete="name"
            />
          </label>
          <label className="block text-base">
            Email
            <input
              className={authFieldClass}
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </label>
          <label className="block text-base">
            Mobile number
            <input
              className={authFieldClass}
              value={mobile}
              onChange={(event) => setMobile(event.target.value)}
              inputMode="numeric"
              autoComplete="tel"
              required
            />
          </label>
          <PasswordField
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
            minLength={6}
            required
          />
          <Button type="submit" disabled={busy} className="w-full py-2.5 text-sm">
            {busy ? 'Creating account…' : 'Create account'}
          </Button>
          <p className="text-base text-muted">
            Already have an account?{' '}
            <Link to="/login" className="text-forest hover:underline">
              Log in
            </Link>
          </p>
        </form>
      </main>
    </div>
  )
}
