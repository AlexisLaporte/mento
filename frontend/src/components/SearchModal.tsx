import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/lib/api'

interface SearchResult {
  path: string
  name: string
  kind: string
}

interface Project {
  slug: string
  title: string
  color: string
}

const KIND_ICONS: Record<string, string> = {
  markdown: '📄',
  image: '🖼',
  text: '📝',
  pdf: '📕',
}

export function SearchModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState('')
  const [selectedIdx, setSelectedIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiGet<Project[]>('/api/projects'),
    enabled: open,
  })

  // Determine current project from URL
  const currentProject = window.location.pathname.split('/').filter(Boolean)[0] || ''
  const isInProject = projects.some(p => p.slug === currentProject)

  const { data: searchResults = [] } = useQuery({
    queryKey: ['search', currentProject, query],
    queryFn: () => apiGet<SearchResult[]>(`/${currentProject}/api/search?q=${encodeURIComponent(query)}`),
    enabled: open && !!query && query.length >= 2 && isInProject,
  })

  // Filter projects by query
  const matchingProjects = query.length >= 1
    ? projects.filter(p => p.title.toLowerCase().includes(query.toLowerCase()) || p.slug.toLowerCase().includes(query.toLowerCase()))
    : []

  const allResults = [
    ...matchingProjects.map(p => ({ type: 'project' as const, project: p })),
    ...searchResults.map(r => ({ type: 'doc' as const, result: r })),
  ]

  // Reset selection when results change
  useEffect(() => { setSelectedIdx(0) }, [allResults.length])

  // Focus input on open
  useEffect(() => {
    if (open) {
      setQuery('')
      setSelectedIdx(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  // Keyboard shortcut
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        if (open) onClose()
        else onClose() // toggle handled in App
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open, onClose])

  const handleSelect = useCallback((idx: number) => {
    const item = allResults[idx]
    if (!item) return
    if (item.type === 'project') {
      navigate(`/${item.project.slug}/`)
    } else {
      navigate(`/${currentProject}/${item.result.path}`)
    }
    onClose()
  }, [allResults, currentProject, navigate, onClose])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIdx(i => Math.min(i + 1, allResults.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIdx(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      handleSelect(selectedIdx)
    } else if (e.key === 'Escape') {
      onClose()
    }
  }

  if (!open) return null

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-50" onClick={onClose} />
      <div className="fixed top-[15%] left-1/2 -translate-x-1/2 w-full max-w-lg z-50 px-4">
        <div className="bg-card rounded-xl border shadow-2xl overflow-hidden">
          {/* Search input */}
          <div className="flex items-center gap-3 px-4 py-3 border-b">
            <svg className="w-4 h-4 text-muted-foreground shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              ref={inputRef}
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isInProject ? 'Search docs and projects...' : 'Search projects...'}
              className="flex-1 bg-transparent outline-none text-sm placeholder:text-muted-foreground"
            />
            <kbd className="hidden sm:inline-block text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">ESC</kbd>
          </div>

          {/* Results */}
          <div className="max-h-80 overflow-y-auto py-1">
            {query.length < 1 ? (
              <p className="text-sm text-muted-foreground text-center py-6">Start typing to search...</p>
            ) : allResults.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-6">No results</p>
            ) : (
              allResults.map((item, idx) => (
                <button
                  key={item.type === 'project' ? `p-${item.project.slug}` : `d-${item.result.path}`}
                  onClick={() => handleSelect(idx)}
                  onMouseEnter={() => setSelectedIdx(idx)}
                  className={`w-full text-left flex items-center gap-3 px-4 py-2 text-sm transition-colors ${
                    idx === selectedIdx ? 'bg-accent' : 'hover:bg-accent/50'
                  }`}
                >
                  {item.type === 'project' ? (
                    <>
                      <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: item.project.color }} />
                      <div className="min-w-0 flex-1">
                        <div className="font-medium truncate">{item.project.title}</div>
                        <div className="text-xs text-muted-foreground">{item.project.slug}</div>
                      </div>
                      <span className="text-xs text-muted-foreground shrink-0">Project</span>
                    </>
                  ) : (
                    <>
                      <span className="text-base shrink-0">{KIND_ICONS[item.result.kind] || '📄'}</span>
                      <div className="min-w-0 flex-1">
                        <div className="font-medium truncate">{item.result.name}</div>
                        <div className="text-xs text-muted-foreground truncate">{item.result.path}</div>
                      </div>
                      <span className="text-xs text-muted-foreground shrink-0 capitalize">{item.result.kind}</span>
                    </>
                  )}
                </button>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 border-t flex items-center gap-4 text-[10px] text-muted-foreground">
            <span><kbd className="bg-muted px-1 py-0.5 rounded">↑↓</kbd> Navigate</span>
            <span><kbd className="bg-muted px-1 py-0.5 rounded">↵</kbd> Open</span>
            <span><kbd className="bg-muted px-1 py-0.5 rounded">ESC</kbd> Close</span>
          </div>
        </div>
      </div>
    </>
  )
}
