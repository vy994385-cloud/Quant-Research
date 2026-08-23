/**
 * DATA COVERAGE — one compact matrix of what this research has, what is
 * limited, missing, stale, or unsupported by evidence.
 *
 * Replaces scattered warning cards: a fixed six-row table (status, item count,
 * expandable details). No feature keys, no provider IDs in the summary — those
 * stay in the technical detail.
 */

import { Fragment, useMemo, useState } from "react"
import { ChevronDown } from "lucide-react"
import type { CompanyResearch } from "../api/types"
import { formatLabel, formatSourceName, splitMeasureUncertainty } from "../lib/format"
import { PanelHead } from "./ui"

type CoverageStatus = "available" | "limited" | "missing" | "stale" | "insufficient" | "conflict"

interface CoverageItem {
  status: CoverageStatus
  summary: string
  details: string[]
}

const STATUS_ORDER: CoverageStatus[] = [
  "available",
  "limited",
  "missing",
  "stale",
  "insufficient",
  "conflict",
]

const STATUS_META: Record<CoverageStatus, { label: string; toneClass: string }> = {
  available: { label: "Available", toneClass: "ok" },
  limited: { label: "Limited", toneClass: "warn" },
  missing: { label: "Missing", toneClass: "bad" },
  stale: { label: "Stale", toneClass: "warn" },
  insufficient: { label: "Insufficient evidence", toneClass: "warn" },
  conflict: { label: "Conflicting evidence", toneClass: "warn" },
}

function buildCoverage(data: CompanyResearch): CoverageItem[] {
  const dq = data.data_quality
  const pit = data.point_in_time
  const intel = data.intelligence

  const available: string[] = []
  const limited: string[] = []
  const missing: string[] = []
  const stale: string[] = []
  const insufficient: string[] = []
  const conflict: string[] = []

  // ── Core datasets ──────────────────────────────────────────────
  if (!dq.financial_data_missing && dq.financial_record_count > 0) {
    available.push(
      `Financial statements (${dq.financial_record_count} records)`,
    )
  } else {
    missing.push("Financial statement records")
  }

  if (dq.market_accepted_records > 0) {
    available.push(
      `Market price history (${dq.market_accepted_records} validated records)`,
    )
  }
  if (dq.market_rejected_records > 0) {
    limited.push(
      `${dq.market_rejected_records} market record${dq.market_rejected_records !== 1 ? "s" : ""} rejected during validation`,
    )
  }

  // ── Intelligence sections ──────────────────────────────────────
  const sections: Array<[string, typeof intel.business_quality]> = [
    ["Business quality", intel.business_quality],
    ["Financial quality", intel.financial_quality],
    ["Competitive position", intel.competitive_position],
    ["Capital allocation", intel.capital_allocation],
    ["Customer intelligence", intel.customer_intelligence],
    ["Management", intel.management_intelligence],
    ["Market intelligence", intel.market_intelligence],
    ["Innovation", intel.innovation],
    ["Future technology", intel.future_technology],
    ["Risks & anomalies", intel.risks_anomalies],
  ]
  for (const [label, section] of sections) {
    if (section === null) {
      missing.push(`${label} analysis`)
    } else if (section.observations.length === 0) {
      insufficient.push(`${label}: no supported observations`)
    }
  }

  // ── Timeline / coverage ────────────────────────────────────────
  const rs = data.research_status
  if (rs) {
    const coveredCategories = Object.keys(rs.coverage.by_category).length
    if (rs.coverage.item_count > 0) {
      available.push(`Evidence timeline (${rs.coverage.item_count} items across ${coveredCategories} categories)`)
    }
    if (rs.coverage.missing_categories.length > 0) {
      missing.push(
        `No events recorded for: ${rs.coverage.missing_categories.map(formatLabel).join(", ")}`,
      )
    }
    if (rs.quality.insufficient_evidence_notes.length > 0) {
      insufficient.push(...rs.quality.insufficient_evidence_notes)
    }
  }

  // ── Source freshness ───────────────────────────────────────────
  for (const source of data.source_statuses) {
    if (source.stale) {
      stale.push(
        `${formatSourceName(source.source_name)}: ${source.days_since_latest_published ?? "?"} days since latest publication`,
      )
    }
  }
  if (pit.sources_rejected > 0) {
    limited.push(`${pit.sources_rejected} source${pit.sources_rejected !== 1 ? "s" : ""} discovered but not accepted into this snapshot`)
  }

  // ── Point-in-time ──────────────────────────────────────────────
  if (pit.future_evidence_excluded > 0) {
    limited.push(
      `${pit.future_evidence_excluded} evidence item${pit.future_evidence_excluded !== 1 ? "s" : ""} published after the as-of cutoff and excluded`,
    )
  }

  // ── Narrative-flagged gaps & uncertainty ───────────────────────
  // Uniform "measure has limited evidence reliability" sentences condense
  // into one summary line instead of repeating the same boilerplate.
  if (data.narrative) {
    const { measures, other } = splitMeasureUncertainty(data.narrative.uncertainty)
    if (measures.length > 0) {
      insufficient.push(
        `${measures.length} recorded measure${measures.length !== 1 ? "s" : ""} with limited evidence reliability: ${measures.join(", ")}`,
      )
    }
    insufficient.push(...other)
    missing.push(...data.narrative.evidence_gaps)
  }

  // ── Conflicting evidence (kept apart from missing data) ────────
  if (data.assessment.conflict_detected) {
    conflict.push(
      "Supporting and contradicting evidence are both recorded for this company; review the Research Overview narrative before weighing direction.",
    )
  }

  // ── Provider failures (technical, kept at detail depth) ────────
  const providerFailures = [...dq.provider_failures, ...data.provider_failures]
  if (providerFailures.length > 0) {
    missing.push(
      `${providerFailures.length} research provider${providerFailures.length !== 1 ? "s" : ""} failed and were isolated from this snapshot (${providerFailures.join(", ")})`,
    )
  }

  const groups: CoverageItem[] = [
    { status: "available", summary: "", details: available },
    { status: "limited", summary: "", details: limited },
    { status: "missing", summary: "", details: missing },
    { status: "stale", summary: "", details: stale },
    { status: "insufficient", summary: "", details: insufficient },
    { status: "conflict", summary: "", details: conflict },
  ]
  return groups.map((group) => ({
    ...group,
    summary:
      group.details.length > 0
        ? `${group.details.length} item${group.details.length !== 1 ? "s" : ""}`
        : "None",
  }))
}

function CoverageRow({ group }: { group: CoverageItem }) {
  const [open, setOpen] = useState(false)
  const meta = STATUS_META[group.status]
  const count = group.details.length
  const hasItems = count > 0

  return (
    <Fragment key={group.status}>
      <tr className={`coverage-row coverage-${meta.toneClass}`}>
        <th scope="row" className="coverage-status-label">
          <span className="coverage-dot" aria-hidden />
          {meta.label}
        </th>
        <td className="coverage-count-cell">
          <button
            type="button"
            className="coverage-group-head"
            onClick={() => hasItems && setOpen(!open)}
            disabled={!hasItems}
            aria-expanded={hasItems ? open : undefined}
            aria-controls={`coverage-${group.status}`}
            aria-label={hasItems ? `${meta.label}: ${count} item${count !== 1 ? "s" : ""}` : undefined}
          >
            {count > 0 ? `${count} item${count !== 1 ? "s" : ""}` : "None"}
            {hasItems && (
              <ChevronDown size={13} className={open ? "chevron-open" : ""} aria-hidden />
            )}
          </button>
        </td>
      </tr>
      {open && hasItems && (
        <tr className="coverage-detail-row">
          <td colSpan={2} id={`coverage-${group.status}`}>
            <ul className="coverage-details">
              {group.details.map((detail) => (
                <li key={detail}>{detail}</li>
              ))}
            </ul>
          </td>
        </tr>
      )}
    </Fragment>
  )
}

export default function DataCoveragePanel({ data }: { data: CompanyResearch }) {
  const groups = useMemo(() => buildCoverage(data), [data])
  const pitOk = data.point_in_time.pit_checks_passed

  return (
    <section id="data-coverage" className="section-anchor">
      <PanelHead
        title="Data Coverage"
        subtitle="What this research has, what is limited, missing, stale, or unsupported"
      />

      <div className="table-scroll coverage-table-wrap" tabIndex={0} role="region" aria-label="Coverage matrix">
        <table className="coverage-table">
          <caption className="visually-hidden">
            Coverage status with item counts and expandable details
          </caption>
          <thead>
            <tr>
              <th scope="col">Status</th>
              <th scope="col">Items</th>
            </tr>
          </thead>
          <tbody>
            {STATUS_ORDER.map((status) => {
              const group = groups.find((g) => g.status === status)!
              return <CoverageRow key={status} group={group} />
            })}
          </tbody>
        </table>
      </div>

      {!pitOk && (
        <p className="coverage-pit-note" role="status">
          Point-in-time checks did not all pass for this snapshot; review evidence
          timestamps with extra caution.
        </p>
      )}
    </section>
  )
}
