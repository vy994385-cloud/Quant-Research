/**
 * VISUAL SYSTEM 3.0 — consolidated UI primitives.
 *
 * Premium dark research terminal language:
 *   flat layered panels · hairline separators · one cool cyan accent
 *   semantic badges · tabular numerals · restrained motion.
 *
 * Every export is backward compatible with prior pages. New primitives
 * (PageShell, Section, MetricStrip, ChartShell, SegmentedControl,
 * ResearchTable, SourceBadge, PITBadge, …) are additive.
 */

import type { ReactNode } from "react"
import { useEffect, useRef } from "react"
import { X } from "lucide-react"
import type { Tone } from "../lib/signal"

/* ── Semantic badges ─────────────────────────────────────────────── */

export function Tag({
  text,
  tone,
}: {
  text: string
  tone: Tone
}) {
  return <span className={`tag ${tone}`}>{text}</span>
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

/** Provenance source chip: mono, quiet, never decorative. */
export function SourceBadge({
  source,
  recordId,
}: {
  source: string
  recordId?: string | null
}) {
  return (
    <span className="source-badge">
      <span>{source}</span>
      {recordId ? <span>· {recordId}</span> : null}
    </span>
  )
}

/** Point-in-time verified marker — cyan/teal credibility accent. */
export function PITBadge({
  label = "PIT VERIFIED",
}: {
  label?: string
}) {
  return <span className="pit-badge">{label}</span>
}

/* ── Page structure ──────────────────────────────────────────────── */

export type PageShellWidth = "data" | "reading" | "report"

/** Canvas wrapper: intentional max-width per page archetype. */
export function PageShell({
  width = "data",
  children,
  className = "",
}: {
  width?: PageShellWidth
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`page-shell page-shell--${width} ${className}`.trim()}>
      {children}
    </div>
  )
}

/** Semantic section with editorial header row. */
export function Section({
  id,
  title,
  subtitle,
  meta,
  children,
  className = "",
}: {
  id?: string
  title: string
  subtitle?: string
  meta?: ReactNode
  children?: ReactNode
  className?: string
}) {
  return (
    <section id={id} className={`section ${className}`.trim()}>
      <header className="section-head">
        <div>
          <h3 className="section-title">{title}</h3>
          {subtitle && <p className="section-subtitle">{subtitle}</p>}
        </div>
        {meta && <div className="section-meta">{meta}</div>}
      </header>
      {children}
    </section>
  )
}

/** Reusable section header with title, subtitle, meta, and optional aside. */
export function SectionHeader({
  title,
  subtitle,
  meta,
  aside,
}: {
  title: string
  subtitle?: string
  meta?: ReactNode
  aside?: ReactNode
}) {
  return (
    <div className="section-head">
      <div>
        <h3 className="section-title">{title}</h3>
        {subtitle && <p className="section-subtitle">{subtitle}</p>}
        {meta && <span className="section-meta">{meta}</span>}
      </div>
      {aside && <div className="section-aside">{aside}</div>}
    </div>
  )
}

/** Panel header row: uppercase micro-title + optional aside. */
export function PanelHeader({
  title,
  aside,
}: {
  title: string
  aside?: ReactNode
}) {
  return (
    <div className="panel-header">
      <h4>{title}</h4>
      {aside}
    </div>
  )
}

/* ── Legacy panel head (kept for existing pages) ─────────────────── */

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

/* ── Label / value pairing ───────────────────────────────────────── */

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

/* ── MetricStrip: dense KPI band, no floating cards ─────────────── */

const STRIP_VALUE_TONES = new Set(["positive", "negative"])

export function MetricStripCell({
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
  tone?: "positive" | "negative" | "neutral"
}) {
  const toneClass =
    tone && STRIP_VALUE_TONES.has(tone) ? ` ${tone}` : ""
  return (
    <div className="metric-strip-cell">
      <span className="metric-strip-label">{label}</span>
      <div className={`metric-strip-value${toneClass}`}>
        {value ?? "\u2014"}
        {unit ? <span className="metric-strip-unit">{unit}</span> : null}
      </div>
      {detail ? <small className="metric-strip-detail">{detail}</small> : null}
    </div>
  )
}

export function MetricStrip({
  cells,
  children,
}: {
  cells?: Array<Parameters<typeof MetricStripCell>[0]>
  children?: ReactNode
}) {
  return (
    <div className="metric-strip">
      {cells?.map((cell, i) => <MetricStripCell key={i} {...cell} />)}
      {children}
    </div>
  )
}

/* ── Legacy metric tile (kept; styled by .metric-tile) ──────────── */

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

/* ── Metric: primary standalone metric primitive ─────────────────── */

export function Metric({
  label,
  value,
  unit,
  detail,
  tone,
  className = "",
}: {
  label: string
  value: ReactNode
  unit?: string
  detail?: string
  tone?: Tone
  className?: string
}) {
  return (
    <article className={`metric-tile${tone ? ` ${tone}` : ""} ${className}`.trim()}>
      <span className="metric-tile-label">{label}</span>
      <strong className="metric-tile-value">{value}</strong>
      {unit && <span className="metric-tile-unit">{unit}</span>}
      {detail && <span className="metric-tile-detail">{detail}</span>}
    </article>
  )
}

/* ── Delta / dividers ────────────────────────────────────────────── */

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

/* ── Tabs — smooth active underline transition ──────────────────── */

export interface TabItem {
  id: string
  label: string
}

/**
 * Anchor tab strip for document-style pages. Tabs scroll to sections;
 * `activeId` (scroll-spy) drives the underline + aria-current state.
 * The underline animates via CSS transition on border-color/transform.
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

/* ── SegmentedControl — animated active state ───────────────────── */

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
  size = "md",
}: {
  options: Array<{ value: T; label: string }>
  value: T
  onChange: (next: T) => void
  ariaLabel: string
  size?: "sm" | "md"
}) {
  return (
    <div
      className={`seg-control seg-control--${size}`}
      role="tablist"
      aria-label={ariaLabel}
    >
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="tab"
          aria-selected={option.value === value}
          className={
            option.value === value
              ? "seg-control-item active"
              : "seg-control-item"
          }
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

/* ── FilterBar + chips ───────────────────────────────────────────── */

export function FilterBar({
  label,
  children,
}: {
  label?: string
  children: ReactNode
}) {
  return (
    <div className="filter-bar" role="group">
      {label && <span className="filter-bar-label">{label}</span>}
      {label && <span className="filter-bar-divider" aria-hidden />}
      {children}
    </div>
  )
}

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
    <div className="filter-bar" role="group" aria-label={ariaLabel}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={
            option.value === value ? "filter-chip-btn active" : "filter-chip-btn"
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

/* ── ResearchTable: standardized dense table shell ──────────────── */

export function ResearchTable({
  headers,
  rows,
  caption,
  emptyText,
  footNote,
  align,
  stickyHeader = true,
}: {
  headers: string[]
  rows: Array<{ key: string; cells: ReactNode[]; detail?: ReactNode; selected?: boolean }>
  caption?: string
  emptyText: string
  footNote?: string
  /** Per-column alignment: "left" (default) or "num" for tabular numerals */
  align?: Array<"left" | "num">
  stickyHeader?: boolean
}) {
  if (rows.length === 0) {
    return <EmptyCopy text={emptyText} />
  }
  const cellClass = (i: number) =>
    align?.[i] === "num" ? "num" : undefined
  return (
    <div className="research-table-wrap">
      <div className="table-scroll data-table-wrap">
        <table
          className={`data-table${stickyHeader ? " has-sticky-header" : ""}`}
        >
          {caption ? <caption className="visually-hidden">{caption}</caption> : null}
          <thead>
            <tr>
              {headers.map((header, i) => (
                <th scope="col" key={header} className={cellClass(i)}>
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className={row.selected ? "row-selected" : undefined}>
                {row.cells.map((cell, i) => (
                  <td key={i} className={cellClass(i)}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {footNote && (
        <div className="research-table-foot">
          <span>{footNote}</span>
        </div>
      )}
    </div>
  )
}

/* ── FeedTable (legacy master/detail feed; restyled via CSS) ────── */

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

/* ── ChartShell — title/subtitle/unit/legend/source/as_of ──────── */

export function ChartShell({
  title,
  subtitle,
  unit,
  legend,
  source,
  asOf,
  height,
  children,
}: {
  title: string
  subtitle?: string
  unit?: string
  legend?: Array<{ label: string; color: string }>
  source?: string
  asOf?: string
  height?: number
  children: ReactNode
}) {
  return (
    <figure className="chart-shell" style={height ? { minHeight: height } : undefined}>
      <div className="chart-shell-head">
        <div>
          <h4 className="chart-shell-title">{title}</h4>
          {subtitle && <p className="chart-shell-subtitle">{subtitle}</p>}
        </div>
        {unit && <span className="chart-shell-unit">{unit}</span>}
      </div>
      {(legend?.length || source || asOf) && (
        <div className="chart-shell-foot">
          {legend?.length ? (
            <div className="chart-shell-legend">
              {legend.map((entry) => (
                <span key={entry.label}>
                  <span
                    className="legend-swatch"
                    style={{ background: entry.color }}
                  />
                  {entry.label}
                </span>
              ))}
            </div>
          ) : <span />}
          <span>
            {source}
            {source && asOf ? " · " : ""}
            {asOf ? `as of ${asOf}` : ""}
          </span>
        </div>
      )}
      <div className="chart-shell-body">{children}</div>
    </figure>
  )
}

/* ── DetailDrawer — standardized right drawer ───────────────────── */

export function DetailDrawer({
  open,
  onClose,
  kicker,
  title,
  footer,
  width = 480,
  children,
}: {
  open: boolean
  onClose: () => void
  kicker?: string
  title: ReactNode
  footer?: ReactNode
  width?: number
  children: ReactNode
}) {
  const closeRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!open) return undefined
    const previous = document.activeElement as HTMLElement | null
    closeRef.current?.focus()
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose()
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.removeEventListener("keydown", handleKeyDown)
      previous?.focus?.()
    }
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="drawer-root" role="dialog" aria-modal="true">
      <button type="button" className="drawer-scrim" onClick={onClose} aria-label="Close details" />
      <div className="drawer" style={{ width: `min(${width}px, 94vw)` }}>
        <div className="drawer-head">
          <div>
            {kicker && <div className="drawer-kicker">{kicker}</div>}
            <div className="drawer-title">{title}</div>
          </div>
          <button
            type="button"
            ref={closeRef}
            className="drawer-close"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={15} />
          </button>
        </div>
        <div className="drawer-body">{children}</div>
        {footer && <div className="drawer-footer">{footer}</div>}
      </div>
    </div>
  )
}
