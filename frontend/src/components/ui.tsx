import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { LlmSource } from '../types/api.ts'

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted2" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-forest" />
      {label}
    </div>
  )
}

export function PageSpinner({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="grid min-h-svh place-items-center bg-paper">
      <Spinner label={label} />
    </div>
  )
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-bad/30 bg-bad/10 px-3 py-2 text-sm text-bad" role="alert">
      {message}
    </div>
  )
}

export function SourceBadge({ source }: { source?: LlmSource | string | null }) {
  if (!source) return null
  const label = source === 'openai' ? 'AssistifyAI' : source === 'mixed' ? 'Mixed' : 'Local fallback'
  return (
    <span className="rounded-full border border-line bg-paper px-2 py-0.5 text-xs text-muted2">
      {label}
    </span>
  )
}

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

const buttonStyles: Record<ButtonVariant, string> = {
  primary: 'bg-forest text-white hover:bg-forest-soft disabled:bg-forest/50',
  secondary: 'bg-forest-soft text-white hover:bg-forest disabled:bg-forest-soft/50',
  ghost: 'border border-line bg-card text-ink hover:border-forest disabled:opacity-50',
  danger: 'border border-bad/30 bg-bad/10 text-bad hover:bg-bad/15 disabled:opacity-50',
}

export function Button({
  variant = 'primary',
  className = '',
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      className={`inline-flex items-center justify-center rounded-lg px-4 py-2.5 text-sm font-medium transition disabled:cursor-not-allowed ${buttonStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-line bg-card p-5 shadow-[0_8px_30px_rgba(28,25,23,0.04)] ${className}`}>
      {children}
    </div>
  )
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string
  body: string
  action?: ReactNode
}) {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-card/60 px-6 py-10 text-center">
      <h3 className="font-serif text-xl">{title}</h3>
      <p className="mt-2 text-sm text-muted2">{body}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  )
}

export function Wordmark({
  to = '/documents',
  variant = 'app',
}: {
  to?: string
  variant?: 'app' | 'auth'
}) {
  const src = variant === 'auth' ? '/assistify-logo.png' : '/assistify-icon.png'
  return (
    <Link to={to} className="flex items-center" aria-label="AssistifyAI">
      <img
        src={src}
        alt="AssistifyAI"
        className={
          variant === 'auth'
            ? 'h-11 w-auto max-w-[12rem] object-contain object-left'
            : 'h-12 w-12 rounded-xl object-contain'
        }
      />
    </Link>
  )
}

export const fieldClass =
  'w-full rounded-lg border border-line bg-white/75 px-3 py-2.5 text-sm outline-none transition focus:border-forest'
