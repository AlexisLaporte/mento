import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiDelete } from '@/lib/api'
import { useAuth } from '@/hooks/use-auth'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

interface AdminProject {
  slug: string
  title: string
  color: string
  repo_full_name: string
  owner_email: string
}

export default function AdminPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['admin-projects'],
    queryFn: () => apiGet<AdminProject[]>('/api/admin/projects'),
    enabled: !!user?.is_super_admin,
  })

  const deleteMut = useMutation({
    mutationFn: (slug: string) => apiDelete(`/api/admin/projects/${slug}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-projects'] }),
  })

  if (!user?.is_super_admin) {
    return <p className="text-center py-20 text-muted-foreground">Access denied</p>
  }

  return (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 pt-6 pb-20">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-lg font-semibold">All Projects</h1>
        <div className="flex gap-3">
          <Link to="/new"><Button>+ New project</Button></Link>
          <Link to="/"><Button variant="ghost">Back</Button></Link>
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : (
        <>
          <div className="bg-card rounded-lg border overflow-hidden hidden md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Slug</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>Repo</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {projects.length === 0 ? (
                  <TableRow><TableCell colSpan={5} className="text-center text-muted-foreground py-6">No projects</TableCell></TableRow>
                ) : projects.map(p => (
                  <TableRow key={p.slug}>
                    <TableCell className="font-mono text-sm">{p.slug}</TableCell>
                    <TableCell className="font-semibold" style={{ color: p.color }}>{p.title}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">{p.repo_full_name}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">{p.owner_email}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Link to={`/${p.slug}/settings`} className="text-xs text-primary hover:underline">Settings</Link>
                        <Link to={`/${p.slug}/`} className="text-xs text-muted-foreground hover:underline">View</Link>
                        <button
                          onClick={() => { if (confirm(`Delete ${p.slug}?`)) deleteMut.mutate(p.slug) }}
                          className="text-xs text-destructive hover:underline"
                        >Delete</button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="md:hidden space-y-2">
            {projects.length === 0 ? (
              <p className="text-center text-muted-foreground py-6">No projects</p>
            ) : projects.map(p => (
              <div key={p.slug} className="bg-card rounded-lg border p-4">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: p.color }} />
                  <span className="font-semibold" style={{ color: p.color }}>{p.title}</span>
                </div>
                <p className="text-xs font-mono text-muted-foreground mb-1">{p.slug}</p>
                <p className="text-xs text-muted-foreground mb-1">{p.repo_full_name}</p>
                <p className="text-xs text-muted-foreground mb-2">{p.owner_email}</p>
                <div className="flex gap-3">
                  <Link to={`/${p.slug}/settings`} className="text-xs text-primary hover:underline">Settings</Link>
                  <Link to={`/${p.slug}/`} className="text-xs text-muted-foreground hover:underline">View</Link>
                  <button
                    onClick={() => { if (confirm(`Delete ${p.slug}?`)) deleteMut.mutate(p.slug) }}
                    className="text-xs text-destructive hover:underline"
                  >Delete</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </main>
  )
}
