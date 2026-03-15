import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/lib/api'

interface Project {
  slug: string
  title: string
  color: string
  repo_full_name: string
  is_owner: boolean
}

export default function DashboardPage() {
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiGet<Project[]>('/api/projects'),
  })

  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-8 pt-6 sm:pt-10 pb-20">
      <h1 className="text-2xl font-bold tracking-tight font-serif mb-6" style={{ letterSpacing: '-0.02em' }}>
        Projects
      </h1>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : projects.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-muted-foreground mb-2">No projects yet</p>
          <Link to="/new" className="text-sm text-primary hover:underline">Create your first project</Link>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map(p => (
            <Link
              key={p.slug}
              to={`/${p.slug}/`}
              className="group block rounded-xl border border-border/50 bg-card/50 p-5 hover:border-border transition-all"
            >
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: p.color }} />
                <span className="text-xs text-muted-foreground font-mono">{p.repo_full_name}</span>
              </div>
              <div className="font-semibold text-base tracking-tight group-hover:text-foreground transition-colors">
                {p.title}
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  )
}
