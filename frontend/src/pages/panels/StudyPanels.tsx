import { useEffect, useState } from 'react'
import { Button, ErrorBanner, SourceBadge, Spinner, fieldClass } from '../../components/ui.tsx'
import { documentsApi } from '../../lib/api.ts'
import { errorMessage } from '../../lib/format.ts'
import type { KeyPointsResponse, SummaryResponse, TopicKeyPointsResponse } from '../../types/api.ts'

export function SummaryPanel({ documentId }: { documentId: string }) {
  const [data, setData] = useState<SummaryResponse | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    setBusy(true)
    setError('')
    try {
      setData(await documentsApi.summary(documentId))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-serif text-2xl">Summary</h2>
          <p className="text-sm text-muted2">A condensed reading of the uploaded document.</p>
        </div>
        <Button onClick={load} disabled={busy}>
          {busy ? 'Generating…' : data ? 'Regenerate' : 'Generate summary'}
        </Button>
      </header>
      {error ? <ErrorBanner message={error} /> : null}
      {busy ? <Spinner label="This can take a minute" /> : null}
      {data ? (
        <div className="space-y-3">
          <SourceBadge source={data.source} />
          <p className="whitespace-pre-wrap leading-7">{data.summary}</p>
        </div>
      ) : null}
    </section>
  )
}

export function KeyPointsPanel({ documentId }: { documentId: string }) {
  const [data, setData] = useState<KeyPointsResponse | null>(null)
  const [topicData, setTopicData] = useState<TopicKeyPointsResponse | null>(null)
  const [topic, setTopic] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function loadAll() {
    setBusy(true)
    setError('')
    setTopicData(null)
    try {
      setData(await documentsApi.keypoints(documentId))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function loadTopic() {
    if (topic.trim().length < 2) {
      setError('Enter a topic of at least 2 characters.')
      return
    }
    setBusy(true)
    setError('')
    try {
      setTopicData(await documentsApi.topicKeypoints(documentId, topic.trim()))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const points = topicData?.key_points ?? data?.key_points ?? []
  const source = topicData?.source ?? data?.source

  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-serif text-2xl">Key points</h2>
          <p className="text-sm text-muted2">Revision bullets for the whole document, or one topic.</p>
        </div>
        <Button onClick={loadAll} disabled={busy}>
          {busy ? 'Generating…' : 'Generate key points'}
        </Button>
      </header>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          className={fieldClass}
          value={topic}
          onChange={(event) => setTopic(event.target.value)}
          placeholder="Optional topic, e.g. photosynthesis"
        />
        <Button variant="ghost" onClick={loadTopic} disabled={busy}>
          Topic only
        </Button>
      </div>
      {error ? <ErrorBanner message={error} /> : null}
      {busy ? <Spinner label="This can take a minute" /> : null}
      {points.length > 0 ? (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <SourceBadge source={source} />
            {topicData ? <span className="text-sm text-muted2">Topic: {topicData.topic}</span> : null}
          </div>
          <ul className="list-disc space-y-2 pl-5">
            {points.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}

export function NotesPanel({ documentId }: { documentId: string }) {
  const [chapters, setChapters] = useState<{ chapter_id: string; title: string; chapter_number: number }[]>([])
  const [chapterId, setChapterId] = useState('')
  const [topic, setTopic] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [notes, setNotes] = useState<Awaited<ReturnType<typeof documentsApi.notes>> | null>(null)

  useEffect(() => {
    documentsApi
      .chapters(documentId)
      .then((result) => {
        setChapters(result.chapters)
        if (result.chapters[0]) setChapterId(result.chapters[0].chapter_id)
      })
      .catch((err) => setError(errorMessage(err)))
  }, [documentId])

  async function load() {
    if (!chapterId) {
      setError('Select a chapter first.')
      return
    }
    setBusy(true)
    setError('')
    try {
      setNotes(await documentsApi.notes(documentId, chapterId, topic || undefined))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="space-y-4">
      <header>
        <h2 className="font-serif text-2xl">Revision notes</h2>
        <p className="text-sm text-muted2">Chapter-wise notes, optionally filtered by topic.</p>
      </header>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">
          Chapter
          <select
            className={`${fieldClass} mt-1`}
            value={chapterId}
            onChange={(event) => setChapterId(event.target.value)}
          >
            {chapters.length === 0 ? <option value="">No chapters found</option> : null}
            {chapters.map((chapter) => (
              <option key={chapter.chapter_id} value={chapter.chapter_id}>
                {chapter.chapter_number}. {chapter.title}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Topic (optional)
          <input
            className={`${fieldClass} mt-1`}
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
          />
        </label>
      </div>
      <Button onClick={load} disabled={busy || !chapterId}>
        {busy ? 'Generating…' : 'Generate notes'}
      </Button>
      {error ? <ErrorBanner message={error} /> : null}
      {busy ? <Spinner label="This can take a minute" /> : null}
      {notes
        ? notes.chapters.map((chapter) => (
            <article key={chapter.chapter_id ?? chapter.title} className="space-y-3">
              <div className="flex items-center gap-2">
                <h3 className="font-serif text-xl">{chapter.title}</h3>
                <SourceBadge source={notes.source} />
              </div>
              {chapter.topics.map((item) => (
                <div key={item.topic}>
                  <h4 className="font-medium">{item.topic}</h4>
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
                    {item.notes.map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </article>
          ))
        : null}
    </section>
  )
}
