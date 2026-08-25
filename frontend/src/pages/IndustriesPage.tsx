/**
 * Industry Intelligence page: sector-level intelligence overview.
 *
 * Data available from discovery API:
 * - Sector classification (per company)
 * - Company counts per sector
 * - Research availability per sector
 *
 * Data NOT available (backend required):
 * - Cross-industry aggregation / sector-level metrics
 * - Competitive dynamics between sectors
 * - Industry health / trend indicators
 * - Regulation and compliance overview
 * - Demand drivers, growth drivers
 * - Supply chain analysis
 * - Technology disruption trends per sector
 *
 * All sections show:
 * - Data status (available / missing / backend required)
 * - Evidence backing (research source references)
 * - Provenance links
 */

import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Building2,
  TrendingUp,
  Shield,
  Zap,
  BarChart3,
} from "lucide-react"
import { fetchDiscovery } from "../api/client"
import type { DiscoveryItem } from "../api/types"
import { formatLabel } from "../lib/format"
import { SectionDivider, Tag } from "../components/ui"
import { LoadingState, EmptyState, ErrorState } from "../components/States"
import {
  ResearchSection,
  DataStatus,
  UnsupportedData,
  ProvenanceLink,
} from "../components/ResearchPrimitives"

/* ── Sector metadata ────────────────────────────────────────────────── */

const SECTOR_DESCRIPTIONS: Record<string, { description: string; keyFactors: string[] }> = {
  banking: { description: "Commercial banks, private banks, small finance banks, payment banks, cooperative banks", keyFactors: ["Net Interest Margin (NIM)", "GNPA ratio", "CRAR", "CASA ratio", "Credit growth"] },
  it: { description: "IT services, software products, digital solutions, consulting", keyFactors: ["Revenue growth", "Attrition rate", "Deal pipeline", "Digital revenue share", "AI revenue"] },
  pharma: { description: "Pharmaceutical companies, API manufacturers, CDMO, formulations", keyFactors: ["ANDA filings", "API margins", "US/EU revenue", "Clinical pipeline", "GMP compliance"] },
  auto: { description: "Auto manufacturers, component makers, EV manufacturers, commercial vehicles", keyFactors: ["Volumes", "Market share", "EV transition", "Export growth", "R&D spend"] },
  chemicals: { description: "Specialty chemicals, agrochemicals, petrochemicals, fine chemicals", keyFactors: ["Capacity utilization", "New plant commissioning", "Export share", "R&D pipeline", "Regulatory compliance"] },
  realty: { description: "Real estate developers, REITs, construction-linked companies", keyFactors: ["Pre-sales", "Launch pipeline", "Collections", "Net debt", "Inventory months"] },
  fmcg: { description: "Fast-moving consumer goods, food processing, personal care", keyFactors: ["Volume growth", "Pricing power", "Distribution reach", "Rural penetration", "Premiumization"] },
  metals: { description: "Steel, aluminium, copper, zinc, specialty metals, mining", keyFactors: ["Prices", "Capacity utilization", "Export volumes", "Cost efficiency", "Raw material security"] },
  infrastructure: { description: "Construction, engineering, EPC, roads, railways, power", keyFactors: ["Order book", "Execution pace", "Bid pipeline", "Working capital", "Debt reduction"] },
  power: { description: "Power generation, distribution, transmission, renewable energy", keyFactors: ["Plant Load Factor", "Tariff", "AT&C losses", "Renewable capacity", "Debt profile"] },
  energy: { description: "Oil & gas exploration, refining, marketing, pipelines, LNG", keyFactors: ["Crack spreads", "GRM", "Volume growth", "LNG spot volumes", "Regulatory impact"] },
  telecom: { description: "Telecom operators, tower companies, fiber infrastructure", keyFactors: ["ARPU", "Subscriber churn", "5G rollout", "Data usage", "Network investment"] },
  nbfc: { description: "Non-banking financial companies, HFCs, microfinance, insurance", keyFactors: ["AUM growth", "Net interest margin", "Asset quality", "Cost-to-income", "ROE"] },
  finance: { description: "Mutual funds, stock broking, wealth management, investment banking", keyFactors: ["AUM growth", "Flow trends", "Market share", "Cost-to-income", "Digital adoption"] },
  hospitality: { description: "Hotels, resorts, travel, tourism, quick-service restaurants", keyFactors: ["RevPAR", "Occupancy", "ADR", "New properties", "F&B revenue"] },
  textiles: { description: "Textile manufacturing, garments, home textiles, technical textiles", keyFactors: ["Export orders", "Capacity utilization", "Raw material cost", "New product mix", "Sustainability compliance"] },
  paper: { description: "Paper manufacturing, packaging, specialty papers", keyFactors: ["Capacity utilization", "Realization", "New capacity", "Export volumes", "Sustainability"] },
  telecom_media: { description: "Media, entertainment, broadcasting, digital content, advertising", keyFactors: ["Subscriber base", "Ad revenue", "Content pipeline", "Digital revenue", "Market share"] },
  miscellaneous: { description: "Companies not classified into standard sectors", keyFactors: ["Varies by company"] },
}

const SECTOR_ICONS: Record<string, typeof TrendingUp> = {
  banking: Shield,
  it: Zap,
  pharma: Shield,
  auto: BarChart3,
  chemicals: Zap,
  realty: Building2,
  fmcg: TrendingUp,
  metals: BarChart3,
  infrastructure: Building2,
  power: Zap,
  energy: TrendingUp,
  telecom: Zap,
  nbfc: Shield,
  finance: Shield,
  hospitality: TrendingUp,
  textiles: BarChart3,
  paper: BarChart3,
  telecom_media: TrendingUp,
  miscellaneous: Building2,
}

/* ── Page component ─────────────────────────────────────────────────── */

export default function IndustriesPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedSector, setSelectedSector] = useState<string | null>(null)

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

  const sectorData = useMemo(() => {
    const map = new Map<string, DiscoveryItem[]>()
    for (const item of items) {
      const list = map.get(item.sector) ?? []
      list.push(item)
      map.set(item.sector, list)
    }
    return [...map.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([sector, sectorItems]) => ({
        sector,
        companies: sectorItems,
        researchCount: sectorItems.filter((i) => i.research_available).length,
        totalCompanies: sectorItems.length,
      }))
  }, [items])

  const selectedSectorData = useMemo(() => {
    if (!selectedSector) return null
    const found = sectorData.find((s) => s.sector === selectedSector)
    return found ?? null
  }, [selectedSector, sectorData])

  const totalCompanies = items.length
  const totalWithResearch = items.filter((i) => i.research_available).length

  return (
    <div className="page-industries">
      <section className="page-hero">
        <p className="page-kicker">Discover</p>
        <h1>Industry Intelligence</h1>
        <p className="page-subtitle">
          Sector overview and company distribution. Industry-specific context
          (competitive dynamics, regulation, demand drivers) is researched
          per-company and available on each company research page.
        </p>
      </section>

      {loading && <LoadingState label="Fetching discovery information..." />}

      {error && <ErrorState error={error} />}

      {!loading && !error && (
        <>
          {/* Summary */}
          <div className="industry-summary">
            <ResearchSection id="industry-coverage" title="Industry Coverage Summary">
              <DataStatus
                availability="available"
                detail={`${sectorData.length} sectors, ${totalWithResearch} / ${totalCompanies} companies with research available`}
              />
            </ResearchSection>
          </div>

          {/* Main layout */}
          <div className="industry-layout">
            {/* LEFT: Sector list */}
            <div className="industry-sectors-list">
              {sectorData.map((s) => (
                <button
                  key={s.sector}
                  className={`industry-sector-item ${selectedSector === s.sector ? "active" : ""}`}
                  onClick={() => setSelectedSector(s.sector)}
                >
                  <span className="sector-name">{formatLabel(s.sector)}</span>
                  <span className="sector-count">
                    <Tag text={`${s.totalCompanies}`} tone="slate" />
                  </span>
                </button>
              ))}
            </div>

            {/* RIGHT: Sector detail */}
            <div className="industry-detail">
              {!selectedSector ? (
                <EmptyState
                  icon={BarChart3}
                  title="Select a sector"
                  description="Click a sector on the left to view details. Each sector shows the companies it covers and links to their research pages."
                />
              ) : selectedSectorData ? (
                <SectorDetail sector={selectedSectorData} onCompanyClick={(sym) => navigate(`/companies/${sym}`)} />
              ) : null}
            </div>
          </div>

          {/* Industry intelligence capability note */}
          <div className="industry-architecture-note">
            <SectionDivider label="How industry coverage works" />
            <div className="architecture-note-content">
              <p>
                Sectors here come from the discovery record: they group the tracked
                companies and show how much research exists in each one. Sector-level
                metrics — industry KPIs, cross-company competitive dynamics, regulatory
                landscapes — are not recorded yet, so this page does not pretend to
                compute them.
              </p>
              <p>
                What does exist is per-company industry context: each company's
                research page covers its competitive dynamics, demand drivers,
                technology disruption, regulatory landscape, and AI relevance as part
                of the recorded analysis.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

/* ── Sector Detail ──────────────────────────────────────────────────── */

function SectorDetail({
  sector,
  onCompanyClick,
}: {
  sector: {
    sector: string
    companies: DiscoveryItem[]
    researchCount: number
    totalCompanies: number
  }
  onCompanyClick: (symbol: string) => void
}) {
  const meta = SECTOR_DESCRIPTIONS[sector.sector]
  const IconComponent = SECTOR_ICONS[sector.sector] ?? Building2

  return (
    <div className="sector-detail">
      <div className="sector-detail-head">
        <IconComponent size={18} />
        <div>
          <h2>{formatLabel(sector.sector)}</h2>
          <p>{meta?.description ?? "Sector classification"}</p>
        </div>
      </div>

      <ResearchSection id="sector-coverage" title="Coverage">
        <div className="sector-coverage-stats">
          <div className="sector-stat">
            <span className="sector-stat-value">{sector.totalCompanies}</span>
            <span className="sector-stat-label">Total companies</span>
          </div>
          <div className="sector-stat">
            <span className="sector-stat-value">{sector.researchCount}</span>
            <span className="sector-stat-label">With research</span>
          </div>
          <div className="sector-stat">
            <span className="sector-stat-value">{sector.totalCompanies - sector.researchCount}</span>
            <span className="sector-stat-label">No research</span>
          </div>
        </div>
      </ResearchSection>

      {meta?.keyFactors && (
        <ResearchSection id="sector-key-factors" title="Key Factors (Research Framework)">
          <div className="sector-key-factors">
            {meta.keyFactors.map((factor) => (
              <Tag key={factor} text={factor} tone="blue" />
            ))}
          </div>
          <DataStatus
            availability="missing"
            detail="Key factors shown are the research framework; actual metrics and values are not yet available"
          />
        </ResearchSection>
      )}

      <ResearchSection id="sector-companies" title="Companies in this Sector">
        <div className="sector-companies-grid">
          {sector.companies.map((item) => (
            <button
              key={item.symbol}
              className="sector-company-card"
              onClick={() => onCompanyClick(item.symbol)}
            >
              <span className="company-symbol">{item.symbol}</span>
              <span className="company-name">{item.company_name ?? item.symbol}</span>
              <span className="company-research-status">
                {item.research_available ? (
                  <Tag text="Research available" tone="green" />
                ) : (
                  <Tag text="No research yet" tone="slate" />
                )}
              </span>
            </button>
          ))}
        </div>
      </ResearchSection>

      <ResearchSection id="sector-context" title="Industry Context">
        <UnsupportedData
          feature="Sector-level competitive dynamics and industry context"
          description="Cross-company sector analysis is not recorded yet — per-company industry context is available on each research page."
        />
        <p className="industry-context-note">
          For industry-specific context, visit each company's research page
          where competitive dynamics, technology disruption, regulatory landscape,
          and industry demand drivers are researched as part of the company analysis.
        </p>
      </ResearchSection>

      <ResearchSection id="sector-provenance" title="Data Sources & Provenance">
        <ProvenanceLink source="Discovery API" />
        <p className="provenance-note">
          Sector classification follows the tracked company universe. The key
          factors framework is static and does not reflect actual company
          metrics. Research availability indicates whether a company has been
          analyzed, not industry-level data completeness.
        </p>
      </ResearchSection>
    </div>
  )
}
