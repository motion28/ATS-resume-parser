import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { isParseResult } from './types'
import type { ParseResult } from './types'

type ConnectionStatus = 'checking' | 'connected' | 'error'
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL?.trim() || 'http://localhost:8000')
  .replace(/\/+$/, '')

export default function App() {
  const [connection, setConnection] = useState<ConnectionStatus>('checking')
  const [file, setFile] = useState<File | null>(null)
  const [isParsing, setIsParsing] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<ParseResult | null>(null)

  const warnings: string[] = []
  if (result) {
    if (!result.resume.name?.trim()) {
      warnings.push('No name was extracted. Check the raw text and original PDF.')
    }
    if (!result.resume.email?.trim()) {
      warnings.push('No email address was extracted. Check the raw text and original PDF.')
    }
    if (result.resume.skills.length === 0) {
      warnings.push('No skills were extracted. Check the raw text and original PDF.')
    }
    if (result.resume.experience.length === 0) {
      warnings.push('No work experience was extracted. Check the raw text and original PDF.')
    }
    if (result.resume.education.length === 0) {
      warnings.push('No education was extracted. Check the raw text and original PDF.')
    }
  }

  useEffect(() => {
    const controller = new AbortController()

    async function checkHealth() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/health`, {
          signal: controller.signal,
        })
        if (!response.ok) throw new Error('Health check failed')

        const data = await response.json()
        if (data.status !== 'ok') throw new Error('Unexpected health response')

        setConnection('connected')
      } catch {
        if (!controller.signal.aborted) setConnection('error')
      }
    }

    void checkHealth()
    return () => controller.abort()
  }, [])

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setResult(null)

    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please select a PDF file.')
      return
    }

    setIsParsing(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      // The browser sets the multipart Content-Type, including its boundary.
      const response = await fetch(`${API_BASE_URL}/api/parse`, {
        method: 'POST',
        body: formData,
      })
      const data = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(
          typeof data?.detail === 'string'
            ? data.detail
            : 'Could not parse this PDF. Please try again.',
        )
      }
      if (!isParseResult(data)) {
        throw new Error('The backend returned an unexpected response. Please try again.')
      }
      setResult(data)
    } catch (error) {
      setError(
        error instanceof TypeError
          ? 'Cannot reach the backend. It may be starting up. Please try again shortly.'
          : error instanceof Error
            ? error.message
            : 'Could not parse this PDF. Please try again.',
      )
    } finally {
      setIsParsing(false)
    }
  }

  return (
    <main>
      <header className="page-header">
        <p className="eyebrow">Resume extraction</p>
        <h1>ATS Resume Parser</h1>
        <p className="subtitle">
          See what an automated resume parser can extract from your resume.
        </p>
      </header>

      <form className="upload-area" onSubmit={handleUpload} aria-busy={isParsing}>
        <label htmlFor="resume">Choose a PDF resume</label>
        <div className="upload-controls">
          <input
            id="resume"
            type="file"
            accept=".pdf,application/pdf"
            disabled={isParsing}
            aria-describedby="upload-help"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null)
              setError('')
              setResult(null)
            }}
          />
          <button type="submit" disabled={!file || isParsing}>
            {isParsing ? 'Reading and analyzing…' : 'Upload Resume'}
          </button>
        </div>
        {file && <p className="selected-filename">{file.name}</p>}
        <p id="upload-help">Use a text-based PDF. Scanned or image-only PDFs are not supported yet.</p>
        {isParsing && <p role="status">Reading and analyzing your PDF…</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </form>

      {result && (
        <div className="results">
          <div className="results-header">
            <p className="eyebrow">Extraction results</p>
            <p className="result-filename">{result.filename}</p>
            <p className="result-note">Extracted information may contain mistakes. Compare these results with your original resume.</p>
          </div>

          {warnings.length > 0 && (
            <section className="result-section parsing-warnings" aria-labelledby="warnings-heading">
              <h2 id="warnings-heading">Parsing warnings</h2>
              <ul>
                {warnings.map((warning) => <li key={warning}>{warning}</li>)}
              </ul>
            </section>
          )}

          <section className="result-section" aria-labelledby="contact-heading">
            <h2 id="contact-heading">Contact information</h2>
            <dl className="details">
              <div><dt>Name</dt><dd>{result.resume.name || 'Not found'}</dd></div>
              <div><dt>Email</dt><dd>{result.resume.email || 'Not found'}</dd></div>
              <div><dt>Phone</dt><dd>{result.resume.phone || 'Not found'}</dd></div>
              <div><dt>Location</dt><dd>{result.resume.location || 'Not found'}</dd></div>
            </dl>
          </section>

          <section className="result-section" aria-labelledby="skills-heading">
            <h2 id="skills-heading">Skills</h2>
            {result.resume.skills.length > 0 ? (
              <ul className="skills-list">
                {result.resume.skills.map((skill, index) => <li key={index}>{skill || 'Not found'}</li>)}
              </ul>
            ) : <p>No skills extracted.</p>}
          </section>

          <section className="result-section" aria-labelledby="experience-heading">
            <h2 id="experience-heading">Work experience</h2>
            {result.resume.experience.length > 0 ? result.resume.experience.map((experience, index) => (
              <article className="result-entry" key={index} aria-label={`Work experience ${index + 1}`}>
                <dl className="details">
                  <div><dt>Company</dt><dd>{experience.company || 'Not found'}</dd></div>
                  <div><dt>Title</dt><dd>{experience.title || 'Not found'}</dd></div>
                  <div><dt>Start date</dt><dd>{experience.start_date || 'Not found'}</dd></div>
                  <div><dt>End date</dt><dd>{experience.end_date || 'Not found'}</dd></div>
                  <div className="full-width"><dt>Description</dt><dd className="description">{experience.description || 'Not found'}</dd></div>
                </dl>
              </article>
            )) : <p>No work experience extracted.</p>}
          </section>

          <section className="result-section" aria-labelledby="education-heading">
            <h2 id="education-heading">Education</h2>
            {result.resume.education.length > 0 ? result.resume.education.map((education, index) => (
              <article className="result-entry" key={index} aria-label={`Education ${index + 1}`}>
                <dl className="details">
                  <div><dt>Institution</dt><dd>{education.institution || 'Not found'}</dd></div>
                  <div><dt>Degree</dt><dd>{education.degree || 'Not found'}</dd></div>
                  <div><dt>Field of study</dt><dd>{education.field_of_study || 'Not found'}</dd></div>
                  <div><dt>Graduation date</dt><dd>{education.graduation_date || 'Not found'}</dd></div>
                </dl>
              </article>
            )) : <p>No education extracted.</p>}
          </section>

          <section className="extracted-text" aria-labelledby="text-heading">
            <h2 id="text-heading">Raw extracted text</h2>
            <pre>{result.text}</pre>
          </section>
        </div>
      )}

      <p className={`connection ${connection}`} role="status">
        {connection === 'checking' && 'Checking backend connection…'}
        {connection === 'connected' && 'Backend connected — status: ok'}
        {connection === 'error' &&
          'Cannot reach the backend. It may be starting up. Please refresh this page shortly.'}
      </p>
    </main>
  )
}
