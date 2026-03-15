import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/hooks/use-auth'
import { apiGet, apiPost } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface Installation { id: number; account: string; avatar: string }
interface Repo { full_name: string; name: string; private: boolean }

export default function NewProjectPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [installationId, setInstallationId] = useState('')
  const [repo, setRepo] = useState('')
  const [slug, setSlug] = useState('')
  const [title, setTitle] = useState('')
  const [color, setColor] = useState('#6366F1')
  const [docsPaths, setDocsPaths] = useState('docs')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const githubConnected = user?.github_connected ?? false

  const { data: installations = [] } = useQuery({
    queryKey: ['installations'],
    queryFn: () => apiGet<Installation[]>('/api/installations'),
    enabled: githubConnected,
  })

  const { data: repos = [], isLoading: loadingRepos } = useQuery({
    queryKey: ['repos', installationId],
    queryFn: () => apiGet<Repo[]>(`/api/installations/${installationId}/repos`),
    enabled: !!installationId,
  })

  const { data: appInfo } = useQuery({
    queryKey: ['github-app-name'],
    queryFn: () => apiGet<{ name: string }>('/api/github-app-name'),
    enabled: githubConnected,
  })

  function onRepoChange(fullName: string) {
    setRepo(fullName)
    const name = fullName.split('/').pop() || ''
    if (!slug) setSlug(name.toLowerCase())
    if (!title) setTitle(name.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()))
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const res = await apiPost<{ slug: string }>('/api/projects', {
        slug, title, repo, color,
        docs_paths: docsPaths.split(',').map(s => s.trim()).filter(Boolean),
      })
      navigate(`/${res.slug}/`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="max-w-lg mx-auto px-6 pt-10 pb-20">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-lg font-semibold">New project</h1>
        <Button variant="ghost" size="sm" onClick={() => navigate('/')}>Cancel</Button>
      </div>

      {!githubConnected ? (
        <div className="bg-card rounded-lg border p-6 text-center">
          <p className="text-sm text-muted-foreground mb-4">
            Connect your GitHub account to select a repository.
          </p>
          <a href="/auth/github">
            <Button>Connect GitHub</Button>
          </a>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="bg-card rounded-lg border p-6 space-y-4">
          <div>
            <Label>GitHub Account</Label>
            <Select value={installationId} onValueChange={v => { setInstallationId(v ?? ''); setRepo('') }}>
              <SelectTrigger className="mt-1"><SelectValue placeholder="Select account" /></SelectTrigger>
              <SelectContent>
                {installations.map(i => (
                  <SelectItem key={i.id} value={String(i.id)}>{i.account}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {appInfo && (
              <p className="text-xs text-muted-foreground mt-1">
                Don't see your account?{' '}
                <a href={`https://github.com/apps/${appInfo.name}/installations/new`} target="_blank" className="text-primary hover:underline">
                  Install the Memento GitHub App
                </a>
              </p>
            )}
          </div>

          <div>
            <Label>Repository</Label>
            <Select value={repo} onValueChange={v => onRepoChange(v ?? '')} disabled={!installationId || loadingRepos}>
              <SelectTrigger className="mt-1">
                <SelectValue placeholder={loadingRepos ? 'Loading...' : 'Select repo'} />
              </SelectTrigger>
              <SelectContent>
                {repos.map(r => (
                  <SelectItem key={r.full_name} value={r.full_name}>
                    {r.name}{r.private ? ' \u{1F512}' : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label>Slug (URL identifier)</Label>
            <Input value={slug} onChange={e => setSlug(e.target.value)} placeholder="my-project" pattern="[a-z0-9-]+" required className="mt-1" />
          </div>

          <div>
            <Label>Title</Label>
            <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="My Project" required className="mt-1" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Color</Label>
              <Input type="color" value={color} onChange={e => setColor(e.target.value)} className="mt-1 h-9 w-20" />
            </div>
            <div>
              <Label>Docs paths</Label>
              <Input value={docsPaths} onChange={e => setDocsPaths(e.target.value)} className="mt-1" />
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button type="submit" className="w-full" disabled={submitting || !repo || !slug || !title}>
            {submitting ? 'Creating...' : 'Create project'}
          </Button>
        </form>
      )}
    </main>
  )
}
