/**
 * Quant Research Terminal — Evidence-first research & intelligence platform.
 *
 * Presents FACTS + EVIDENCE + SOURCES + DATA + PROVENANCE + POINT-IN-TIME CONTEXT.
 * Never presents rankings, scores, recommendations, or investment judgements.
 *
 * Pages are route-level code-split (React.lazy) so the initial bundle carries
 * only the shell + first page; the Layout shell itself stays eager.
 */

import { lazy, Suspense } from "react"
import { BrowserRouter, Route, Routes } from "react-router-dom"
import { DiscoveryProvider } from "./DiscoveryContext"
import Layout from "./Layout"
import "./App.css"

const ResearchHome = lazy(() => import("./pages/ResearchHome"))
const DiscoverPage = lazy(() => import("./pages/DiscoverPage"))
const CompaniesPage = lazy(() => import("./pages/CompaniesPage"))
const CompanyResearchPage = lazy(() => import("./pages/CompanyResearchPage"))
const IndustriesPage = lazy(() => import("./pages/IndustriesPage"))
const ThemesPage = lazy(() => import("./pages/ThemesPage"))
const FinancialIntelligencePage = lazy(() => import("./pages/FinancialIntelligencePage"))
const SignalsPage = lazy(() => import("./pages/SignalsPage"))
const ReportsPage = lazy(() => import("./pages/ReportsPage"))
const ComparePage = lazy(() => import("./pages/ComparePage"))
const EvidencePage = lazy(() => import("./pages/EvidencePage"))
const ProfessionalReportPage = lazy(() => import("./pages/ProfessionalReportPage"))
const MarketIntelligencePage = lazy(() => import("./pages/MarketIntelligencePage"))
const ScreenerPage = lazy(() => import("./pages/ScreenerPage"))
const TimelinePage = lazy(() => import("./pages/TimelinePage"))
const TechnicalPage = lazy(() => import("./pages/TechnicalPage"))
const CrossDomainPage = lazy(() => import("./pages/CrossDomainPage"))
const ResearchGapsPage = lazy(() => import("./pages/ResearchGapsPage"))
const AssetClassesPage = lazy(() => import("./pages/AssetClassesPage"))
const MyResearchPage = lazy(() => import("./pages/MyResearchPage"))
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
        <Route path="/" element={<Page><ResearchHome /></Page>} />
        <Route path="/discover" element={<Page><DiscoverPage /></Page>} />
        <Route path="/companies" element={<Page><CompaniesPage /></Page>} />
        <Route path="/companies/:symbol" element={<Page><CompanyResearchPage /></Page>} />
        <Route path="/timeline" element={<Page><TimelinePage /></Page>} />
        <Route path="/screener" element={<Page><ScreenerPage /></Page>} />
        <Route path="/industries" element={<Page><IndustriesPage /></Page>} />
        <Route path="/themes" element={<Page><ThemesPage /></Page>} />
        <Route path="/financial-intelligence" element={<Page><FinancialIntelligencePage /></Page>} />
        <Route path="/market-intelligence" element={<Page><MarketIntelligencePage /></Page>} />
        <Route path="/signals" element={<Page><SignalsPage /></Page>} />
        <Route path="/technical" element={<Page><TechnicalPage /></Page>} />
        <Route path="/cross-domain" element={<Page><CrossDomainPage /></Page>} />
        <Route path="/research-gaps" element={<Page><ResearchGapsPage /></Page>} />
        <Route path="/asset-classes" element={<Page><AssetClassesPage /></Page>} />
        <Route path="/profile" element={<Page><MyResearchPage /></Page>} />
        <Route path="/reports" element={<Page><ReportsPage /></Page>} />
        <Route path="/compare" element={<Page><ComparePage /></Page>} />
        <Route path="/evidence" element={<Page><EvidencePage /></Page>} />
        <Route path="/professional-report" element={<Page><ProfessionalReportPage /></Page>} />
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
