/**
 * Shared application shell: compact sidebar navigation + global search +
 * main content area. Routes render via <Outlet />.
 *
 * Information architecture — five conceptual clusters:
 *   DISCOVER   entry points (home, discovery, company index, asset classes)
 *   RESEARCH   analytical terminals (financials, markets, screener, sectors)
 *   MONITOR    ongoing observation surfaces (signals, events, derived links)
 *   OUTPUT     document deliverables (reports, compare)
 *   EVIDENCE   evidence infrastructure (record, coverage & gaps)
 *
 * On narrow viewports the sidebar becomes an off-canvas drawer controlled
 * from the sticky top bar.
 */

import { useCallback, useEffect, useRef, useState } from "react"
import { NavLink, Outlet, useNavigate } from "react-router-dom"
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bookmark,
  Building2,
  Clock,
  Eye,
  FileSearch,
  FileText,
  Filter,
  GitBranch,
  GitCompareArrows,
  Layers,
  Lightbulb,
  LineChart,
  Menu,
  Signal,
  TrendingUp,
  UserRound,
  X,
} from "lucide-react"
import CompanySearch from "./components/CompanySearch"

const NAV_SECTIONS = [
  {
    label: "Discover",
    items: [
      { to: "/", label: "Research Home", icon: Activity, end: true },
      { to: "/discover", label: "Discover", icon: FileSearch },
      { to: "/companies", label: "Companies", icon: Building2 },
    ],
  },
  {
    label: "Research",
    items: [
      { to: "/financial-intelligence", label: "Financial Intelligence", icon: LineChart },
      { to: "/market-intelligence", label: "Markets", icon: Eye },
      { to: "/technical", label: "Technical", icon: TrendingUp },
      { to: "/screener", label: "Screener", icon: Filter },
      { to: "/industries", label: "Industries", icon: BarChart3 },
      { to: "/themes", label: "Themes", icon: Lightbulb },
    ],
  },
  {
    label: "Monitor",
    items: [
      { to: "/timeline", label: "Events", icon: Clock },
      { to: "/signals", label: "Signals", icon: Signal },
      { to: "/cross-domain", label: "Cross-Domain", icon: GitBranch },
      { to: "/profile", label: "My Research", icon: UserRound },
    ],
  },
  {
    label: "Output",
    items: [
      { to: "/reports", label: "Reports", icon: Layers },
      { to: "/professional-report", label: "Professional Report", icon: FileText },
      { to: "/compare", label: "Compare", icon: GitCompareArrows },
    ],
  },
  {
    label: "Evidence Base",
    items: [
      { to: "/evidence", label: "Evidence", icon: FileSearch },
      { to: "/research-gaps", label: "Coverage & Gaps", icon: AlertTriangle },
      { to: "/asset-classes", label: "Asset Classes", icon: Bookmark },
    ],
  },
]

function Sidebar({
  onNavigate,
  closeButtonRef,
  hidden,
}: {
  onNavigate?: () => void
  closeButtonRef?: React.RefObject<HTMLButtonElement | null>
  hidden?: boolean
}) {
  return (
    <aside className="sidebar" inert={hidden || undefined}>
      <div className="brand">
        <span className="brand-mark">Q</span>
        <span>
          <strong>Quant Research</strong>
          <small>EVIDENCE TERMINAL</small>
        </span>
        <button
          type="button"
          ref={closeButtonRef}
          className="sidebar-close"
          onClick={onNavigate}
          aria-label="Close navigation"
        >
          <X size={16} />
        </button>
      </div>
      <nav className="sidebar-nav" aria-label="Primary">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="nav-section">
            <div className="nav-section-label">{section.label}</div>
            {section.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => (isActive ? "nav-active" : "")}
                onClick={onNavigate}
              >
                <item.icon size={15} />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div className="sidebar-footer">
        <span className="live-dot" />
        Evidence-first research
        <br />
        <small>Facts. Evidence. Sources. No judgement.</small>
      </div>
    </aside>
  )
}

function GlobalSearch({
  onToggleNav,
  navOpen,
  navToggleRef,
}: {
  onToggleNav: () => void
  navOpen: boolean
  navToggleRef?: React.RefObject<HTMLButtonElement | null>
}) {
  const navigate = useNavigate()
  const handleSelect = useCallback(
    (symbol: string) => navigate(`/companies/${symbol}`),
    [navigate],
  )
  return (
    <>
      <button
        type="button"
        ref={navToggleRef}
        className="nav-toggle"
        onClick={onToggleNav}
        aria-label="Open navigation"
        aria-expanded={navOpen}
      >
        <Menu size={17} />
      </button>
      <CompanySearch onSelect={handleSelect} />
    </>
  )
}

export default function Layout() {
  const [navOpen, setNavOpen] = useState(false)
  const navToggleRef = useRef<HTMLButtonElement>(null)
  const sidebarCloseRef = useRef<HTMLButtonElement>(null)
  const [mobileNav, setMobileNav] = useState(
    typeof window.matchMedia === "function" &&
      window.matchMedia("(max-width: 900px)").matches,
  )

  // Track the off-canvas breakpoint and close the drawer when the viewport
  // grows past it.
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined
    const desktop = window.matchMedia("(min-width: 901px)")
    const mobile = window.matchMedia("(max-width: 900px)")
    function handleChange() {
      if (desktop.matches) setNavOpen(false)
      setMobileNav(mobile.matches)
    }
    desktop.addEventListener("change", handleChange)
    mobile.addEventListener("change", handleChange)
    return () => {
      desktop.removeEventListener("change", handleChange)
      mobile.removeEventListener("change", handleChange)
    }
  }, [])

  // Off-canvas drawer behaviour on mobile: focus moves into the drawer on
  // open, Escape closes it, and focus returns to the toggle button. The
  // always-visible desktop sidebar is unaffected.
  useEffect(() => {
    if (!mobileNav || !navOpen) return undefined
    const previous = document.activeElement as HTMLElement | null
    sidebarCloseRef.current?.focus()
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setNavOpen(false)
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.removeEventListener("keydown", handleKeyDown)
      previous?.focus?.()
    }
  }, [mobileNav, navOpen])

  const close = useCallback(() => setNavOpen(false), [])

  return (
    <div className={navOpen ? "terminal-shell nav-open" : "terminal-shell"}>
      <div
        className={navOpen ? "sidebar-scrim visible" : "sidebar-scrim"}
        onClick={close}
        aria-hidden
      />
      <Sidebar
        onNavigate={close}
        closeButtonRef={sidebarCloseRef}
        hidden={mobileNav && !navOpen}
      />
      <main className="workspace">
        <div className="global-search-bar">
          <GlobalSearch
            onToggleNav={() => setNavOpen((value) => !value)}
            navOpen={navOpen}
            navToggleRef={navToggleRef}
          />
        </div>
        <div className="research-workspace">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
