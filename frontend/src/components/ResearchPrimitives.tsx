/**
 * Reusable research primitives for the evidence-first platform.
 *
 * These components establish consistent UI patterns across all pages.
 * Every primitive enforces factual presentation — no judgement, no scores.
 *
 * Components:
 * - ResearchSection: consistent section wrapper with anchor, title, subtitle
 * - DataStatus: shows data availability (AVAILABLE / MISSING / STALE / etc.)
 * - PITStatus: point-in-time status indicator
 * - MetricTileCompact: compact metric for inline use
 * - MetricTable: structured table for financial/operational data
 * - ChangeRow: single change observation with source attribution
 * - ObservationCard: research observation with evidence and provenance
 * - FilterChip: removable filter chip for screener
 * - FilterGroup: group of related filters
 * - ProvenanceLink: clickable provenance reference
 */

import type { ReactNode } from "react"
import {
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Shield,
  Database,
} from "lucide-react"
import { formatIso, formatLabel } from "../lib/format"
import { Tag, StatusBadge } from "./ui"
import type { Tone } from "../lib/signal"

/* ── ResearchSection ────────────────────────────────────────────────── */

export function ResearchSection({
  id,
  title,
  subtitle,
  status,
  children,
}: {
  id: string
  title: string
  subtitle?: string
  status?: { label: string; tone: Tone }
  children: ReactNode
}) {
  return (
    <section id={id} className="section-anchor">
      <div className="research-section-head">
        <div>
          <h3>{title}</h3>
          {subtitle && <span className="research-section-subtitle">{subtitle}</span>}
        </div>
        {status && <Tag text={status.label} tone={status.tone} />}
      </div>
      {children}
    </section>
  )
}

/* ── DataStatus ─────────────────────────────────────────────────────── */

export type DataAvailability = "available" | "partial" | "missing" | "stale" | "invalid" | "unavailable"

export function DataStatus({ availability, detail }: { availability: DataAvailability; detail?: string }) {
  const config: Record<DataAvailability, { icon: React.ComponentType<{ size?: number }>; tone: Tone; label: string }> = {
    available: { icon: CheckCircle2, tone: "green", label: "AVAILABLE" },
    partial: { icon: AlertTriangle, tone: "amber", label: "PARTIAL" },
    missing: { icon: XCircle, tone: "red", label: "MISSING" },
    stale: { icon: Clock, tone: "amber", label: "STALE" },
    invalid: { icon: XCircle, tone: "red", label: "INVALID" },
    unavailable: { icon: HelpCircle, tone: "slate", label: "NOT AVAILABLE" },
  }
  const c = config[availability]
  const Icon = c.icon
  return (
    <span className={`data-status data-status-${availability}`}>
      <Icon size={12} />
      <StatusBadge text={c.label} tone={c.tone} />
      {detail && <span className="data-status-detail">{detail}</span>}
    </span>
  )
}

/* ── PITStatus ──────────────────────────────────────────────────────── */

export function PITStatus({
  passed,
  asOf,
  effectiveAsOf,
}: {
  passed: boolean
  asOf?: string
  effectiveAsOf?: string
}) {
  return (
    <span className={`pit-status ${passed ? "pit-ok" : "pit-fail"}`}>
      <Shield size={12} />
      <StatusBadge text={passed ? "PIT OK" : "PIT FAILED"} tone={passed ? "green" : "red"} />
      {asOf && <span className="pit-date">as-of {formatIso(asOf)}</span>}
      {effectiveAsOf && <span className="pit-date">effective {formatIso(effectiveAsOf)}</span>}
    </span>
  )
}

/* ── MetricTileCompact ──────────────────────────────────────────────── */

export function MetricTileCompact({
  label,
  value,
  unit,
  status,
}: {
  label: string
  value: ReactNode
  unit?: string
  status?: DataAvailability
}) {
  return (
    <div className="metric-tile-compact">
      <span className="metric-tile-compact-label">{label}</span>
      <div className="metric-tile-compact-value">
        <strong>{value ?? "\u2014"}</strong>
        {unit && <span className="metric-tile-compact-unit">{unit}</span>}
      </div>
      {status && <DataStatus availability={status} />}
    </div>
  )
}

/* ── MetricTable ────────────────────────────────────────────────────── */

export function MetricTable({
  rows,
  showStatus = false,
}: {
  rows: Array<{
    label: string
    value: ReactNode
    unit?: string
    status?: DataAvailability
    source?: string
  }>
  showStatus?: boolean
}) {
  return (
    <div className="metric-table">
      {rows.map((row) => (
        <div key={row.label} className="metric-table-row">
          <span className="metric-table-label">{row.label}</span>
          <span className="metric-table-value">
            {row.value ?? "\u2014"}
            {row.unit && <span className="metric-table-unit">{row.unit}</span>}
          </span>
          {showStatus && row.status && (
            <span className="metric-table-status">
              <DataStatus availability={row.status} />
            </span>
          )}
          {row.source && <span className="metric-table-source">{row.source}</span>}
        </div>
      ))}
    </div>
  )
}

/* ── ChangeRow ──────────────────────────────────────────────────────── */

export function ChangeRow({
  label,
  previous,
  current,
  delta,
  deltaPct,
  period,
  source,
}: {
  label: string
  previous?: string | null
  current?: string | null
  delta?: string | null
  deltaPct?: string | null
  period?: string
  source?: string
}) {
  return (
    <div className="change-row">
      <span className="change-row-label">{label}</span>
      <span className="change-row-values">
        {previous != null && <span className="change-row-prev">{previous}</span>}
        {previous != null && current != null && <span className="change-row-arrow">→</span>}
        {current != null && <span className="change-row-curr">{current}</span>}
        {delta != null && (
          <span className={`change-row-delta ${Number(delta) >= 0 ? "positive" : "negative"}`}>
            {Number(delta) >= 0 ? "+" : ""}{delta}
            {deltaPct != null && ` (${Number(deltaPct) >= 0 ? "+" : ""}${(Number(deltaPct) * 100).toFixed(1)}%)`}
          </span>
        )}
      </span>
      {period && <span className="change-row-period">{period}</span>}
      {source && <span className="change-row-source">{source}</span>}
    </div>
  )
}

/* ── ObservationCard ────────────────────────────────────────────────── */

export function ObservationCard({
  title,
  category,
  direction,
  explanation,
  date,
  source,
  confidence,
  evidenceType,
}: {
  title: string
  category?: string
  direction?: string
  explanation?: string
  date?: string
  source?: string
  confidence?: string
  evidenceType?: string
}) {
  const dirTone: Record<string, Tone> = {
    POSITIVE: "green",
    NEGATIVE: "red",
    NEUTRAL: "slate",
    MIXED: "amber",
  }

  return (
    <div className="observation-card">
      <div className="observation-card-head">
        {direction && dirTone[direction] && (
          <Tag text={direction} tone={dirTone[direction]} />
        )}
        {category && <Tag text={formatLabel(category)} tone="slate" />}
        <strong>{title}</strong>
        {date && <span className="observation-card-date">{formatIso(date)}</span>}
      </div>
      {explanation && <p className="observation-card-body">{explanation}</p>}
      <div className="observation-card-meta">
        {evidenceType && <span>Type: {evidenceType}</span>}
        {confidence && <span>Confidence: {confidence}</span>}
        {source && <span>Source: {source}</span>}
      </div>
    </div>
  )
}

/* ── FilterChip ─────────────────────────────────────────────────────── */

export function FilterChip({
  label,
  value,
  onRemove,
}: {
  label: string
  value: string
  onRemove?: () => void
}) {
  return (
    <span className="filter-chip">
      <span className="filter-chip-label">{label}:</span>
      <span className="filter-chip-value">{value}</span>
      {onRemove && (
        <button className="filter-chip-remove" onClick={onRemove} aria-label={`Remove ${label} filter`}>
          <XCircle size={12} />
        </button>
      )}
    </span>
  )
}

/* ── FilterGroup ────────────────────────────────────────────────────── */

export function FilterGroup({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <div className="filter-group">
      <span className="filter-group-label">{label}</span>
      <div className="filter-group-options">{children}</div>
    </div>
  )
}

/* ── ProvenanceLink ─────────────────────────────────────────────────── */

export function ProvenanceLink({
  source,
  sourceType,
  recordId,
  retrievedAt,
  availableAt,
}: {
  source: string
  sourceType?: string
  recordId?: string | null
  retrievedAt?: string | null
  availableAt?: string | null
}) {
  return (
    <div className="provenance-link">
      <Database size={12} />
      <span className="provenance-link-source">{source}</span>
      {sourceType && <Tag text={formatLabel(sourceType)} tone="slate" />}
      {recordId && <span className="provenance-link-id mono">{recordId}</span>}
      {retrievedAt && <span className="provenance-link-date">retrieved {formatIso(retrievedAt)}</span>}
      {availableAt && <span className="provenance-link-date">available {formatIso(availableAt)}</span>}
    </div>
  )
}

/* ── UnsupportedData ────────────────────────────────────────────────── */

export function UnsupportedData({
  feature,
  description,
}: {
  feature: string
  description?: string
}) {
  return (
    <div className="unsupported-data">
      <div className="unsupported-data-head">
        <HelpCircle size={13} />
        <strong>{feature}</strong>
        <Tag text="NOT YET AVAILABLE" tone="amber" />
      </div>
      {description && <p>{description}</p>}
    </div>
  )
}
