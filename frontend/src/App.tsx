import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { useAuth } from '@/hooks/use-auth'
import { AppSidebar } from '@/components/AppSidebar'
import WelcomePage from '@/pages/WelcomePage'
import DashboardPage from '@/pages/DashboardPage'
import NewProjectPage from '@/pages/NewProjectPage'
import AdminPage from '@/pages/AdminPage'
import DocPage from '@/pages/DocPage'
import IssuesPage from '@/pages/IssuesPage'
import SettingsPage from '@/pages/SettingsPage'

export default function App() {
  const { isLoading, isAuthenticated } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-muted-foreground text-sm">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <WelcomePage />
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/40 z-40 md:hidden" onClick={() => setSidebarOpen(false)} />
      )}
      <AppSidebar mobileOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <main className="flex-1 overflow-y-auto min-w-0">
        {/* Mobile header */}
        <div className="sticky top-0 z-30 flex items-center gap-3 px-4 py-3 bg-background border-b border-border md:hidden">
          <button onClick={() => setSidebarOpen(true)} className="p-1 -ml-1" aria-label="Open menu">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h18M3 6h18M3 18h18" />
            </svg>
          </button>
          <span className="text-sm font-bold tracking-tight font-serif">Memento</span>
        </div>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/new" element={<NewProjectPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/:project/settings" element={<SettingsPage />} />
          <Route path="/:project/issues" element={<IssuesPage />} />
          <Route path="/:project/*" element={<DocPage />} />
          <Route path="/:project" element={<DocPage />} />
        </Routes>
      </main>
    </div>
  )
}
