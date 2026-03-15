import { useEffect, useRef } from 'react'

interface DocData {
  path: string
  frontmatter: Record<string, string>
  html: string
}

function statusVariant(status: string) {
  const s = status.toLowerCase()
  if (s.includes('draft')) return 'bg-amber-100 text-amber-800'
  if (s.includes('review') || s.includes('alignment')) return 'bg-blue-100 text-blue-800'
  if (s.includes('approved') || s.includes('done') || s.includes('ready')) return 'bg-green-100 text-green-800'
  return 'bg-muted text-muted-foreground'
}

export function DocViewer({ doc, editBaseUrl }: { doc: DocData | null; editBaseUrl?: string }) {
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!contentRef.current) return
    // Render mermaid diagrams
    const mermaidEls = contentRef.current.querySelectorAll('pre > code.language-mermaid')
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
  }, [doc?.path])

  if (!doc) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <p className="text-sm">Select a document from the sidebar</p>
      </div>
    )
  }

  const fm = doc.frontmatter || {}
  const title = fm.title || doc.path.split('/').pop()?.replace(/\.md$/, '') || ''

  return (
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
      <div ref={contentRef} className="prose" dangerouslySetInnerHTML={{ __html: doc.html }} />
    </div>
  )
}
