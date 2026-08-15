import { useEffect, useState } from 'react'
import { Button, Card, EmptyState, ErrorBanner, Spinner } from '../../components/ui.tsx'
import { documentsApi } from '../../lib/api.ts'
import { errorMessage, formatDate, formatScore } from '../../lib/format.ts'
import type { AttemptDetailResponse, AttemptListItem, WeakTopicOut } from '../../types/api.ts'

function asWeakTopics(value: unknown): WeakTopicOut[] {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is WeakTopicOut => {
    return Boolean(
      item &&
        typeof item === 'object' &&
        'topic' in item &&
        'accuracy' in item &&
        'suggestion' in item,
    )
  })
}

export function AttemptsPanel({ documentId }: { documentId: string }) {
  const [attempts, setAttempts] = useState<AttemptListItem[]>([])
  const [detail, setDetail] = useState<AttemptDetailResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState('')

  useEffect(() => {
    documentsApi
      .attempts(documentId)
      .then((result) => setAttempts(result.attempts))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [documentId])

  async function openAttempt(attemptId: string) {
    setBusyId(attemptId)
    setError('')
    try {
      setDetail(await documentsApi.attempt(documentId, attemptId))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusyId('')
    }
  }

  if (loading) return <Spinner label="Loading attempts" />

  return (
    <section className="space-y-4">
      <header>
        <h2 className="font-serif text-2xl">Attempts</h2>
        <p className="text-sm text-muted2">Past scored practice on this document.</p>
      </header>
      {error ? <ErrorBanner message={error} /> : null}
      {attempts.length === 0 ? (
        <EmptyState title="No attempts yet" body="Submit a practice set to see scores here." />
      ) : (
        <div className="space-y-3">
          {attempts.map((attempt) => (
            <Card key={attempt.attempt_id} className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-medium">{formatScore(attempt.total_score)}</p>
                <p className="text-sm text-muted2">
                  {formatDate(attempt.created_at)} · next: {attempt.recommended_difficulty}
                </p>
              </div>
              <Button variant="ghost" onClick={() => openAttempt(attempt.attempt_id)} disabled={busyId === attempt.attempt_id}>
                {busyId === attempt.attempt_id ? 'Loading…' : 'View'}
              </Button>
            </Card>
          ))}
        </div>
      )}
      {detail ? (
        <div className="space-y-3">
          <h3 className="font-serif text-xl">Attempt detail</h3>
          {asWeakTopics(detail.weak_topics).map((topic) => (
            <p key={topic.topic} className="text-sm text-muted2">
              {topic.topic}: {Math.round(topic.accuracy)}% — {topic.suggestion}
            </p>
          ))}
          {detail.reviews.map((review) => (
            <Card key={review.question_id}>
              <p className={review.is_correct ? 'text-good' : 'text-bad'}>
                {review.is_correct ? 'Correct' : 'Incorrect'} · {Math.round(review.score)} / 100
              </p>
              <p className="mt-1 text-sm">{review.explanation}</p>
            </Card>
          ))}
        </div>
      ) : null}
    </section>
  )
}
