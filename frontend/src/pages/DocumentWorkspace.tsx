import { useEffect, useState } from 'react'
import { Link, NavLink, useNavigate, useParams } from 'react-router-dom'
import { AppShell } from '../components/AppShell.tsx'
import { Button, Card, ErrorBanner, Spinner } from '../components/ui.tsx'
import { documentsApi } from '../lib/api.ts'
import { errorMessage, formatDate } from '../lib/format.ts'
import { AttemptsPanel } from './panels/AttemptsPanel.tsx'
import { DoubtPanel } from './panels/DoubtPanel.tsx'
import { PracticePanel } from './panels/PracticePanel.tsx'
import { KeyPointsPanel, NotesPanel, SummaryPanel } from './panels/StudyPanels.tsx'
import {
  DOCUMENT_SECTIONS,
  type ChapterInfo,
  type DocumentDetailResponse,
  type DocumentSection,
} from '../types/api.ts'

const SECTION_LABELS: Record<DocumentSection, string> = {
  overview: 'Overview',
  summary: 'Summary',
  keypoints: 'Key points',
  notes: 'Notes',
  practice: 'Practice',
  attempts: 'Attempts',
  doubt: 'Doubt chat',
}

function isSection(value: string | undefined): value is DocumentSection {
  return DOCUMENT_SECTIONS.includes(value as DocumentSection)
}

export function DocumentWorkspace() {
  const { documentId = '', section } = useParams<{ documentId: string; section?: string }>()
  const navigate = useNavigate()
  const active: DocumentSection = isSection(section) ? section : 'overview'
  const [doc, setDoc] = useState<DocumentDetailResponse | null>(null)
  const [chapters, setChapters] = useState<ChapterInfo[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!documentId) return
    setLoading(true)
    setError('')
    Promise.allSettled([documentsApi.get(documentId), documentsApi.chapters(documentId)])
      .then(([detailResult, chapterResult]) => {
        if (detailResult.status === 'fulfilled') {
          setDoc(detailResult.value)
        } else {
          setDoc(null)
          setError(errorMessage(detailResult.reason))
          return
        }
        if (chapterResult.status === 'fulfilled') {
          setChapters(chapterResult.value.chapters)
        } else {
          setChapters([])
          setError(
            `Document loaded, but chapters could not be fetched: ${errorMessage(chapterResult.reason)}`,
          )
        }
      })
      .finally(() => setLoading(false))
  }, [documentId])

  async function onDelete() {
    if (!doc) return
    if (!window.confirm(`Delete “${doc.filename}”?`)) return
    try {
      await documentsApi.delete(documentId)
      navigate('/documents', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <AppShell>
      <Link to="/documents" className="text-sm text-muted2 hover:text-ink">
        ← Library
      </Link>
      {loading ? <div className="mt-6"><Spinner label="Opening document" /></div> : null}
      {error ? <div className="mt-4"><ErrorBanner message={error} /></div> : null}
      {doc ? (
        <>
          <header className="mt-4 mb-6">
            <p className="text-xs uppercase tracking-wide text-muted2">{doc.detected_type}</p>
            <h1 className="font-serif text-4xl">{doc.filename}</h1>
          </header>
          <div className="mb-6 flex flex-wrap gap-2">
            {DOCUMENT_SECTIONS.map((item) => (
              <NavLink
                key={item}
                to={item === 'overview' ? `/documents/${documentId}` : `/documents/${documentId}/${item}`}
                end={item === 'overview'}
                className={({ isActive }) =>
                  `rounded-full px-3 py-1.5 text-sm ${
                    isActive || active === item
                      ? 'bg-forest text-paper'
                      : 'border border-line bg-card hover:border-copper'
                  }`
                }
              >
                {SECTION_LABELS[item]}
              </NavLink>
            ))}
          </div>
          <Card>
            {active === 'overview' ? (
              <OverviewPanel doc={doc} chapters={chapters} onDelete={onDelete} />
            ) : null}
            {active === 'summary' ? <SummaryPanel documentId={documentId} /> : null}
            {active === 'keypoints' ? <KeyPointsPanel documentId={documentId} /> : null}
            {active === 'notes' ? <NotesPanel documentId={documentId} /> : null}
            {active === 'practice' ? <PracticePanel documentId={documentId} /> : null}
            {active === 'attempts' ? <AttemptsPanel documentId={documentId} /> : null}
            {active === 'doubt' ? <DoubtPanel documentId={documentId} /> : null}
          </Card>
        </>
      ) : null}
    </AppShell>
  )
}

function OverviewPanel({
  doc,
  chapters,
  onDelete,
}: {
  doc: DocumentDetailResponse
  chapters: ChapterInfo[]
  onDelete: () => void
}) {
  return (
    <section className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Uploaded" value={formatDate(doc.created_at)} />
        <Stat label="Questions Attempted" value={String(doc.question_attempted_count)} />
        <Stat label="Attempts" value={String(doc.attempt_count)} />
      </div>
      <div>
        <h2 className="font-serif text-2xl">Preview</h2>
        <div className="mt-2 max-h-96 overflow-y-auto rounded-xl border border-line bg-paper p-4">
          <p className="w-full break-words text-sm leading-relaxed text-ink/90 [overflow-wrap:anywhere]">
            {doc.text_preview || 'No preview available.'}
          </p>
        </div>
      </div>
      <div>
        <h2 className="font-serif text-2xl">Chapters</h2>
        {chapters.length === 0 ? (
          <p className="mt-2 text-sm text-muted2">No chapter headings detected. Notes still work with chapter 1.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {chapters.map((chapter) => (
              <li key={chapter.chapter_id} className="rounded-lg border border-line px-3 py-2 text-sm">
                {chapter.title}
              </li>
            ))}
          </ul>
        )}
      </div>
      <Button variant="danger" onClick={onDelete}>
        Delete document
      </Button>
    </section>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-paper px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-muted2">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  )
}
