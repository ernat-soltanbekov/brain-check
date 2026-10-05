import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { BookOpen, Plus } from 'lucide-react'
import { requireAuth } from '../utils/guards'
import { api } from '../utils/apiClient'
import { useApi } from '../hooks/useApi'
import { Loading, ErrorMessage, PageHeading } from '../components/UI'
export const Route = createFileRoute('/material')({ beforeLoad: requireAuth, component: Material })
function Material() {
  const [page, setPage] = useState(1),
    { data, error, loading, reload } = useApi(`/material/?page=${page}`)
  const [busy, setBusy] = useState(false),
    [saveError, setSaveError] = useState(null),
    [saved, setSaved] = useState(false)
  const [file, setFile] = useState(null)
  async function submit(event) {
    event.preventDefault()
    const form = event.currentTarget
    setBusy(true)
    setSaveError(null)
    setSaved(false)
    const body = new FormData(form)
    if (!file) body.delete('file')
    else body.delete('content')
    try {
      await api('/material/', { method: 'POST', body })
      form.reset()
      setFile(null)
      setSaved(true)
      reload()
    } catch (e) {
      setSaveError(e)
    } finally {
      setBusy(false)
    }
  }
  return (
    <>
      <PageHeading
        eyebrow="THE SOURCE OF UNDERSTANDING"
        title="Study notes"
        text="Good questions begin with good material. Add the concepts you actually want to learn."
      />
      <form className="panel" onSubmit={submit}>
        <div className="section-heading">
          <h2>
            <BookOpen size={20} /> Add to your field notes
          </h2>
          <span className="tiny-label">PRIVATE TO YOUR ACCOUNT</span>
        </div>
        <ErrorMessage error={saveError} />
        {saved && (
          <p className="success" role="status">
            Notes saved. You can now generate a quiz on this topic.
          </p>
        )}
        <fieldset disabled={busy}>
          <div className="form-grid">
            <label className="field">
              Topic
              <input required name="topic" maxLength={100} placeholder="e.g. embeddings" />
            </label>
            <label className="field">
              Title
              <input required name="title" maxLength={180} placeholder="A short, useful title" />
            </label>
          </div>
          <label className="field">
            Paste your notes
            <textarea
              name="content"
              rows={7}
              minLength={30}
              maxLength={20000}
              required={!file}
              disabled={!!file}
              placeholder="Explain the concepts, definitions and examples you want to practice…"
            />
          </label>
          <div className="upload-row">
            <label className="field">
              Or upload a text file
              <input
                name="file"
                type="file"
                accept=".txt,.md,text/plain,text/markdown"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
            <span className="muted small">
              UTF-8 .txt or .md · 100 KB maximum
              <br />
              30–20,000 characters
            </span>
          </div>
          <button disabled={busy}>
            <Plus size={18} />
            {busy ? 'Saving notes…' : 'Save study notes'}
          </button>
        </fieldset>
      </form>
      <div className="section-heading">
        <h2>Your source library</h2>
        <span className="tiny-label">{data?.count || 0} NOTES</span>
      </div>
      <ErrorMessage error={error} retry={reload} />
      {loading ? (
        <Loading />
      ) : (
        <div className="notes-grid">
          {data?.results.map((note) => (
            <details className="panel note" key={note.id}>
              <summary>
                <BookOpen size={20} />
                <div>
                  <span className="eyebrow">{note.topic}</span>
                  <h3>{note.title}</h3>
                </div>
                <Plus size={18} />
              </summary>
              <div className="note-content">{note.content}</div>
            </details>
          ))}
        </div>
      )}
      <div className="pagination">
        <button
          className="secondary"
          disabled={!data?.previous}
          onClick={() => setPage((p) => p - 1)}
        >
          Previous
        </button>
        <span>Page {page}</span>
        <button className="secondary" disabled={!data?.next} onClick={() => setPage((p) => p + 1)}>
          Next
        </button>
      </div>
    </>
  )
}
