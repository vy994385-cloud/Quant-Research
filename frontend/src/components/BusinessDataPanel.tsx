/**
 * BUSINESS — operating-context section of the company workspace.
 *
 * Renders only populated intelligence areas as observation lists;
 * unpopulated areas collapse to a single compact "Limited coverage" line.
 * Market intelligence lives in the Market tab — no duplication here.
 */

import { useMemo } from "react"
import type { CompanyResearch } from "../api/types"
import type { Intelligence, IntelligenceSection } from "../api/types"
import { formatLabel, humanizeNarrative } from "../lib/format"
import { EmptyCopy, PanelHead, Tag } from "./ui"

type SectionKey = Exclude<keyof Intelligence, "unknown_missing">

interface AreaSpec {
  key: SectionKey
  title: string
  description: string
}

/**
 * Business-quality observations repeat the same metric label once per period
 * ("Revenue reported: 8,77,835 Cr" × 4). Consecutive repeats condense into a
 * single chronological series so the panel stops restating the financial
 * table line by line. Non-repeating observations pass through untouched.
 */
function condenseSeries(observations: string[]): string[] {
  interface Group {
    label: string
    values: string[]
    numeric: boolean
  }
  const groups = new Map<string, Group>()
  const ordered: Array<{ key: string | null; text: string }> = []

  for (const observation of observations) {
    const humanized = humanizeNarrative(observation)
    const match = /^([^:]{3,60}):\s*(.+)$/.exec(humanized)
    const isNumericValue = match !== null && /\d/.test(match[2]) && /^[₹$]|[\d(]/.test(match[2])
    if (match && isNumericValue) {
      const label = match[1]
      if (!groups.has(label)) {
        groups.set(label, { label, values: [], numeric: true })
        ordered.push({ key: label, text: "" })
      }
      groups.get(label)!.values.push(match[2].trim())
    } else {
      ordered.push({ key: null, text: humanized })
    }
  }

  return ordered.map(({ key, text }) => {
    if (key === null) return text
    const group = groups.get(key)!
    if (group.values.length < 2) {
      return `${group.label}: ${group.values[0]}`
    }
    // Chronological series; the arrow chain keeps every recorded value while
    // removing the per-period repetition.
    const latest = group.values[group.values.length - 1]
    const first = group.values[0]
    let summary = group.values.join(" → ")
    // Very long chains collapse to first → latest with an explicit count.
    if (summary.length > 160) {
      summary = `${first} → ${latest} (${group.values.length} periods)`
    }
    return `${group.label}: ${summary}`
  })
}

const AREAS: AreaSpec[] = [
  {
    key: "business_quality",
    title: "Business quality",
    description: "How the business is observed to operate and compound",
  },
  {
    key: "competitive_position",
    title: "Competitive position",
    description: "Recorded competitive strengths and pressures",
  },
  {
    key: "customer_intelligence",
    title: "Customers",
    description: "Customer concentration, demand and contract evidence",
  },
  {
    key: "management_intelligence",
    title: "Management",
    description: "Execution and governance observations from the record",
  },
  {
    key: "capital_allocation",
    title: "Capital allocation",
    description: "Observed allocation choices: investment, returns, balance sheet",
  },
]

function AreaBlock({ spec, section }: { spec: AreaSpec; section: IntelligenceSection | null }) {
  const supported = Boolean(section && section.observations.length > 0)
  const condensed = useMemo(
    () => (supported ? condenseSeries(section!.observations) : []),
    [section, supported],
  )
  return (
    <article className={supported ? "intel-block supported" : "intel-block"}>
      <header className="intel-block-head">
        <h4>{spec.title}</h4>
        <span className="intel-block-desc">{spec.description}</span>
        {section && supported && (
          <Tag text={formatLabel(section.status)} tone={section.status === "SUPPORTED" ? "green" : "amber"} />
        )}
      </header>
      {supported ? (
        <ul className="intel-observations">
          {condensed.map((observation) => (
            <li key={observation}>{observation}</li>
          ))}
        </ul>
      ) : (
        <p className="limited-note">Limited coverage — no evidence-backed observations recorded for this area yet.</p>
      )}
    </article>
  )
}

export default function BusinessDataPanel({ data }: { data: CompanyResearch }) {
  const name = data.company.company_name ?? data.company.symbol
  const anySupported = AREAS.some((area) => {
    const section = data.intelligence[area.key]
    return Boolean(section && section.observations.length > 0)
  })

  return (
    <div className="section-anchor" id="business-data">
      <PanelHead
        title="Business"
        subtitle={`Operating context recorded from evidence for ${name}`}
      />

      {anySupported ? (
        <div className="intel-blocks">
          {AREAS.map((area) => (
            <AreaBlock key={area.key} spec={area} section={data.intelligence[area.key]} />
          ))}
        </div>
      ) : (
        <EmptyCopy text="No business intelligence observations are currently supported by evidence for this company." />
      )}

      <p className="business-cross-note">
        Market-side context is in the <a href="#market-context">Market</a> section;
        technology activity is in <a href="#tech-innovation">Technology</a>.
      </p>
    </div>
  )
}
