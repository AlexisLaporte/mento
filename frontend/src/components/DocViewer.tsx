import { useEffect, useRef, useState, useCallback } from 'react'
import mammoth from 'mammoth'

interface DocData {
  path: string
  kind: string
  frontmatter?: Record<string, string>
  html?: string
  toc?: { level: number; id: string; text: string }[]
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

function DocxViewer({ doc }: { doc: DocData }) {
  const [html, setHtml] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const convert = useCallback(async () => {
    if (!doc.download_url) return
    try {
      const res = await fetch(doc.download_url)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const arrayBuffer = await res.arrayBuffer()
      const result = await mammoth.convertToHtml({ arrayBuffer })
      setHtml(result.value)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load document')
    }
  }, [doc.download_url])

  useEffect(() => { convert() }, [convert])

  const fileName = doc.path.split('/').pop() || ''

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 md:p-6">
      <div className="mb-4 pb-3 border-b">
        <h1 className="text-xl font-bold">{fileName}</h1>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-xs text-muted-foreground font-mono">{doc.path}</span>
          {doc.download_url && (
            <a href={doc.download_url} download={fileName} className="text-xs text-primary hover:underline">
              Download
            </a>
          )}
        </div>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      {!html && !error && <p className="text-sm text-muted-foreground">Loading...</p>}
      {html && <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />}
    </div>
  )
}

function BinaryViewer({ doc }: { doc: DocData }) {
  const fileName = doc.path.split('/').pop() || ''
  const ext = fileName.includes('.') ? fileName.split('.').pop()?.toUpperCase() : 'FILE'
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 gap-4">
      <div className="w-16 h-16 rounded-xl bg-muted flex items-center justify-center text-2xl font-bold text-muted-foreground">
        .{ext?.toLowerCase()}
      </div>
      <div className="text-center">
        <p className="font-medium">{fileName}</p>
        <p className="text-xs text-muted-foreground mt-1">
          {ext} file {doc.size ? `— ${(doc.size / 1024).toFixed(1)} KB` : ''}
        </p>
      </div>
      {doc.download_url && (
        <a
          href={doc.download_url}
          download={fileName}
          className="px-4 py-2 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          Download
        </a>
      )}
    </div>
  )
}

export function DocViewer({
  doc,
  project,
  editBaseUrl,
  prevDoc,
  nextDoc,
  onNavigate,
}: {
  doc: DocData | null
  project?: string
  editBaseUrl?: string
  prevDoc?: NavDoc | null
  nextDoc?: NavDoc | null
  onNavigate?: (path: string) => void
}) {
  const contentRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement | null>(null)
  const tooltipCache = useRef<Map<string, { title: string; excerpt: string }>>(new Map())

  // Mermaid + copy buttons + doc link tooltips
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

    // Doc link tooltips
    if (!project || !doc?.path) return
    const docDir = doc.path.includes('/') ? doc.path.substring(0, doc.path.lastIndexOf('/') + 1) : ''
    let hideTimeout: ReturnType<typeof setTimeout>

    // Create tooltip element once
    if (!tooltipRef.current) {
      const tip = document.createElement('div')
      tip.className = 'doc-link-tooltip'
      tip.innerHTML = '<div class="tooltip-title"></div><div class="tooltip-excerpt"></div>'
      document.body.appendChild(tip)
      tooltipRef.current = tip
    }
    const tooltip = tooltipRef.current

    function showTooltip(anchor: HTMLAnchorElement, data: { title: string; excerpt: string }) {
      const titleEl = tooltip.querySelector('.tooltip-title') as HTMLElement
      const excerptEl = tooltip.querySelector('.tooltip-excerpt') as HTMLElement
      titleEl.textContent = data.title
      excerptEl.textContent = data.excerpt
      const rect = anchor.getBoundingClientRect()
      tooltip.style.left = `${Math.max(8, Math.min(rect.left, window.innerWidth - 336))}px`
      tooltip.style.top = `${rect.bottom + 6}px`
      tooltip.classList.add('visible')
    }

    function hideTooltip() {
      hideTimeout = setTimeout(() => tooltip.classList.remove('visible'), 100)
    }

    const mdLinks = container.querySelectorAll<HTMLAnchorElement>('a[href$=".md"]')
    const cleanups: (() => void)[] = []

    mdLinks.forEach(link => {
      const href = link.getAttribute('href') || ''
      if (href.startsWith('http') || href.startsWith('#')) return
      const resolvedPath = href.startsWith('/') ? href.slice(1) : docDir + href

      const onEnter = async () => {
        clearTimeout(hideTimeout)
        const cached = tooltipCache.current.get(resolvedPath)
        if (cached) { showTooltip(link, cached); return }
        try {
          const res = await fetch(`/${project}/api/doc/${encodeURI(resolvedPath)}`)
          if (!res.ok) return
          const data = await res.json()
          const title = data.frontmatter?.title || resolvedPath.split('/').pop()?.replace(/\.md$/i, '') || resolvedPath
          let excerpt = data.frontmatter?.summary || ''
          if (!excerpt && data.html) {
            const tmp = document.createElement('div')
            tmp.innerHTML = data.html
            const firstP = tmp.querySelector('p')
            excerpt = firstP?.textContent?.slice(0, 200) || ''
          }
          const entry = { title, excerpt }
          tooltipCache.current.set(resolvedPath, entry)
          showTooltip(link, entry)
        } catch { /* ignore */ }
      }
      const onLeave = () => hideTooltip()

      link.addEventListener('mouseenter', onEnter)
      link.addEventListener('mouseleave', onLeave)
      cleanups.push(() => {
        link.removeEventListener('mouseenter', onEnter)
        link.removeEventListener('mouseleave', onLeave)
      })
    })

    return () => { cleanups.forEach(fn => fn()); clearTimeout(hideTimeout) }
  }, [doc?.path, doc?.html, project])

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
  if (doc.kind === 'docx') return <DocxViewer doc={doc} />
  if (doc.kind === 'binary') return <BinaryViewer doc={doc} />

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
  )
}
