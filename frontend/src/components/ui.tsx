/**
 * Small shared UI primitives for the data-first research platform.
 *
 * Purely informational — no scores, confidence bars, or investment judgments.
 */

import type { ReactNode } from "react"
import type { Tone } from "../lib/signal"

export function Tag({
  text,
  tone,
}: {
  text: string
  tone: Tone
}) {
  return <span className={`tag ${tone}`}>{text}</span>
}

export function PanelHead({
  title,
  subtitle,
}: {
  title: string
  subtitle: string
}) {
  return (
    <div className="panel-head">
      <div>
        <h3>{title}</h3>
        <span>{subtitle}</span>
      </div>
    </div>
  )
}

export function EmptyCopy({ text }: { text: string }) {
  return <p className="empty-copy">{text}</p>
}

export function DataField({
  label,
  value,
  mono = false,
}: {
  label: string
  value: ReactNode
  mono?: boolean
}) {
  return (
    <div className="data-field">
      <dt className="data-field-label">{label}</dt>
      <dd className={mono ? "data-field-value mono" : "data-field-value"}>
        {value ?? "\u2014"}
      </dd>
    </div>
  )
}

export function StatusBadge({
  text,
  tone,
}: {
  text: string
  tone: Tone
}) {
  return (
    <span className={`status-badge ${tone}`}>
      <span className="status-badge-dot" />
      {text}
    </span>
  )
}

export function MetricTile({
  label,
  value,
  unit,
  detail,
  tone,
}: {
  label: string
  value: ReactNode
  unit?: string
  detail?: string
  tone?: Tone
}) {
  return (
    <article className={tone ? `metric-tile ${tone}` : "metric-tile"}>
      <span className="metric-tile-label">{label}</span>
      <div className="metric-tile-value">
        <strong>{value ?? "\u2014"}</strong>
        {unit ? <span className="metric-tile-unit">{unit}</span> : null}
      </div>
      {detail ? <small className="metric-tile-detail">{detail}</small> : null}
    </article>
  )
}

export function DeltaIndicator({
  absolute,
  percentage,
  neutral = false,
}: {
  absolute: string
  percentage: string
  neutral?: boolean
}) {
  return (
    <span className={neutral ? "delta-indicator" : "delta-indicator has-value"}>
      <span className="delta-absolute">{absolute}</span>
      <span className="delta-sep">/</span>
      <span className="delta-percentage">{percentage}</span>
    </span>
  )
}

export function SectionDivider({ label }: { label?: string }) {
  return (
    <div className="section-divider">
      {label ? (
        <>
          <span className="section-divider-line" />
          <span className="section-divider-label">{label}</span>
          <span className="section-divider-line" />
        </>
      ) : (
        <span className="section-divider-line full" />
      )}
    </div>
  )
}

/* ── Redesign 2.0 primitives ──────────────────────────────────────── */

export interface TabItem {
  id: string
  label: string
}

/**
 * Anchor tab strip for document-style pages. Tabs scroll to sections;
 * `activeId` (scroll-spy) drives the underline + aria-current state.
 * Horizontally scrollable on narrow viewports.
 */
export function TabStrip({
  items,
  activeId,
  label,
}: {
  items: TabItem[]
  activeId: string | null
  label: string
}) {
  return (
    <nav className="tab-strip" aria-label={label}>
      <div className="tab-strip-track">
        {items.map((item) => (
          <a
            key={item.id}
            href={`#${item.id}`}
            className={activeId === item.id ? "tab-item active" : "tab-item"}
            aria-current={activeId === item.id ? "location" : undefined}
          >
            {item.label}
          </a>
        ))}
      </div>
    </nav>
  )
}

/**
 * Filter chip row used across evidence/observation/event workspaces.
 * Renders as a group of toggle buttons with optional counts.
 */
export function FilterChips<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
}: {
  options: Array<{ value: T; label: string; count?: number }>
  value: T
  onChange: (next: T) => void
  ariaLabel: string
}) {
  return (
    <div className="filter-chips" role="group" aria-label={ariaLabel}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={
            option.value === value ? "filter-chip active" : "filter-chip"
          }
          onClick={() => onChange(option.value)}
          aria-pressed={option.value === value}
        >
          {option.label}
          {typeof option.count === "number" && (
            <span className="chip-count">{option.count}</span>
          )}
        </button>
      ))}
    </div>
  )
}

/**
 * Right-side detail drawer for master/detail explorers.
 * Closes on Escape and overlay click; focus moves to the close button.
 */
/**
 * Dense feed row for discovery surfaces:
 * date | company | event | type | source | verification.
 */
export function FeedTable({
  headers,
  rows,
  caption,
  emptyText,
}: {
  headers: string[]
  rows: Array<{ key: string; cells: ReactNode[]; detail?: ReactNode }>
  caption?: string
  emptyText: string
}) {
  if (rows.length === 0) {
    return <EmptyCopy text={emptyText} />
  }
  return (
    <div className="table-scroll">
      <table className="feed-table">
        {caption ? <caption className="visually-hidden">{caption}</caption> : null}
        <thead>
          <tr>
            {headers.map((header) => (
              <th scope="col" key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              {row.cells.map((cell, i) => (
                <td key={i}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
