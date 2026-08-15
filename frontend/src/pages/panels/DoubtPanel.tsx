import { useEffect, useRef, useState, type SubmitEvent } from 'react'
import { Button, EmptyState, ErrorBanner, Spinner, fieldClass } from '../../components/ui.tsx'
import { documentsApi } from '../../lib/api.ts'
import { errorMessage, formatDate } from '../../lib/format.ts'
import type { ChatMessageOut, DoubtSessionDetailResponse, DoubtSessionListItem } from '../../types/api.ts'

export function DoubtPanel({ documentId }: { documentId: string }) {
  const [sessions, setSessions] = useState<DoubtSessionListItem[]>([])
  const [active, setActive] = useState<DoubtSessionDetailResponse | null>(null)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  async function refreshSessions() {
    const result = await documentsApi.doubtSessions(documentId)
    setSessions(result.sessions)
    return result.sessions
  }

  useEffect(() => {
    let cancelled = false
    documentsApi
      .doubtSessions(documentId)
      .then(async (result) => {
        if (cancelled) return
        setSessions(result.sessions)
        if (result.sessions[0]) {
          const first = await documentsApi.getDoubtSession(documentId, result.sessions[0].session_id)
          if (!cancelled) setActive(first)
        }
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
  }, [documentId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [active?.messages.length, busy])

  async function startSession() {
    setBusy(true)
    setError('')
    try {
      const created = await documentsApi.createDoubtSession(documentId)
      setActive(created)
      await refreshSessions()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function openSession(sessionId: string) {
    setBusy(true)
    setError('')
    try {
      setActive(await documentsApi.getDoubtSession(documentId, sessionId))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function removeSession(sessionId: string) {
    if (!window.confirm('Delete this chat?')) return
    try {
      await documentsApi.deleteDoubtSession(documentId, sessionId)
      const list = await refreshSessions()
      if (active?.session_id === sessionId) {
        setActive(list[0] ? await documentsApi.getDoubtSession(documentId, list[0].session_id) : null)
      }
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  async function send(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!active || draft.trim().length < 3) {
      setError('Write at least 3 characters.')
      return
    }
    const question = draft.trim()
    setDraft('')
    setBusy(true)
    setError('')
    const optimistic: ChatMessageOut = {
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
    }
    setActive((current) =>
      current ? { ...current, messages: [...current.messages, optimistic] } : current,
    )
    try {
      const reply = await documentsApi.sendDoubt(documentId, question, active.session_id)
      setActive((current) =>
        current
          ? {
              ...current,
              session_id: reply.session_id,
              messages: reply.messages.length > 0 ? reply.messages : current.messages,
            }
          : current,
      )
      await refreshSessions()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <Spinner label="Loading chats" />

  return (
    <section className="grid gap-4 lg:grid-cols-[240px_1fr]">
      <aside className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-serif text-xl">Chats</h2>
          <Button variant="secondary" onClick={startSession} disabled={busy}>
            New
          </Button>
        </div>
        {sessions.length === 0 ? (
          <p className="text-sm text-muted2">No tutoring chats yet.</p>
        ) : (
          <ul className="space-y-1">
            {sessions.map((session) => (
              <li key={session.session_id}>
                <button
                  type="button"
                  onClick={() => openSession(session.session_id)}
                  className={`w-full rounded-lg px-3 py-2 text-left text-sm ${
                    active?.session_id === session.session_id ? 'bg-forest text-paper' : 'hover:bg-line/60'
                  }`}
                >
                  <span className="block truncate">{session.title || 'Untitled chat'}</span>
                  <span className="text-xs opacity-80">{session.message_count} messages</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      <div className="flex min-h-[480px] flex-col rounded-2xl border border-line bg-card">
        {error ? (
          <div className="p-4">
            <ErrorBanner message={error} />
          </div>
        ) : null}
        {!active ? (
          <div className="flex flex-1 items-center justify-center p-6">
            <EmptyState
              title="Start a tutoring chat"
              body="The tutor asks first, then you can answer or raise a doubt about this document."
              action={
                <Button onClick={startSession} disabled={busy}>
                  {busy ? 'Starting…' : 'Start session'}
                </Button>
              }
            />
          </div>
        ) : (
          <>
            <header className="flex items-center justify-between border-b border-line px-4 py-3">
              <div>
                <p className="font-medium">{active.title || 'Tutoring chat'}</p>
                <p className="text-xs text-muted2">Updated {formatDate(active.updated_at)}</p>
              </div>
              <Button variant="danger" onClick={() => removeSession(active.session_id)}>
                Delete
              </Button>
            </header>
            <div className="flex-1 space-y-3 overflow-y-auto p-4">
              {active.messages.map((message, index) => (
                <div
                  key={`${message.created_at}-${index}`}
                  className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                    message.role === 'user'
                      ? 'ml-auto bg-forest text-white'
                      : 'bg-paper text-ink'
                  }`}
                >
                  {message.content}
                </div>
              ))}
              {busy ? <Spinner label="Tutor is thinking" /> : null}
              <div ref={bottomRef} />
            </div>
            <form onSubmit={send} className="flex gap-2 border-t border-line p-3">
              <input
                className={fieldClass}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Answer or ask a doubt…"
                disabled={busy}
              />
              <Button type="submit" disabled={busy}>
                Send
              </Button>
            </form>
          </>
        )}
      </div>
    </section>
  )
}
