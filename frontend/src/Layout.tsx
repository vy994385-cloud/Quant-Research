/**
 * Application shell — one coherent evidence-first research terminal.
 *
 * Structure:
 *   TOP COMMAND BAR   global search · contextual actions
 *   LEFT PRIMARY NAV  workflow-aligned research terminal navigation
 *                     DISCOVER · RESEARCH · SCREEN · MONITOR · OUTPUT · ASSETS
 *   MAIN CANVAS       the routed research workspace
 *
 * Navigation expresses the user workflow:
 *   DISCOVER  → find and enter the research universe
 *   RESEARCH  → deep investigation of companies and domains
 *   SCREEN    → filter, compare, screen
 *   MONITOR   → track changes, watch, alert
 *   OUTPUT    → reports, export, evidence packages
 *   ASSETS    → multi-asset class entry points
 */

import { useCallback, useEffect, useRef, useState } from "react"
import { NavLink, Outlet, useNavigate } from "react-router-dom"
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bookmark,
  Building2,
  ChevronDown,
  Clock,
  Compass,
  Eye,
  FileOutput,
  FileSearch,
  FileText,
  Filter,
  GitBranch,
  GitCompareArrows,
  Home,
  Layers,
  Landmark,
  Lightbulb,
  LineChart,
  Menu,
  Search,
  Shield,
  Signal,
  SlidersHorizontal,
  TrendingUp,
  UserRound,
  X,
} from "lucide-react"
import CompanySearch from "./components/CompanySearch"

interface NavItem {
  to: string
  label: string
  icon: React.ComponentType<{ size?: number }>
  end?: boolean
}

interface NavGroup {
  id: string
  label: string
  icon: React.ComponentType<{ size?: number }>
  items: NavItem[]
}

const NAV_GROUPS: NavGroup[] = [
  {
    id: "discover",
    label: "Discover",
    icon: Compass,
    items: [
      { to: "/discover", label: "Research Home", icon: Home },
      { to: "/companies", label: "Companies", icon: Building2 },
      { to: "/industries", label: "Industries", icon: BarChart3 },
      { to: "/themes", label: "Themes", icon: Lightbulb },
    ],
  },
  {
    id: "research",
    label: "Research",
    icon: Search,
    items: [
      { to: "/financial-intelligence", label: "Financial Intelligence", icon: LineChart },
      { to: "/market-intelligence", label: "Market Intelligence", icon: Eye },
      { to: "/technical", label: "Technical", icon: TrendingUp },
      { to: "/events", label: "Events", icon: Clock },
      { to: "/evidence", label: "Evidence", icon: Shield },
      { to: "/research-gaps", label: "Coverage & Gaps", icon: AlertTriangle },
    ],
  },
  {
    id: "screen",
    label: "Screen",
    icon: SlidersHorizontal,
    items: [
      { to: "/screener", label: "Screener", icon: Filter },
      { to: "/compare", label: "Compare", icon: GitCompareArrows },
    ],
  },
  {
    id: "monitor",
    label: "Monitor",
    icon: Activity,
    items: [
      { to: "/my-research", label: "My Research", icon: UserRound },
      { to: "/signals", label: "Signals", icon: Signal },
      { to: "/cross-domain", label: "Cross-Domain", icon: GitBranch },
    ],
  },
  {
    id: "output",
    label: "Output",
    icon: FileOutput,
    items: [
      { to: "/reports", label: "Reports", icon: Layers },
      { to: "/professional-report", label: "Professional Report", icon: FileText },
      { to: "/evidence-package", label: "Evidence Package", icon: FileSearch },
    ],
  },
  {
    id: "assets",
    label: "Asset Classes",
    icon: Landmark,
    items: [
      { to: "/asset-classes", label: "Asset Classes", icon: Bookmark },
    ],
  },
]

const COLLAPSED_KEY = "qrt.nav.collapsed.v1"

function readCollapsed(): string[] {
  try {
    const raw = localStorage.getItem(COLLAPSED_KEY)
    const parsed: unknown = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed)
      ? parsed.filter((entry): entry is string => typeof entry === "string")
      : []
  } catch {
    return []
  }
}

function SideNav({
  collapsed,
  onToggleGroup,
  onNavigate,
  closeButtonRef,
  hidden,
}: {
  collapsed: string[]
  onToggleGroup: (id: string) => void
  onNavigate?: () => void
  closeButtonRef?: React.RefObject<HTMLButtonElement | null>
  hidden?: boolean
}) {
  return (
    <aside className="side-nav" inert={hidden || undefined}>
      <div className="brand">
        <span className="brand-mark">QR</span>
        <span className="brand-text">
          <strong>Quant Research</strong>
          <small>EVIDENCE TERMINAL</small>
        </span>
        <button
          type="button"
          ref={closeButtonRef}
          className="side-nav-close"
          onClick={onNavigate}
          aria-label="Close navigation"
        >
          <X size={16} />
        </button>
      </div>

      <nav className="nav-workflow" aria-label="Primary">
        {NAV_GROUPS.map((group) => {
          const isCollapsed = collapsed.includes(group.id)
          return (
            <section key={group.id} className="nav-group">
              <button
                type="button"
                className="nav-group-head"
                onClick={() => onToggleGroup(group.id)}
                aria-expanded={!isCollapsed}
                aria-controls={`nav-group-${group.id}`}
              >
                <group.icon size={14} />
                <span>{group.label}</span>
                <ChevronDown
                  size={13}
                  className={isCollapsed ? "nav-group-chevron collapsed" : "nav-group-chevron"}
                  aria-hidden
                />
              </button>
              {!isCollapsed && (
                <ul id={`nav-group-${group.id}`} className="nav-group-items">
                  {group.items.map((item) => (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        end={item.end}
                        className={({ isActive }) => (isActive ? "nav-item nav-active" : "nav-item")}
                        onClick={onNavigate}
                      >
                        <item.icon size={14} />
                        <span>{item.label}</span>
                      </NavLink>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )
        })}
      </nav>

      <div className="side-nav-footer">
        <p className="side-nav-principle">
          <span className="live-dot" /> Evidence · Sources · Provenance
        </p>
      </div>
    </aside>
  )
}

export default function Layout() {
  const navigate = useNavigate()
  const [navOpen, setNavOpen] = useState(false)
  const [collapsed, setCollapsed] = useState<string[]>(readCollapsed)
  const [mobileNav, setMobileNav] = useState(
    typeof window.matchMedia === "function" &&
      window.matchMedia("(max-width: 900px)").matches,
  )
  const navToggleRef = useRef<HTMLButtonElement>(null)
  const sidebarCloseRef = useRef<HTMLButtonElement>(null)

  // Track the off-canvas breakpoint; close the drawer when the viewport
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

  // Off-canvas drawer behaviour on mobile.
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

  const toggleGroup = useCallback((id: string) => {
    setCollapsed((prev) => {
      const next = prev.includes(id)
        ? prev.filter((entry) => entry !== id)
        : [...prev, id]
      try {
        localStorage.setItem(COLLAPSED_KEY, JSON.stringify(next))
      } catch {
        // Storage unavailable: collapse state stays in-session only.
      }
      return next
    })
  }, [])

  const handleSelect = useCallback(
    (symbol: string) => navigate(`/companies/${encodeURIComponent(symbol)}`),
    [navigate],
  )

  return (
    <div className={navOpen ? "terminal-shell nav-open" : "terminal-shell"}>
      <div
        className={navOpen ? "sidebar-scrim visible" : "sidebar-scrim"}
        onClick={close}
        aria-hidden
      />
      <SideNav
        collapsed={collapsed}
        onToggleGroup={toggleGroup}
        onNavigate={close}
        closeButtonRef={sidebarCloseRef}
        hidden={mobileNav && !navOpen}
      />
      <div className="main-column">
        <header className="cmd-bar">
          {mobileNav && (
            <button
              type="button"
              ref={navToggleRef}
              className="cmd-menu"
              onClick={() => setNavOpen((value) => !value)}
              aria-label="Open navigation"
              aria-expanded={navOpen}
            >
              <Menu size={17} />
            </button>
          )}
          <CompanySearch onSelect={handleSelect} />
        </header>
        <main className="research-workspace">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
