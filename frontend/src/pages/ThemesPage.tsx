/**
 * Themes & Technologies page: technology/theme intelligence architecture.
 *
 * Data available from discovery/research:
 * - Which companies have technology exposure (per-company from research)
 * - Technology classification (AI, Cloud, Semiconductors, etc.)
 *
 * Data NOT available (backend required):
 * - Cross-company theme aggregation
 * - Theme-level metrics / KPIs
 * - Theme trend / momentum indicators
 * - Theme regulation landscape
 * - Cross-theme correlation
 *
 * Evidence categories for technology exposure:
 * - ACTUAL_USE: Company has a product/service using this technology
 * - MENTIONED: Company mentions this technology (may not be core business)
 * - ADOPTER: Company uses this technology internally
 * - INFRASTRUCTURE_PROVIDER: Company provides this technology infrastructure
 * - EVIDENCE_TAGGED: Evidence type is classified
 *
 * All sections show:
 * - Data status (available / missing / backend required)
 * - Evidence references
 * - Provenance links
 */

import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Cpu,
  Cloud,
  CircuitBoard,
  Bot,
  Shield,
  Zap,
  CreditCard,
  Factory,
  Activity,
  FileSearch,
  AlertTriangle,
} from "lucide-react"
import { fetchDiscovery } from "../api/client"
import type { DiscoveryItem } from "../api/types"
import { SectionDivider, Tag } from "../components/ui"
import {
  ResearchSection,
  DataStatus,
  UnsupportedData,
  ProvenanceLink,
} from "../components/ResearchPrimitives"

/* ── Theme definitions ──────────────────────────────────────────────── */

interface Theme {
  id: string
  label: string
  icon: React.ReactNode
  description: string
  examples: string[]
  evidenceTypes: string[]
  backendRequired: boolean
}

const THEMES: Theme[] = [
  {
    id: "ai",
    label: "Artificial Intelligence",
    icon: <Cpu size={18} />,
    description: "AI exposure, actual AI use vs mentions, automation, and technology adoption. Evidence-backed technology intelligence distinguishes between companies that have AI products, companies that use AI internally, and companies that merely mention AI.",
    examples: ["Machine learning", "NLP", "Computer vision", "Generative AI", "AI infrastructure"],
    evidenceTypes: ["AI Product", "AI Adoption", "AI Capex", "AI Revenue"],
    backendRequired: true,
  },
  {
    id: "cloud",
    label: "Cloud Computing",
    icon: <Cloud size={18} />,
    description: "Cloud migration, SaaS adoption, infrastructure-as-a-service, and platform services.",
    examples: ["Public cloud", "Hybrid cloud", "SaaS", "PaaS", "Cloud-native"],
    evidenceTypes: ["Cloud Product", "Cloud Infrastructure", "Cloud Adoption"],
    backendRequired: true,
  },
  {
    id: "semiconductors",
    label: "Semiconductors",
    icon: <CircuitBoard size={18} />,
    description: "Chip design, fabrication, supply chain, and demand dynamics.",
    examples: ["Fabless", "Foundry", "EDA", "Advanced packaging", "Edge computing"],
    evidenceTypes: ["Design", "Fabrication", "Packaging", "EDA Tools"],
    backendRequired: true,
  },
  {
    id: "robotics",
    label: "Robotics & Automation",
    icon: <Bot size={18} />,
    description: "Industrial automation, robotics adoption, and process automation.",
    examples: ["Industrial robots", "Collaborative robots", "Process automation", "Warehouse automation"],
    evidenceTypes: ["Robotics Product", "Automation Adoption", "Industrial IoT"],
    backendRequired: true,
  },
  {
    id: "cybersecurity",
    label: "Cybersecurity",
    icon: <Shield size={18} />,
    description: "Security infrastructure, threat landscape, and compliance requirements.",
    examples: ["Network security", "Endpoint security", "Zero trust", "Compliance"],
    evidenceTypes: ["Security Product", "Security Infrastructure", "Compliance"],
    backendRequired: true,
  },
  {
    id: "energy",
    label: "Energy Transition",
    icon: <Zap size={18} />,
    description: "Renewable energy, battery technology, grid modernization, and sustainability.",
    examples: ["Solar", "Wind", "Battery storage", "EV infrastructure", "Green hydrogen"],
    evidenceTypes: ["Renewable Product", "Clean Energy", "Grid Technology"],
    backendRequired: true,
  },
  {
    id: "fintech",
    label: "Digital Payments & Fintech",
    icon: <CreditCard size={18} />,
    description: "Digital payment infrastructure, fintech platforms, and financial innovation.",
    examples: ["UPI", "Digital wallets", "BNPL", "Open banking", "Embedded finance"],
    evidenceTypes: ["Payment Platform", "Fintech Product", "Embedded Finance"],
    backendRequired: true,
  },
  {
    id: "manufacturing",
    label: "Advanced Manufacturing",
    icon: <Factory size={18} />,
    description: "Smart manufacturing, Industry 4.0, additive manufacturing, and supply chain digitization.",
    examples: ["3D printing", "Digital twins", "IoT sensors", "Predictive maintenance"],
    evidenceTypes: ["Smart Manufacturing", "Additive Manufacturing", "IoT Platform"],
    backendRequired: true,
  },
]

/* ── Page component ─────────────────────────────────────────────────── */

export default function ThemesPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [query, setQuery] = useState("")

  useEffect(() => {
    let cancelled = false
    fetchDiscovery()
      .then((res) => {
        if (!cancelled) {
          setItems(res.results)
          setLoading(false)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Discovery unavailable")
          setLoading(false)
        }
      })
    return () => { cancelled = true }
  }, [])

  const filteredThemes = useMemo(() => {
    const q = query.toLowerCase()
    if (!q) return THEMES
    return THEMES.filter(
      (t) =>
        t.label.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q) ||
        t.examples.some((e) => e.toLowerCase().includes(q)),
    )
  }, [query])

  const activeTheme = THEMES.find((t) => t.id === selected)
  const totalCompanies = items.length
  const companiesWithResearch = items.filter((i) => i.research_available).length

  return (
    <div className="page-themes">
      <section className="page-hero">
        <h1>Themes & Technologies</h1>
        <p className="page-subtitle">
          Technology and theme exploration. Company-specific evidence of exposure
          (actual use vs mentions, adoption maturity, business-model impact) is
          available on individual company research pages. No AI scores or rankings.
        </p>
      </section>

      {loading && (
        <div className="loading-state" role="status">
          <Activity className="spin" size={26} />
          <strong>Loading theme data</strong>
          <span>Fetching discovery information...</span>
        </div>
      )}

      {error && (
        <div className="empty-state error" role="alert">
          <FileSearch size={28} />
          <strong>Discovery unavailable</strong>
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && (
        <>
          {/* Summary */}
          <ResearchSection id="theme-coverage" title="Theme Coverage Summary">
            <DataStatus
              availability="available"
              detail={`${filteredThemes.length} themes defined, ${companiesWithResearch} / ${totalCompanies} companies with research available for technology analysis`}
            />
          </ResearchSection>

          {/* Search */}
          <section className="page-search-section">
            <div className="home-search">
              <Cpu size={17} />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter themes by name, description, or technology area..."
                aria-label="Filter themes"
              />
            </div>
          </section>

          {/* Main layout */}
          <div className="themes-layout">
            {/* LEFT: Theme list */}
            <div className="themes-sidebar">
              <div className="panel">
                <div className="panel-head">
                  <h3>Technology Themes</h3>
                  <span>{filteredThemes.length} themes</span>
                </div>
                <div className="theme-list">
                  {filteredThemes.map((theme) => (
                    <button
                      key={theme.id}
                      className={`theme-list-item ${selected === theme.id ? "theme-active" : ""}`}
                      onClick={() => setSelected(selected === theme.id ? null : theme.id)}
                    >
                      {theme.icon}
                      <span>{theme.label}</span>
                      {theme.backendRequired && (
                        <Tag text="Planned" tone="amber" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* RIGHT: Theme detail */}
            <div className="themes-content">
              {activeTheme ? (
                <ThemeDetail theme={activeTheme} onCompanyClick={(sym) => navigate(`/companies/${sym}`)} />
              ) : (
                <div className="panel">
                  <div className="empty-state">
                    <Cpu size={28} />
                    <strong>Select a theme</strong>
                    <p>Choose a technology theme from the list to view its overview.</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Theme intelligence capability note */}
          <div className="theme-architecture-note">
            <SectionDivider label="HOW THEME COVERAGE WORKS TODAY" />
            <div className="architecture-note-content">
              <p>
                Themes are evidence-backed technology classifications: each company's
                exposure is recorded with the type of evidence behind it — actual
                products versus mentions, internal adoption versus external provision.
                The classification lives on each company's research page alongside its
                AI, cloud, semiconductor, automation, cybersecurity, and energy
                transition context.
              </p>
              <p>
                Cross-company theme aggregates — momentum indicators, regulation
                landscapes, market sizing — are not recorded yet, so this page shows
                the tracked universe per theme rather than computed theme metrics.
              </p>
              <UnsupportedData
                feature="Cross-company theme aggregation and theme-level intelligence"
                description="Theme roll-ups are not recorded yet — theme exposure currently lives on each company's research page."
              />
            </div>
          </div>
        </>
      )}
    </div>
  )
}

/* ── Theme Detail ───────────────────────────────────────────────────── */

function ThemeDetail({
  theme,
}: {
  theme: Theme
  onCompanyClick?: (symbol: string) => void
}) {
  return (
    <div className="panel">
      <div className="panel-head">
        <h3>{theme.label}</h3>
        <span>Theme overview</span>
      </div>

      <p className="theme-description">{theme.description}</p>

      <ResearchSection id="theme-areas" title="Key Technology Areas">
        <div className="theme-example-tags">
          {theme.examples.map((ex) => (
            <Tag key={ex} text={ex} tone="slate" />
          ))}
        </div>
      </ResearchSection>

      <ResearchSection id="theme-evidence-types" title="Evidence Types for This Theme">
        <div className="theme-evidence-types">
          {theme.evidenceTypes.map((et) => (
            <Tag key={et} text={et} tone="blue" />
          ))}
        </div>
        <DataStatus
          availability="missing"
          detail="Evidence type classification requires backend technology intelligence endpoint"
        />
      </ResearchSection>

      <ResearchSection id="theme-data-availability" title="Data Availability">
        {theme.backendRequired ? (
          <UnsupportedData
            feature={`${theme.label} company-level exposure data`}
            description="Per-company exposure and maturity records for this theme are not recorded yet."
          />
        ) : (
          <DataStatus
            availability="available"
            detail="Data available from client-side sources"
          />
        )}
      </ResearchSection>

      <ResearchSection id="theme-evidence-note" title="Where to Find Evidence">
        <div className="theme-evidence-note">
          <AlertTriangle size={14} />
          <span>
            Company-specific evidence of exposure to {theme.label.toLowerCase()} (actual use vs
            mentions, adoption maturity, business-model impact) is available on individual
            company research pages under the Technology & Innovation section.
          </span>
        </div>
      </ResearchSection>

      <ResearchSection id="theme-provenance" title="Data Sources & Provenance">
        <ProvenanceLink source="Discovery API" />
        <p className="provenance-note">
          Theme definitions are frontend-curated. Actual technology exposure data
          per company requires the backend technology intelligence endpoint. Each
          company's research page contains the authoritative technology analysis.
        </p>
      </ResearchSection>
    </div>
  )
}
