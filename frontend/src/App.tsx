import { useState, useEffect, useCallback } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/use-auth'
import { AppSidebar } from '@/components/AppSidebar'
import { SearchModal } from '@/components/SearchModal'
import WelcomePage from '@/pages/WelcomePage'
import DashboardPage from '@/pages/DashboardPage'
import NewProjectPage from '@/pages/NewProjectPage'
import AdminPage from '@/pages/AdminPage'
import DocPage from '@/pages/DocPage'
import IssuesPage from '@/pages/IssuesPage'
import SettingsPage from '@/pages/SettingsPage'
import HelpPage from '@/pages/HelpPage'
import { LegalNoticePage, PrivacyPage, TermsPage } from '@/pages/LegalPage'

export default function App() {
  const { isLoading, isAuthenticated } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)

  // Global Cmd+K / Ctrl+K shortcut
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setSearchOpen(prev => !prev)
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [])

  const closeSearch = useCallback(() => setSearchOpen(false), [])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-muted-foreground text-sm">Loading...</div>
      </div>
    )
  }

  const { pathname } = useLocation()

  const publicPages: Record<string, React.ReactNode> = {
    '/help': <HelpPage />,
    '/legal': <LegalNoticePage />,
    '/privacy': <PrivacyPage />,
    '/terms': <TermsPage />,
  }
  if (publicPages[pathname]) return <>{publicPages[pathname]}</>

  if (!isAuthenticated) {
    return <WelcomePage />
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/40 z-40 md:hidden" onClick={() => setSidebarOpen(false)} />
      )}
      <AppSidebar mobileOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} onSearchOpen={() => setSearchOpen(true)} />
      <main className="flex-1 overflow-y-auto min-w-0">
        {/* Mobile header */}
        <div className="sticky top-0 z-30 flex items-center gap-3 px-4 py-3 bg-background border-b border-border md:hidden">
          <button onClick={() => setSidebarOpen(true)} className="p-1 -ml-1" aria-label="Open menu">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h18M3 6h18M3 18h18" />
            </svg>
          </button>
          <span className="text-sm font-bold tracking-tight font-serif flex-1">Mento</span>
          <button onClick={() => setSearchOpen(true)} className="p-1" aria-label="Search">
            <svg className="w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </button>
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

      {/* Search modal */}
      <SearchModal open={searchOpen} onClose={closeSearch} />
    </div>
  )
}
