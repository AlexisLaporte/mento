import { useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiGet, ApiError } from '@/lib/api'
import { DocViewer } from '@/components/DocViewer'
import { TocSidebar } from '@/components/TocSidebar'

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

interface TreeNode {
  name: string
  path: string
  type: 'file' | 'dir'
  kind?: string
  children?: TreeNode[]
}

interface ProjectConfig {
  slug: string; title: string; color: string; repo_full_name: string; owner_email: string
}

function countFiles(nodes: TreeNode[]): { files: number; dirs: number } {
  let files = 0, dirs = 0
  for (const n of nodes) {
    if (n.type === 'file') files++
    else if (n.children) { dirs++; const c = countFiles(n.children); files += c.files; dirs += c.dirs }
  }
  return { files, dirs }
}

function flattenTree(nodes: TreeNode[]): { path: string; name: string }[] {
  const result: { path: string; name: string }[] = []
  for (const node of nodes) {
    if (node.type === 'file') {
      result.push({ path: node.path, name: node.name })
    } else if (node.children) {
      result.push(...flattenTree(node.children))
    }
  }
  return result
}

export default function DocPage() {
  const { project, '*': splat } = useParams()
  const navigate = useNavigate()
  const docPath = splat || ''
  const projectBase = `/${project}`

  const { data: doc } = useQuery({
    queryKey: ['doc', project, docPath],
    queryFn: () => apiGet<DocData>(`${projectBase}/api/doc/${encodeURI(docPath)}`),
    enabled: !!docPath,
  })

  const { data: settings } = useQuery({
    queryKey: ['settings', project],
    queryFn: () => apiGet<{ project: ProjectConfig; is_owner: boolean }>(`${projectBase}/api/settings`).catch(() => null),
    retry: false,
  })

  const { data: tree = [], error: treeError } = useQuery({
    queryKey: ['tree', project],
    queryFn: () => apiGet<TreeNode[]>(`${projectBase}/api/tree`),
    retry: (count, err) => !(err instanceof ApiError && (err.status === 401 || err.status === 403)) && count < 2,
  })

  const flatFiles = useMemo(() => flattenTree(tree), [tree])
  const currentIdx = flatFiles.findIndex(f => f.path === docPath)
  const prevDoc = currentIdx > 0 ? flatFiles[currentIdx - 1] : null
  const nextDoc = currentIdx >= 0 && currentIdx < flatFiles.length - 1 ? flatFiles[currentIdx + 1] : null

  const config = settings?.project
  const editBaseUrl = config?.repo_full_name
    ? `https://github.com/${config.repo_full_name}/edit/main/`
    : undefined

  const currentDoc = docPath ? (doc || null) : null
  const stats = useMemo(() => countFiles(tree), [tree])
  const readmeFile = flatFiles.find(f => /^readme\.md$/i.test(f.name))

  // Auth required — private project, not logged in
  if (treeError instanceof ApiError && (treeError.status === 401 || treeError.status === 403)) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <h2 className="text-xl font-semibold">Sign in required</h2>
          <p className="text-muted-foreground text-sm">You need to be a member to access this project.</p>
          <a href="/auth/login" className="inline-block px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm hover:bg-primary/90 transition">
            Sign in
          </a>
        </div>
      </div>
    )
  }

  // Project home — no doc selected
  if (!docPath) {
    return (
      <div className="h-full overflow-y-auto px-6 py-8 max-w-3xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          {config?.color && <div className="w-4 h-4 rounded-full shrink-0" style={{ background: config.color }} />}
          <h1 className="text-2xl font-bold font-serif">{config?.title || project}</h1>
        </div>

        {config?.repo_full_name && (
          <a
            href={`https://github.com/${config.repo_full_name}`}
            target="_blank"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition mb-6"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
            {config.repo_full_name}
          </a>
        )}

        {/* Stats */}
        <div className="flex gap-6 mb-8">
          <div className="text-center">
            <div className="text-2xl font-bold">{stats.files}</div>
            <div className="text-xs text-muted-foreground">files</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold">{stats.dirs}</div>
            <div className="text-xs text-muted-foreground">folders</div>
          </div>
        </div>

        {/* Quick links */}
        {flatFiles.length > 0 && (
          <div>
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-3">Documents</h2>
            <div className="space-y-1">
              {flatFiles.slice(0, 12).map(f => (
                <button
                  key={f.path}
                  onClick={() => navigate(`${projectBase}/${f.path}`)}
                  className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm hover:bg-muted transition text-left"
                >
                  <span className="text-muted-foreground">
                    {f.name.endsWith('.md') ? '📄' : f.name.match(/\.(png|jpg|svg|webp)$/i) ? '🖼' : f.name.endsWith('.pdf') ? '📕' : '📝'}
                  </span>
                  <span className="truncate">{f.name.replace(/\.md$/i, '')}</span>
                  <span className="text-xs text-muted-foreground ml-auto truncate max-w-[200px]">{f.path.includes('/') ? f.path.substring(0, f.path.lastIndexOf('/')) : ''}</span>
                </button>
              ))}
              {flatFiles.length > 12 && (
                <p className="text-xs text-muted-foreground px-3 pt-1">and {flatFiles.length - 12} more files</p>
              )}
            </div>
          </div>
        )}

        {readmeFile && (
          <button
            onClick={() => navigate(`${projectBase}/${readmeFile.path}`)}
            className="mt-6 text-sm text-primary hover:underline"
          >
            Open README →
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="h-full flex">
      {currentDoc?.kind === 'markdown' && (
        <TocSidebar headings={currentDoc.toc || []} />
      )}
      <DocViewer
        doc={currentDoc}
        project={project}
        editBaseUrl={editBaseUrl}
        prevDoc={prevDoc}
        nextDoc={nextDoc}
        onNavigate={(path) => navigate(`${projectBase}/${path}`)}
      />
    </div>
  )
}
