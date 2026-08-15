import { useCallback, useEffect, useState, type DragEvent, type SubmitEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AppShell } from '../components/AppShell.tsx'
import { Button, Card, EmptyState, ErrorBanner, Spinner, fieldClass } from '../components/ui.tsx'
import { documentsApi } from '../lib/api.ts'
import { errorMessage, formatDate } from '../lib/format.ts'
import type { DocumentListItem } from '../types/api.ts'

const ACCEPT = '.pdf,.docx,.txt,.png,.jpg,.jpeg,.webp'

export function DocumentsPage() {
  const navigate = useNavigate()
  const [documents, setDocuments] = useState<DocumentListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [text, setText] = useState('')
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)

  const load = useCallback(async () => {
    setError('')
    const result = await documentsApi.list()
    setDocuments(result.documents)
  }, [])

  useEffect(() => {
    load()
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [load])

  function onDrop(event: DragEvent) {
    event.preventDefault()
    setDragOver(false)
    const next = event.dataTransfer.files[0]
    if (next) setFile(next)
  }

  async function onUpload(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file && !text.trim()) {
      setError('Choose a file or paste some text.')
      return
    }
    setUploading(true)
    setError('')
    try {
      const uploaded = await documentsApi.upload(file ?? undefined, text)
      setFile(null)
      setText('')
      navigate(`/documents/${uploaded.document_id}`)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setUploading(false)
    }
  }

  async function onDelete(documentId: string, filename: string) {
    if (!window.confirm(`Delete “${filename}”? This cannot be undone.`)) return
    try {
      await documentsApi.delete(documentId)
      setDocuments((current) => current.filter((item) => item.document_id !== documentId))
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <AppShell>
      <div className="mb-8">
        <p className="text-sm uppercase tracking-[0.2em] text-copper">Library</p>
      </div>

      <Card className="mb-8">
        <h2 className="font-serif text-2xl">Upload Your Study Material</h2>
        <p className="mt-1 text-sm text-muted2">PDF, DOCX, TXT, or an image. You can also paste text.</p>
        <form onSubmit={onUpload} className="mt-4 space-y-4">
          {error ? <ErrorBanner message={error} /> : null}
          <label
            onDragOver={(event) => {
              event.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            className={`flex cursor-pointer flex-col items-center rounded-xl border border-dashed px-4 py-8 text-center ${
              dragOver ? 'border-copper bg-copper/5' : 'border-line'
            }`}
          >
            <input
              type="file"
              accept={ACCEPT}
              className="sr-only"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
            <span className="text-sm font-medium">{file ? file.name : 'Drop a file here, or click to browse'}</span>
            <span className="mt-1 text-xs text-muted2">Max useful for one chapter or unit at a time</span>
          </label>
          <label className="block text-sm">
            Or paste text
            <textarea
              className={`${fieldClass} mt-1 min-h-24`}
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Paste notes if you do not have a file…"
            />
          </label>
          <Button type="submit" disabled={uploading}>
            {uploading ? 'Uploading and parsing…' : 'Upload'}
          </Button>
        </form>
      </Card>

      <div className="mb-4">
        <h1 className="font-serif text-4xl">List of Document Uploaded Earlier</h1>
      </div>

      {loading ? (
        <Spinner label="Loading documents" />
      ) : documents.length === 0 ? (
        <EmptyState
          title="Nothing here yet"
          body="Upload a PDF or paste notes to generate summaries, questions, and a doubt chat."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {documents.map((doc) => (
            <Card key={doc.document_id} className="flex flex-col">
              <Link to={`/documents/${doc.document_id}`} className="flex-1">
                <p className="text-xs uppercase tracking-wide text-muted2">{doc.detected_type}</p>
                <h3 className="mt-1 font-serif text-xl">{doc.filename}</h3>
                <p className="mt-2 text-sm text-muted2">
                  {formatDate(doc.created_at)} · {doc.question_count} generated question
                  {doc.question_count === 1 ? '' : 's'}
                </p>
              </Link>
              <div className="mt-4 flex gap-2">
                <Link
                  to={`/documents/${doc.document_id}`}
                  className="rounded-lg bg-forest px-3 py-2 text-sm text-paper hover:bg-forest-soft"
                >
                  Open
                </Link>
                <Button variant="danger" onClick={() => onDelete(doc.document_id, doc.filename)}>
                  Delete
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </AppShell>
  )
}
