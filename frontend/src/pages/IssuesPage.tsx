import { useParams } from 'react-router-dom'
import { IssuesTable } from '@/components/IssuesTable'

export default function IssuesPage() {
  const { project } = useParams()
  return (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 pt-6 pb-20">
      <h1 className="text-lg font-semibold mb-4">Issues</h1>
      <IssuesTable projectBase={`/${project}`} />
    </main>
  )
}
