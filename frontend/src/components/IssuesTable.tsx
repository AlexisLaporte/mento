import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/lib/api'
import { Button } from '@/components/ui/button'

interface Issue {
  number: number
  title: string
  state: string
  labels: { name: string; color: string }[]
  assignee: string | null
  created_at: string
  updated_at: string
  comments: number
  url: string
  milestone: string | null
}

interface LabelOption { name: string; color: string }
interface MilestoneOption { number: number; title: string }

export function IssuesTable({ projectBase }: { projectBase: string }) {
  const [state, setState] = useState('open')
  const [label, setLabel] = useState('')
  const [milestone, setMilestone] = useState('')

  const params = new URLSearchParams({ state })
  if (label) params.set('labels', label)
  if (milestone) params.set('milestone', milestone)

  const { data: issues, isLoading, refetch } = useQuery({
    queryKey: ['issues', projectBase, state, label, milestone],
    queryFn: () => apiGet<Issue[]>(`${projectBase}/api/issues?${params}`),
  })

  const { data: labels = [] } = useQuery({
    queryKey: ['labels', projectBase],
    queryFn: () => apiGet<LabelOption[]>(`${projectBase}/api/labels`),
  })

  const { data: milestones = [] } = useQuery({
    queryKey: ['milestones', projectBase],
    queryFn: () => apiGet<MilestoneOption[]>(`${projectBase}/api/milestones`),
  })

  return (
    <div className="p-4">
      {/* Filters */}
      <div className="flex gap-2 mb-4 flex-wrap items-center">
        <select value={state} onChange={e => setState(e.target.value)} className="text-sm border rounded px-2 py-1">
          <option value="open">Open</option>
          <option value="closed">Closed</option>
          <option value="all">All</option>
        </select>
        <select value={label} onChange={e => setLabel(e.target.value)} className="text-sm border rounded px-2 py-1">
          <option value="">All labels</option>
          {labels.map(l => <option key={l.name} value={l.name}>{l.name}</option>)}
        </select>
        <select value={milestone} onChange={e => setMilestone(e.target.value)} className="text-sm border rounded px-2 py-1">
          <option value="">All milestones</option>
          {milestones.map(m => <option key={m.number} value={String(m.number)}>{m.title}</option>)}
        </select>
        <Button variant="ghost" size="sm" onClick={() => refetch()}>Refresh</Button>
      </div>

      {/* Content */}
      {isLoading ? (
        <p className="text-sm text-muted-foreground text-center py-8">Loading...</p>
      ) : !issues?.length ? (
        <p className="text-sm text-muted-foreground text-center py-8">No issues found.</p>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-muted-foreground uppercase border-b">
                <tr>
                  <th className="text-left py-2 px-2 w-16">#</th>
                  <th className="text-left py-2 px-2">Title</th>
                  <th className="text-left py-2 px-2 w-32">Labels</th>
                  <th className="text-left py-2 px-2 w-24">Assignee</th>
                  <th className="text-left py-2 px-2 w-28">Updated</th>
                </tr>
              </thead>
              <tbody>
                {issues.map(issue => (
                  <tr
                    key={issue.number}
                    onClick={() => window.open(issue.url, '_blank')}
                    className="border-b hover:bg-accent cursor-pointer"
                  >
                    <td className="py-2 px-2 text-muted-foreground">
                      <span className={`inline-block w-2 h-2 rounded-full mr-1.5 ${issue.state === 'open' ? 'bg-green-500' : 'bg-purple-500'}`} />
                      {issue.number}
                    </td>
                    <td className="py-2 px-2 font-medium">
                      {issue.title}
                      {issue.comments > 0 && <span className="text-xs text-muted-foreground ml-1">{issue.comments}</span>}
                    </td>
                    <td className="py-2 px-2">
                      {issue.labels.map(l => (
                        <span
                          key={l.name}
                          className="inline-block text-xs px-1.5 py-0.5 rounded-full mr-1"
                          style={{ background: `#${l.color}20`, color: `#${l.color}`, border: `1px solid #${l.color}40` }}
                        >
                          {l.name}
                        </span>
                      ))}
                    </td>
                    <td className="py-2 px-2 text-muted-foreground">{issue.assignee || ''}</td>
                    <td className="py-2 px-2 text-muted-foreground">
                      {new Date(issue.updated_at).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile card list */}
          <div className="md:hidden space-y-2">
            {issues.map(issue => (
              <div
                key={issue.number}
                onClick={() => window.open(issue.url, '_blank')}
                className="border rounded-lg p-3 hover:bg-accent cursor-pointer"
              >
                <div className="flex items-start gap-2">
                  <span className={`mt-1.5 inline-block w-2 h-2 rounded-full shrink-0 ${issue.state === 'open' ? 'bg-green-500' : 'bg-purple-500'}`} />
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-sm">{issue.title}</div>
                    <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                      <span>#{issue.number}</span>
                      {issue.assignee && <span>{issue.assignee}</span>}
                      <span>{new Date(issue.updated_at).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}</span>
                      {issue.comments > 0 && <span>{issue.comments} comments</span>}
                    </div>
                    {issue.labels.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {issue.labels.map(l => (
                          <span
                            key={l.name}
                            className="inline-block text-xs px-1.5 py-0.5 rounded-full"
                            style={{ background: `#${l.color}20`, color: `#${l.color}`, border: `1px solid #${l.color}40` }}
                          >
                            {l.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
