/**
 * Quant Research Terminal — Evidence-first research & intelligence platform.
 *
 * Presents FACTS + EVIDENCE + SOURCES + DATA + PROVENANCE + POINT-IN-TIME CONTEXT.
 * Never presents rankings, scores, recommendations, or investment judgements.
 *
 * Information architecture:
 *   DISCOVER  → find and enter the research universe
 *   RESEARCH  → deep investigation of companies and domains
 *   SCREEN    → filter, compare, screen
 *   MONITOR   → track changes, watch, alert
 *   OUTPUT    → reports, export, evidence packages
 *   ASSETS    → multi-asset class entry points
 *
 * Pages are route-level code-split (React.lazy).
 */

import { lazy, Suspense } from "react"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { DiscoveryProvider } from "./DiscoveryContext"
import Layout from "./Layout"
import "./App.css"

/* ── DISCOVER ─────────────────────────────────────────────────── */
const DiscoverPage = lazy(() => import("./pages/DiscoverPage"))
const GlobalSearchPage = lazy(() => import("./pages/GlobalSearchPage"))
const CompaniesPage = lazy(() => import("./pages/CompaniesPage"))
const IndustriesPage = lazy(() => import("./pages/IndustriesPage"))
const ThemesPage = lazy(() => import("./pages/ThemesPage"))

/* ── RESEARCH ─────────────────────────────────────────────────── */
const CompanyResearchPage = lazy(() => import("./pages/CompanyResearchPage"))
const FinancialIntelligencePage = lazy(() => import("./pages/FinancialIntelligencePage"))
const MarketIntelligencePage = lazy(() => import("./pages/MarketIntelligencePage"))
const TechnicalPage = lazy(() => import("./pages/TechnicalPage"))
const TimelinePage = lazy(() => import("./pages/TimelinePage"))
const EvidencePage = lazy(() => import("./pages/EvidencePage"))
const ResearchGapsPage = lazy(() => import("./pages/ResearchGapsPage"))

/* ── SCREEN ───────────────────────────────────────────────────── */
const ScreenerPage = lazy(() => import("./pages/ScreenerPage"))
const ComparePage = lazy(() => import("./pages/ComparePage"))
const PeerResearchPage = lazy(() => import("./pages/PeerResearchPage"))

/* ── MONITOR ──────────────────────────────────────────────────── */
const MyResearchPage = lazy(() => import("./pages/MyResearchPage"))
const WatchlistsPage = lazy(() => import("./pages/WatchlistsPage"))
const ResearchChangesPage = lazy(() => import("./pages/ResearchChangesPage"))
const EvidenceAlertsPage = lazy(() => import("./pages/EvidenceAlertsPage"))
const CalendarPage = lazy(() => import("./pages/CalendarPage"))

/* ── OUTPUT ───────────────────────────────────────────────────── */
const ReportsPage = lazy(() => import("./pages/ReportsPage"))
const ProfessionalReportPage = lazy(() => import("./pages/ProfessionalReportPage"))

/* ── ASSET CLASSES ────────────────────────────────────────────── */
const AssetClassesPage = lazy(() => import("./pages/AssetClassesPage"))

/* ── MISC ─────────────────────────────────────────────────────── */
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"))

function RouteFallback() {
  return (
    <div className="route-fallback" role="status">
      <span className="spinner" aria-hidden />
      <span>Loading…</span>
    </div>
  )
}

function Page({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<RouteFallback />}>{children}</Suspense>
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/discover" replace />} />

        {/* ── DISCOVER ─────────────────────────────────────────── */}
        <Route path="/discover" element={<Page><DiscoverPage /></Page>} />
        <Route path="/discover/search" element={<Page><GlobalSearchPage /></Page>} />
        <Route path="/companies" element={<Page><CompaniesPage /></Page>} />
        <Route path="/companies/:symbol" element={<Page><CompanyResearchPage /></Page>} />
        <Route path="/industries" element={<Page><IndustriesPage /></Page>} />
        <Route path="/themes" element={<Page><ThemesPage /></Page>} />

        {/* ── RESEARCH ─────────────────────────────────────────── */}
        <Route path="/financial-intelligence" element={<Page><FinancialIntelligencePage /></Page>} />
        <Route path="/market-intelligence" element={<Page><MarketIntelligencePage /></Page>} />
        <Route path="/technical" element={<Page><TechnicalPage /></Page>} />
        <Route path="/events" element={<Page><TimelinePage /></Page>} />
        <Route path="/evidence" element={<Page><EvidencePage /></Page>} />
        <Route path="/research-gaps" element={<Page><ResearchGapsPage /></Page>} />

        {/* ── SCREEN ───────────────────────────────────────────── */}
        <Route path="/screener" element={<Page><ScreenerPage /></Page>} />
        <Route path="/compare" element={<Page><ComparePage /></Page>} />
        <Route path="/peer-research" element={<Page><PeerResearchPage /></Page>} />

        {/* ── MONITOR ──────────────────────────────────────────── */}
        <Route path="/my-research" element={<Page><MyResearchPage /></Page>} />
        <Route path="/watchlists" element={<Page><WatchlistsPage /></Page>} />
        <Route path="/research-changes" element={<Page><ResearchChangesPage /></Page>} />
        <Route path="/evidence-alerts" element={<Page><EvidenceAlertsPage /></Page>} />
        <Route path="/calendar" element={<Page><CalendarPage /></Page>} />

        {/* ── OUTPUT ───────────────────────────────────────────── */}
        <Route path="/reports" element={<Page><ReportsPage /></Page>} />
        <Route path="/professional-report" element={<Page><ProfessionalReportPage /></Page>} />
        <Route path="/evidence-package" element={<Page><EvidencePage /></Page>} />

        {/* ── ASSET CLASSES ────────────────────────────────────── */}
        <Route path="/asset-classes" element={<Page><AssetClassesPage /></Page>} />
        <Route path="/asset-classes/:classId" element={<Page><AssetClassesPage /></Page>} />

        {/* ── Legacy redirects (backward compat) ───────────────── */}
        <Route path="/timeline" element={<Navigate to="/events" replace />} />
        <Route path="/profile" element={<Navigate to="/my-research" replace />} />
        <Route path="/research-home" element={<Navigate to="/discover" replace />} />

        {/* ── 404 ──────────────────────────────────────────────── */}
        <Route path="*" element={<Page><NotFoundPage /></Page>} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <DiscoveryProvider>
        <AppRoutes />
      </DiscoveryProvider>
    </BrowserRouter>
  )
}
