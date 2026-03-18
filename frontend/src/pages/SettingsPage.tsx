import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPut, apiPost, apiDelete } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'

interface ProjectConfig {
  slug: string; title: string; color: string; repo_full_name: string
  docs_paths: string[]; allowed_files: string[]; owner_email: string; custom_domain: string
  is_public: boolean
}
interface Member {
  email: string; name: string; picture: string; role: string; created_at: string
}
interface SettingsData {
  project: ProjectConfig; members: Member[]; is_owner: boolean; mcp_url: string
}

export default function SettingsPage() {
  const { project } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const projectBase = `/${project}`

  const { data, isLoading } = useQuery({
    queryKey: ['settings', project],
    queryFn: () => apiGet<SettingsData>(`${projectBase}/api/settings`),
  })

  if (isLoading || !data) return <p className="text-center py-20 text-muted-foreground text-sm">Loading...</p>

  return (
    <main className="max-w-3xl mx-auto px-4 sm:px-6 pt-6 pb-20">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-lg font-semibold">Settings</h1>
        <Link to={`${projectBase}/`} className="text-sm text-primary hover:underline">Back to docs</Link>
      </div>

      <ProjectSettingsForm config={data.project} projectBase={projectBase} queryClient={queryClient} />
      <Separator className="my-6" />
      <MembersSection members={data.members} projectBase={projectBase} queryClient={queryClient} />
      <Separator className="my-6" />
      <McpSection mcpUrl={data.mcp_url} />

      {data.is_owner && (
        <>
          <Separator className="my-6" />
          <DangerZone projectBase={projectBase} slug={project!} navigate={navigate} />
        </>
      )}
    </main>
  )
}

function ProjectSettingsForm({ config, projectBase, queryClient }: {
  config: ProjectConfig; projectBase: string; queryClient: ReturnType<typeof useQueryClient>
}) {
  const [title, setTitle] = useState(config.title)
  const [color, setColor] = useState(config.color)
  const [docsPaths, setDocsPaths] = useState(config.docs_paths.join(','))
  const [allowedFiles, setAllowedFiles] = useState(config.allowed_files.join(','))
  const [customDomain, setCustomDomain] = useState(config.custom_domain)
  const [isPublic, setIsPublic] = useState(config.is_public)

  const mut = useMutation({
    mutationFn: () => apiPut(`${projectBase}/api/settings`, {
      title, color,
      docs_paths: docsPaths.split(',').map(s => s.trim()).filter(Boolean),
      allowed_files: allowedFiles.split(',').map(s => s.trim()).filter(Boolean),
      custom_domain: customDomain.trim(),
      is_public: isPublic,
    }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['settings'] }),
  })

  return (
    <div className="bg-card rounded-lg border p-4">
      <h2 className="text-sm font-semibold mb-3">Project settings</h2>
      <form onSubmit={e => { e.preventDefault(); mut.mutate() }} className="space-y-3">
        <div className="grid sm:grid-cols-2 gap-3">
          <div><Label className="text-xs">Title</Label><Input value={title} onChange={e => setTitle(e.target.value)} className="mt-1" /></div>
          <div><Label className="text-xs">Color</Label><Input type="color" value={color} onChange={e => setColor(e.target.value)} className="mt-1 h-9 w-20" /></div>
        </div>
        <div><Label className="text-xs">Docs paths (comma-separated)</Label><Input value={docsPaths} onChange={e => setDocsPaths(e.target.value)} className="mt-1" /></div>
        <div><Label className="text-xs">Allowed root files</Label><Input value={allowedFiles} onChange={e => setAllowedFiles(e.target.value)} className="mt-1" /></div>
        <div>
          <Label className="text-xs">Custom domain</Label>
          <Input value={customDomain} onChange={e => setCustomDomain(e.target.value)} placeholder="docs.example.com" className="mt-1" />
          <p className="text-xs text-muted-foreground mt-1">Point a CNAME to <code className="text-primary">mento.cc</code> in your DNS</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={isPublic} onChange={e => setIsPublic(e.target.checked)} className="rounded border-input" />
            <span className="text-xs font-medium">Public access</span>
          </label>
          <span className="text-xs text-muted-foreground">Anyone can view docs without signing in</span>
        </div>
        <div className="flex items-center gap-3">
          <Button type="submit" size="sm" disabled={mut.isPending}>{mut.isPending ? 'Saving...' : 'Save settings'}</Button>
          {mut.isSuccess && <span className="text-xs text-green-600">Saved!</span>}
          {mut.isError && <span className="text-xs text-destructive">Error saving</span>}
        </div>
      </form>
    </div>
  )
}

function MembersSection({ members, projectBase, queryClient }: {
  members: Member[]; projectBase: string; queryClient: ReturnType<typeof useQueryClient>
}) {
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteName, setInviteName] = useState('')

  const roleMut = useMutation({
    mutationFn: ({ email, role }: { email: string; role: string }) =>
      apiPut(`${projectBase}/api/members/${email}/role`, { role }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['settings'] }),
  })

  const inviteMut = useMutation({
    mutationFn: () => apiPost(`${projectBase}/api/members/invite`, { email: inviteEmail, name: inviteName }),
    onSuccess: () => {
      setInviteEmail(''); setInviteName('')
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })

  const roleBadge = (role: string) => {
    const v = { admin: 'default', member: 'secondary', blocked: 'destructive' }[role] as 'default' | 'secondary' | 'destructive'
    return <Badge variant={v}>{role}</Badge>
  }

  return (
    <div>
      <h2 className="text-sm font-semibold mb-3">Members</h2>
      {/* Desktop table */}
      <div className="bg-card rounded-lg border overflow-hidden mb-4 hidden sm:block">
        <table className="w-full text-sm">
          <thead className="bg-muted text-xs text-muted-foreground uppercase">
            <tr><th className="px-4 py-2 text-left">Email</th><th className="px-4 py-2 text-left">Name</th><th className="px-4 py-2 text-left">Role</th><th className="px-4 py-2 text-left">Action</th></tr>
          </thead>
          <tbody>
            {members.map(m => (
              <tr key={m.email} className="border-t">
                <td className="px-4 py-2">{m.email}</td>
                <td className="px-4 py-2 text-muted-foreground">{m.name || ''}</td>
                <td className="px-4 py-2">{roleBadge(m.role)}</td>
                <td className="px-4 py-2">
                  <div className="flex gap-2 items-center">
                    <select
                      defaultValue={m.role}
                      onChange={e => roleMut.mutate({ email: m.email, role: e.target.value })}
                      className="text-xs border rounded px-2 py-1"
                    >
                      <option value="blocked">blocked</option>
                      <option value="member">member</option>
                      <option value="admin">admin</option>
                    </select>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile member cards */}
      <div className="sm:hidden space-y-2 mb-4">
        {members.map(m => (
          <div key={m.email} className="bg-card rounded-lg border p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium truncate">{m.email}</span>
              {roleBadge(m.role)}
            </div>
            {m.name && <p className="text-xs text-muted-foreground mb-2">{m.name}</p>}
            <select
              defaultValue={m.role}
              onChange={e => roleMut.mutate({ email: m.email, role: e.target.value })}
              className="text-xs border rounded px-2 py-1 w-full"
            >
              <option value="blocked">blocked</option>
              <option value="member">member</option>
              <option value="admin">admin</option>
            </select>
          </div>
        ))}
      </div>

      <div className="bg-card rounded-lg border p-4">
        <h3 className="text-sm font-semibold mb-2">Invite user</h3>
        <form onSubmit={e => { e.preventDefault(); inviteMut.mutate() }} className="flex flex-col sm:flex-row gap-2 sm:items-end">
          <div className="flex-1"><Label className="text-xs">Email</Label><Input value={inviteEmail} onChange={e => setInviteEmail(e.target.value)} type="email" required placeholder="user@example.com" className="mt-1" /></div>
          <div className="flex-1"><Label className="text-xs">Name</Label><Input value={inviteName} onChange={e => setInviteName(e.target.value)} placeholder="Optional" className="mt-1" /></div>
          <Button type="submit" size="sm" disabled={inviteMut.isPending} className="sm:w-auto">Invite</Button>
        </form>
      </div>
    </div>
  )
}

function McpSection({ mcpUrl }: { mcpUrl: string }) {
  return (
    <div className="bg-card rounded-lg border p-4">
      <h2 className="text-sm font-semibold mb-3">Claude AI connector (MCP)</h2>
      <p className="text-sm text-muted-foreground mb-3">
        Members can access this project's documentation directly from{' '}
        <a href="https://claude.ai" className="text-primary hover:underline" target="_blank">claude.ai</a>{' '}
        using the MCP connector.
      </p>
      <div className="bg-muted rounded p-3 space-y-2 text-xs">
        <div><span className="text-muted-foreground">1. In claude.ai, go to</span> <span className="font-medium">Settings &gt; Connectors &gt; Add</span></div>
        <div>
          <span className="text-muted-foreground">2. Paste this URL:</span>
          <code className="block mt-1 bg-background border rounded px-3 py-2 select-all">{mcpUrl}</code>
        </div>
        <div><span className="text-muted-foreground">3. Authenticate with your email when prompted</span></div>
        <div>
          <span className="text-muted-foreground">4. Claude can now use </span>
          <code className="text-primary">list_projects</code>, <code className="text-primary">read_doc</code>, <code className="text-primary">get_doc_tree</code>, <code className="text-primary">list_issues</code>
        </div>
      </div>
    </div>
  )
}

function DangerZone({ projectBase, slug, navigate }: {
  projectBase: string; slug: string; navigate: (path: string) => void
}) {
  const deleteMut = useMutation({
    mutationFn: () => apiDelete(`${projectBase}/api/settings`),
    onSuccess: () => navigate('/'),
  })

  return (
    <div className="bg-card rounded-lg border border-destructive/30 p-4">
      <h2 className="text-sm font-semibold text-destructive mb-2">Danger zone</h2>
      <Button
        variant="destructive"
        size="sm"
        onClick={() => { if (confirm(`Delete project ${slug}? This cannot be undone.`)) deleteMut.mutate() }}
        disabled={deleteMut.isPending}
      >
        Delete project
      </Button>
    </div>
  )
}
