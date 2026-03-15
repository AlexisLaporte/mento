import { useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/lib/api'
import { DocViewer } from '@/components/DocViewer'

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

  const { data: tree = [] } = useQuery({
    queryKey: ['tree', project],
    queryFn: () => apiGet<TreeNode[]>(`${projectBase}/api/tree`),
  })

  const flatFiles = useMemo(() => flattenTree(tree), [tree])
  const currentIdx = flatFiles.findIndex(f => f.path === docPath)
  const prevDoc = currentIdx > 0 ? flatFiles[currentIdx - 1] : null
  const nextDoc = currentIdx >= 0 && currentIdx < flatFiles.length - 1 ? flatFiles[currentIdx + 1] : null

  const config = settings?.project
  const editBaseUrl = config?.repo_full_name
    ? `https://github.com/${config.repo_full_name}/edit/main/`
    : undefined

  return (
    <div className="h-full flex">
      <DocViewer
        doc={docPath ? (doc || null) : null}
        editBaseUrl={editBaseUrl}
        prevDoc={prevDoc}
        nextDoc={nextDoc}
        onNavigate={(path) => navigate(`${projectBase}/${path}`)}
      />
    </div>
  )
}
