/**
 * ASSET CLASSES — multi-asset workspaces (ETF · Mutual Funds · IPO · F&O).
 *
 * The current data contract covers listed equities only. These contextual
 * workspaces render the same research design system (overview → metrics →
 * history → events → evidence → coverage → sources) but every section is an
 * honest capability state until the backend exposes these datasets.
 * No fields are fabricated and no placeholder data is shown.
 */

import { useState } from "react"
import { Link } from "react-router-dom"
import { BarChart3, Building2, FileSearch, Landmark, LineChart, PieChart, ScrollText } from "lucide-react"
import { PanelHead, SectionDivider } from "../components/ui"

type AssetClass = "etf" | "mf" | "ipo" | "fno"

const TABS: Array<{ value: AssetClass; label: string; blurb: string }> = [
  { value: "etf", label: "ETF", blurb: "Exchange-traded funds" },
  { value: "mf", label: "Mutual Funds", blurb: "Managed fund schemes" },
  { value: "ipo", label: "IPO", blurb: "Primary-market listings" },
  { value: "fno", label: "F&O", blurb: "Futures & options" },
]

const WORKSPACE_SECTIONS = [
  { title: "Overview", detail: "Instrument identity, category and research context" },
  { title: "Metrics", detail: "Reported figures and derived measures per period" },
  { title: "History", detail: "Point-in-time record of reported history" },
  { title: "Events", detail: "Dated developments with verification and source" },
  { title: "Evidence", detail: "Every claim with direction and provenance" },
  { title: "Coverage", detail: "Available, limited, missing, stale and conflicting data" },
  { title: "Sources", detail: "Source lineage and point-in-time methodology" },
]

function CapabilityPanel({ asset }: { asset: AssetClass }) {
  const tab = TABS.find((t) => t.value === asset)!
  return (
    <section className="capability-panel">
      <div className="panel-head">
        <div>
          <h3>{tab.label}</h3>
          <span>{tab.blurb}</span>
        </div>
        <span className="status-badge slate">
          <span className="status-badge-dot" />
          Not yet covered by recorded data
        </span>
      </div>

      <p className="capability-note">
        This workspace is designed but not yet populated: no ETF, mutual-fund,
        IPO or derivatives dataset is exposed by the research API today. When
        the research API adds these datasets, this page renders the same
        sections used for equities — nothing about the presentation changes.
      </p>

      <div className="capability-sections">
        {WORKSPACE_SECTIONS.map((section) => (
          <div key={section.title} className="capability-row">
            <strong>{section.title}</strong>
            <span>{section.detail}</span>
            <em>Awaiting dataset</em>
          </div>
        ))}
      </div>
    </section>
  )
}

export default function AssetClassesPage() {
  const [tab, setTab] = useState<AssetClass>("etf")

  return (
    <div className="page-asset-classes">
      <section className="page-hero">
        <h1>Asset Classes</h1>
        <p className="page-subtitle">
          Dedicated research workspaces beyond single equities. Coverage today is
          listed equities; each additional class below activates as soon as its
          dataset enters the research contract — availability is stated plainly,
          never simulated.
        </p>
      </section>

      <section className="asset-available" aria-label="Available coverage">
        <div className="asset-available-card">
          <Building2 size={18} aria-hidden />
          <div>
            <strong>Listed equities</strong>
            <span>Fully covered — company workspaces, financials, events, evidence and coverage.</span>
          </div>
          <Link className="refresh-button" to="/companies">
            Open companies
          </Link>
        </div>
      </section>

      <SectionDivider label="ADDITIONAL ASSET CLASSES" />

      <div className="filter-chips" role="group" aria-label="Select asset class">
        {TABS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={option.value === tab ? "filter-chip active" : "filter-chip"}
            onClick={() => setTab(option.value)}
            aria-pressed={option.value === tab}
          >
            {option.label}
          </button>
        ))}
      </div>

      <CapabilityPanel asset={tab} />

      <section className="asset-cross-links panel" aria-label="Related research surfaces">
        <PanelHead
          title="Where related evidence lives today"
          subtitle="Equity-side surfaces that already carry adjacent context"
        />
        <ul className="asset-links">
          <li>
            <LineChart size={15} aria-hidden />
            <Link to="/financial-intelligence">Financial Intelligence</Link>
            <span>Cross-company financial observations from reported filings.</span>
          </li>
          <li>
            <PieChart size={15} aria-hidden />
            <Link to="/industries">Industries</Link>
            <span>Sector coverage and company membership.</span>
          </li>
          <li>
            <ScrollText size={15} aria-hidden />
            <Link to="/timeline">Events</Link>
            <span>Corporate actions and disclosures across the universe.</span>
          </li>
          <li>
            <Landmark size={15} aria-hidden />
            <Link to="/screener">Screener</Link>
            <span>Filter the tracked universe by recorded attributes.</span>
          </li>
          <li>
            <FileSearch size={15} aria-hidden />
            <Link to="/evidence">Evidence</Link>
            <span>Lineage explorer over every recorded claim.</span>
          </li>
          <li>
            <BarChart3 size={15} aria-hidden />
            <Link to="/research-gaps">Coverage &amp; Gaps</Link>
            <span>What is available, limited or missing right now.</span>
          </li>
        </ul>
      </section>
    </div>
  )
}
