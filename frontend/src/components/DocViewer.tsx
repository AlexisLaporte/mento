import { useEffect, useRef, useState } from 'react'

interface TocHeading {
  level: number
  id: string
  text: string
}

interface DocData {
  path: string
  kind: string
  frontmatter?: Record<string, string>
  html?: string
  toc?: TocHeading[]
  content?: string
  download_url?: string
  size?: number
}

interface NavDoc {
  path: string
  name: string
}

function statusVariant(status: string) {
  const s = status.toLowerCase()
  if (s.includes('draft')) return 'bg-amber-100 text-amber-800'
  if (s.includes('review') || s.includes('alignment')) return 'bg-blue-100 text-blue-800'
  if (s.includes('approved') || s.includes('done') || s.includes('ready')) return 'bg-green-100 text-green-800'
  return 'bg-muted text-muted-foreground'
}

function TocSidebar({ headings, activeId }: { headings: TocHeading[]; activeId: string }) {
  if (headings.length < 2) return null

  return (
    <nav className="hidden xl:block w-52 shrink-0 sticky top-6 self-start max-h-[calc(100vh-3rem)] overflow-y-auto">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">On this page</p>
      <ul className="space-y-0.5 text-sm">
        {headings.map(h => (
          <li key={h.id} style={{ paddingLeft: `${(h.level - 2) * 0.75}rem` }}>
            <a
              href={`#${h.id}`}
              className={`block py-0.5 transition-colors truncate ${
                activeId === h.id
                  ? 'text-primary font-medium'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {h.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500) }}
      className="absolute top-2 right-2 px-2 py-1 text-xs rounded bg-white/10 hover:bg-white/20 text-white/70 hover:text-white transition-colors"
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

function useActiveHeading(headings: TocHeading[]): string {
  const [activeId, setActiveId] = useState('')

  useEffect(() => {
    if (headings.length < 2) return
    const observer = new IntersectionObserver(
      entries => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id)
            break
          }
        }
      },
      { rootMargin: '-80px 0px -70% 0px', threshold: 0 }
    )
    headings.forEach(h => {
      const el = document.getElementById(h.id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [headings])

  return activeId
}

function ImageViewer({ doc }: { doc: DocData }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 gap-4">
      <img
        src={doc.download_url}
        alt={doc.path.split('/').pop() || ''}
        className="max-w-full max-h-[70vh] object-contain rounded-lg border"
      />
      <div className="text-xs text-muted-foreground">
        {doc.path.split('/').pop()} {doc.size ? `— ${(doc.size / 1024).toFixed(1)} KB` : ''}
      </div>
    </div>
  )
}

function TextViewer({ doc }: { doc: DocData }) {
  const ext = doc.path.split('.').pop() || ''
  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 md:p-6">
      <div className="mb-4 pb-3 border-b">
        <h1 className="text-xl font-bold">{doc.path.split('/').pop()}</h1>
        <span className="text-xs text-muted-foreground font-mono">{doc.path}</span>
      </div>
      <div className="relative">
        <CopyButton text={doc.content || ''} />
        <pre className="bg-[oklch(0.15_0_0)] text-[oklch(0.85_0_0)] p-4 rounded-lg overflow-x-auto text-sm leading-relaxed">
          <code className={`language-${ext}`}>{doc.content}</code>
        </pre>
      </div>
    </div>
  )
}

function PdfViewer({ doc }: { doc: DocData }) {
  return (
    <div className="flex-1 flex flex-col p-4 md:p-6 gap-3">
      <div className="pb-3 border-b">
        <h1 className="text-xl font-bold">{doc.path.split('/').pop()}</h1>
        <span className="text-xs text-muted-foreground font-mono">{doc.path}</span>
      </div>
      <iframe
        src={doc.download_url}
        className="flex-1 w-full rounded-lg border min-h-[60vh]"
        title={doc.path}
      />
      <a
        href={doc.download_url}
        target="_blank"
        className="text-xs text-primary hover:underline self-start"
      >
        Open in new tab
      </a>
    </div>
  )
}

export function DocViewer({
  doc,
  editBaseUrl,
  prevDoc,
  nextDoc,
  onNavigate,
}: {
  doc: DocData | null
  editBaseUrl?: string
  prevDoc?: NavDoc | null
  nextDoc?: NavDoc | null
  onNavigate?: (path: string) => void
}) {
  const contentRef = useRef<HTMLDivElement>(null)
  const headings = doc?.toc || []
  const activeId = useActiveHeading(headings)

  // Mermaid + copy buttons on code blocks
  useEffect(() => {
    if (!contentRef.current) return
    const container = contentRef.current

    // Mermaid
    const mermaidEls = container.querySelectorAll('pre > code.language-mermaid')
    if (mermaidEls.length > 0) {
      import('mermaid').then(({ default: mermaid }) => {
        mermaid.initialize({ startOnLoad: false, theme: 'neutral' })
        mermaidEls.forEach((el, i) => {
          const pre = el.parentElement!
          const div = document.createElement('div')
          div.className = 'mermaid'
          div.id = `mermaid-${i}`
          div.textContent = el.textContent || ''
          pre.replaceWith(div)
        })
        mermaid.run()
      })
    }

    // Add copy buttons to code blocks
    container.querySelectorAll('pre').forEach(pre => {
      if (pre.querySelector('.copy-btn')) return
      const btn = document.createElement('button')
      btn.className = 'copy-btn absolute top-2 right-2 px-2 py-1 text-xs rounded bg-white/10 hover:bg-white/20 text-white/70 hover:text-white transition-colors opacity-0 group-hover:opacity-100'
      btn.textContent = 'Copy'
      btn.onclick = () => {
        const code = pre.querySelector('code')?.textContent || pre.textContent || ''
        navigator.clipboard.writeText(code)
        btn.textContent = 'Copied!'
        setTimeout(() => { btn.textContent = 'Copy' }, 1500)
      }
      pre.style.position = 'relative'
      pre.classList.add('group')
      pre.appendChild(btn)
    })
  }, [doc?.path, doc?.html])

  if (!doc) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <p className="text-sm">Select a document from the sidebar</p>
      </div>
    )
  }

  // Non-markdown viewers
  if (doc.kind === 'image') return <ImageViewer doc={doc} />
  if (doc.kind === 'text') return <TextViewer doc={doc} />
  if (doc.kind === 'pdf') return <PdfViewer doc={doc} />

  const fm = doc.frontmatter || {}
  const title = fm.title || doc.path.split('/').pop()?.replace(/\.md$/, '') || ''

  return (
    <div className="flex-1 flex overflow-hidden">
      <div className="flex-1 overflow-y-auto px-4 py-4 md:p-6">
        {/* Frontmatter bar */}
        <div className="mb-4 pb-3 border-b">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold">{title}</h1>
            {fm.status && (
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusVariant(fm.status)}`}>
                {fm.status}
              </span>
            )}
          </div>
          {fm.summary && <p className="text-sm text-muted-foreground mt-1">{fm.summary}</p>}
          <div className="flex items-center gap-3 mt-2">
            <span className="text-xs text-muted-foreground font-mono">{doc.path}</span>
            {editBaseUrl && (
              <a href={`${editBaseUrl}${doc.path}`} target="_blank" className="text-xs text-primary hover:underline">
                Edit on GitHub
              </a>
            )}
          </div>
        </div>

        {/* Rendered markdown */}
        <div ref={contentRef} className="prose" dangerouslySetInnerHTML={{ __html: doc.html || '' }} />

        {/* Prev / Next navigation */}
        {(prevDoc || nextDoc) && (
          <div className="flex items-center justify-between mt-8 pt-4 border-t gap-4">
            {prevDoc ? (
              <button
                onClick={() => onNavigate?.(prevDoc.path)}
                className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors min-w-0"
              >
                <span className="shrink-0">←</span>
                <span className="truncate">{prevDoc.name.replace(/\.md$/i, '')}</span>
              </button>
            ) : <span />}
            {nextDoc ? (
              <button
                onClick={() => onNavigate?.(nextDoc.path)}
                className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors min-w-0 ml-auto"
              >
                <span className="truncate">{nextDoc.name.replace(/\.md$/i, '')}</span>
                <span className="shrink-0">→</span>
              </button>
            ) : <span />}
          </div>
        )}
      </div>

      {/* TOC sidebar */}
      <TocSidebar headings={headings} activeId={activeId} />
    </div>
  )
}
