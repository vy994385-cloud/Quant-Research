/**
 * FINANCIAL PERFORMANCE — research-terminal presentation of reported
 * financials.
 *
 * Primary view: metric × period table with correct units, period-over-period
 * change, and REPORTED / DERIVED distinction. Charts render only for metrics
 * that exist in the data. Technical detail (timestamps, derivation,
 * provenance) stays behind an expandable row — never in the primary view.
 *
 * No raw formulas in the primary view, no provenance IDs, no fabricated
 * values: gaps render as "—".
 */

import { useMemo, useState } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { ChevronDown, ChevronRight } from "lucide-react"
import type { CompanyResearch, DeepFinancialInsights, DeepMetricObservation } from "../api/types"
import {
  formatCrore,
  formatAxisCompact,
  formatDeltaPct,
  formatIso,
  formatLabel,
  formatPeriodColumn,
  formatPitNote,
} from "../lib/format"
import { EmptyCopy, PanelHead, Tag } from "./ui"

type Unit = "thousand_crore" | "crore" | "billion" | "million" | "raw"
type MetricGroup = "all" | "performance" | "cashflow" | "balance" | "ratios" | "other"
type ReportedFilter = "all" | "reported" | "derived"

const UNIT_OPTIONS: Array<{ value: Unit; label: string }> = [
  { value: "crore", label: "₹ Cr" },
  { value: "thousand_crore", label: "₹ Lakh Cr" },
  { value: "billion", label: "$ B scale" },
  { value: "million", label: "M scale" },
  { value: "raw", label: "Raw units" },
]

const GROUP_OPTIONS: Array<{ value: MetricGroup; label: string }> = [
  { value: "all", label: "All groups" },
  { value: "performance", label: "Performance" },
  { value: "cashflow", label: "Cash flow" },
  { value: "balance", label: "Balance sheet" },
  { value: "ratios", label: "Ratios" },
]

const REPORTED_OPTIONS: Array<{ value: ReportedFilter; label: string }> = [
  { value: "all", label: "Reported + derived" },
  { value: "reported", label: "Reported only" },
  { value: "derived", label: "Derived only" },
]

/** Metrics that are ratios/percentages and must not be currency-scaled. */
const RATIO_METRICS = new Set([
  "operating_margin",
  "net_margin",
  "cash_conversion",
  "return_on_assets",
])

/**
 * Curated reading order for the results table: performance first, then
 * balance sheet, then ratios. Unlisted metrics follow alphabetically.
 */
const METRIC_DISPLAY_ORDER = [
  "revenue",
  "net_profit",
  "operating_cash_flow",
  "free_cash_flow",
  "total_assets",
  "total_debt",
  "operating_margin",
  "net_margin",
  "cash_conversion",
  "return_on_assets",
]

const GROUP_MEMBERSHIP: Record<string, Exclude<MetricGroup, "all" | "other">> = {
  revenue: "performance",
  net_profit: "performance",
  operating_cash_flow: "cashflow",
  free_cash_flow: "cashflow",
  total_assets: "balance",
  total_debt: "balance",
}

function metricGroup(metric: string): Exclude<MetricGroup, "all" | "other"> {
  if (RATIO_METRICS.has(metric)) return "ratios"
  return GROUP_MEMBERSHIP[metric] ?? "other"
}

interface PeriodColumn {
  periodEnd: string
  label: string
}

interface MetricRow {
  metric: string
  label: string
  isRatio: boolean
  group: Exclude<MetricGroup, "all" | "other"> | "other"
  /** One cell per period column; missing periods carry no observation. */
  cells: Array<{ obs: DeepMetricObservation | undefined }>
  /** Change between the two most recent periods with values (from API delta). */
  latestChangePct: string | null
  hasDerived: boolean
  technical?: DeepMetricObservation
}

function buildRows(insights: DeepFinancialInsights): {
  periods: PeriodColumn[]
  rows: MetricRow[]
} {
  const periodMap = new Map<string, PeriodColumn>()
  const metricMap = new Map<string, Map<string, DeepMetricObservation>>()

  for (const obs of insights.observations) {
    if (!periodMap.has(obs.period_end)) {
      periodMap.set(obs.period_end, {
        periodEnd: obs.period_end,
        label: formatPeriodColumn(obs.period_end),
      })
    }
    if (!metricMap.has(obs.metric)) metricMap.set(obs.metric, new Map())
    metricMap.get(obs.metric)!.set(obs.period_end, obs)
  }

  // Chronological columns, oldest → newest.
  const periods = [...periodMap.values()].sort((a, b) =>
    a.periodEnd.localeCompare(b.periodEnd),
  )

  const rows: MetricRow[] = [...metricMap.entries()].map(([metric, byPeriod]) => {
    const cells = periods.map((p) => ({ obs: byPeriod.get(p.periodEnd) }))
    const isRatio = RATIO_METRICS.has(metric)
    let latestChangePct: string | null = null
    let hasDerived = false
    let technical: DeepMetricObservation | undefined

    for (let i = cells.length - 1; i >= 0; i -= 1) {
      const obs = cells[i].obs
      if (!obs) continue
      if (obs.observation_type === "DERIVED") hasDerived = true
      if (latestChangePct === null && obs.delta_pct !== null && !isRatio) {
        latestChangePct = obs.delta_pct
      }
      // Newest non-unavailable observation carries the technical detail.
      if (!technical || technical.observation_type === "UNAVAILABLE") {
        if (obs.observation_type !== "UNAVAILABLE" || !technical) technical = obs
      }
    }

    return {
      metric,
      label: formatLabel(metric),
      isRatio,
      group: metricGroup(metric),
      cells,
      latestChangePct,
      hasDerived,
      technical,
    }
  })

  rows.sort((a, b) => {
    const rankA = METRIC_DISPLAY_ORDER.indexOf(a.metric)
    const rankB = METRIC_DISPLAY_ORDER.indexOf(b.metric)
    const orderA = rankA === -1 ? METRIC_DISPLAY_ORDER.length : rankA
    const orderB = rankB === -1 ? METRIC_DISPLAY_ORDER.length : rankB
    if (orderA !== orderB) return orderA - orderB
    return a.metric.localeCompare(b.metric)
  })
  return { periods, rows }
}

function formatRatio(raw: string): string {
  const numeric = Number(raw)
  if (!Number.isFinite(numeric)) return "\u2014"
  // Ratios arrive as fractions (0.24); cash conversion can exceed 1.
  return `${(numeric * 100).toFixed(1)}%`
}

/**
 * Chart tooltips cap precision at one decimal and use the compact axis scale
 * so raw observation tails ("7.64032806826211") never reach the screen.
 */
function formatChartTooltip(
  value: string | number | readonly (string | number)[] | undefined,
): string {
  if (typeof value === "number") {
    return Number.isFinite(value) ? formatAxisCompact(value) : "\u2014"
  }
  return String(value ?? "")
}

/** Chart series grouped per consolidation/period_type series. */
interface ChartSpec {
  key: string
  title: string
  metrics: [string, string | null]
  kind: "currency" | "ratio"
  unit: Unit
  points: Array<{ period: string; primary: number | null; secondary: number | null }>
}

function buildCharts(
  insights: DeepFinancialInsights,
  unit: Unit,
): ChartSpec[] {
  const specs: Array<{
    title: string
    metrics: [string, string | null]
    kind: "currency" | "ratio"
  }> = [
    { title: "Revenue & net profit", metrics: ["revenue", "net_profit"], kind: "currency" },
    { title: "Cash flow", metrics: ["operating_cash_flow", "free_cash_flow"], kind: "currency" },
    { title: "Assets & debt", metrics: ["total_assets", "total_debt"], kind: "currency" },
    { title: "Margins", metrics: ["operating_margin", "net_margin"], kind: "ratio" },
  ]

  const charts: ChartSpec[] = []
  for (const spec of specs) {
    const [primary, secondary] = spec.metrics
    const primaryByPeriod = new Map<string, DeepMetricObservation>()
    const secondaryByPeriod = new Map<string, DeepMetricObservation>()
    for (const obs of insights.observations) {
      if (obs.value === null) continue
      if (obs.metric === primary) primaryByPeriod.set(obs.period_end, obs)
      else if (secondary && obs.metric === secondary) secondaryByPeriod.set(obs.period_end, obs)
    }
    if (primaryByPeriod.size < 2) continue

    const allPeriods = [...new Set([...primaryByPeriod.keys(), ...secondaryByPeriod.keys()])]
      .sort((a, b) => a.localeCompare(b))
    const points = allPeriods.map((period) => ({
      period: formatPeriodColumn(period),
      primary: numericValue(primaryByPeriod.get(period)?.value, spec.kind, unit),
      secondary: secondary
        ? numericValue(secondaryByPeriod.get(period)?.value, spec.kind, unit)
        : null,
    }))

    charts.push({
      key: spec.metrics.filter(Boolean).join("-"),
      title: spec.title,
      metrics: spec.metrics,
      kind: spec.kind,
      unit,
      points,
    })
  }
  return charts
}

function numericValue(
  raw: string | null | undefined,
  kind: "currency" | "ratio",
  unit: Unit,
): number | null {
  if (raw === null || raw === undefined) return null
  const numeric = Number(raw)
  if (!Number.isFinite(numeric)) return null
  // Scale to the display unit so axis labels stay readable.
  if (kind === "ratio") return numeric * 100
  const divisor: Record<Unit, number> = {
    thousand_crore: 1e11,
    crore: 1e7,
    billion: 1e9,
    million: 1e6,
    raw: 1,
  }
  return numeric / divisor[unit]
}

function ChartBlock({ chart }: { chart: ChartSpec }) {
  const axisLabel =
    chart.kind === "ratio"
      ? "%"
      : chart.unit === "raw"
        ? ""
        : (UNIT_OPTIONS.find((o) => o.value === chart.unit)?.label ?? "")
  const tooltipStyle = {
    contentStyle: {
      fontSize: 11,
      borderRadius: 5,
      border: "1px solid var(--color-border)",
      boxShadow: "var(--shadow-md)",
      padding: "6px 10px",
    },
    labelStyle: {
      fontSize: 10,
      fontWeight: 600,
      color: "var(--color-text-secondary)",
      marginBottom: 2,
    },
    itemStyle: { fontSize: 11, color: "var(--color-text)" },
    cursor: { fill: "var(--color-surface-sunken)" },
  }
  return (
    <figure className="fin-chart">
      <figcaption>{chart.title}{axisLabel ? ` (${axisLabel})` : ""}</figcaption>
      <ResponsiveContainer width="100%" height={200}>
        {chart.kind === "ratio" ? (
          <LineChart data={chart.points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-light)" />
            <XAxis dataKey="period" tick={{ fontSize: 11 }} stroke="var(--color-text-tertiary)" />
            <YAxis
              tick={{ fontSize: 11 }}
              stroke="var(--color-text-tertiary)"
              width={44}
              tickCount={4}
              tickFormatter={(v: number) => `${Math.round(v)}%`}
            />
            <Tooltip {...tooltipStyle} formatter={formatChartTooltip} />
            {chart.metrics[0] && (
              <Line
                type="monotone"
                dataKey="primary"
                name={formatLabel(chart.metrics[0])}
                stroke="#2563a8"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            )}
            {chart.metrics[1] && (
              <Line
                type="monotone"
                dataKey="secondary"
                name={formatLabel(chart.metrics[1])}
                stroke="#d97706"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            )}
          </LineChart>
        ) : (
          <BarChart data={chart.points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-light)" vertical={false} />
            <XAxis dataKey="period" tick={{ fontSize: 11 }} stroke="var(--color-text-tertiary)" />
            <YAxis
              tick={{ fontSize: 11 }}
              stroke="var(--color-text-tertiary)"
              width={52}
              tickCount={4}
              domain={["auto", "auto"]}
              tickFormatter={(v: number) => formatAxisCompact(v)}
            />
            <Tooltip {...tooltipStyle} formatter={formatChartTooltip} />
            {chart.metrics[0] && (
              <Bar dataKey="primary" name={formatLabel(chart.metrics[0])} fill="#2563a8" radius={[2, 2, 0, 0]} />
            )}
            {chart.metrics[1] && (
              <Bar dataKey="secondary" name={formatLabel(chart.metrics[1])} fill="#7fa8cc" radius={[2, 2, 0, 0]} />
            )}
          </BarChart>
        )}
      </ResponsiveContainer>
    </figure>
  )
}

function RowTechnicalDetail({ row }: { row: MetricRow }) {
  const obs = row.technical
  if (!obs) return null
  return (
    <div className="fin-row-detail">
      <dl className="data-field-grid">
        {obs.published_at && (
          <div className="data-field">
            <dt className="data-field-label">Published</dt>
            <dd className="data-field-value">{formatIso(obs.published_at)}</dd>
          </div>
        )}
        {obs.available_at && (
          <div className="data-field">
            <dt className="data-field-label">Available</dt>
            <dd className="data-field-value">{formatIso(obs.available_at)}</dd>
          </div>
        )}
        {obs.consolidation && (
          <div className="data-field">
            <dt className="data-field-label">Consolidation</dt>
            <dd className="data-field-value">{formatLabel(obs.consolidation)}</dd>
          </div>
        )}
        {row.hasDerived && (
          <div className="data-field">
            <dt className="data-field-label">Derivation</dt>
            <dd className="data-field-value">{obs.derivation ?? "Computed from reported figures."}</dd>
          </div>
        )}
      </dl>
    </div>
  )
}

function ResearchTableRow({
  row,
  periods,
}: {
  row: MetricRow
  periods: PeriodColumn[]
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <>
      <tr className="fin-table-row">
        <th scope="row" className="fin-metric-cell">
          <button
            type="button"
            className="fin-metric-toggle"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
            aria-controls={`fin-detail-${row.metric}`}
          >
            {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            <span>{row.label}</span>
          </button>
          {row.hasDerived && <Tag text="Derived" tone="blue" />}
        </th>
        {row.cells.map((cell, i) => {
          const obs = cell.obs
          const missing =
            !obs || obs.value === null || obs.observation_type === "UNAVAILABLE"
          return (
            <td key={periods[i].periodEnd} className={missing ? "fin-cell missing" : "fin-cell"}>
              {missing ? (
                <span className="fin-cell-empty">Not reported</span>
              ) : (
                formatCellFromObs(row, obs!)
              )}
            </td>
          )
        })}
        <td className="fin-cell fin-change-cell">
          {row.latestChangePct !== null ? (
            <span className={Number(row.latestChangePct) >= 0 ? "delta-up" : "delta-down"}>
              {formatDeltaPct(row.latestChangePct)}
            </span>
          ) : (
            "\u2014"
          )}
        </td>
      </tr>
      {expanded && (
        <tr className="fin-detail-row">
          <td colSpan={periods.length + 2} id={`fin-detail-${row.metric}`}>
            <RowTechnicalDetail row={row} />
          </td>
        </tr>
      )}
    </>
  )
}

function formatCellFromObs(row: MetricRow, obs: DeepMetricObservation): string {
  if (obs.value === null) return "\u2014"
  return row.isRatio ? formatRatio(obs.value) : formatCrore(obs.value)
}

export default function FinancialDataPanel({ data }: { data: CompanyResearch }) {
  const insights = data.deep_financial_insights
  const [unit, setUnit] = useState<Unit>("crore")
  const [group, setGroup] = useState<MetricGroup>("all")
  const [reported, setReported] = useState<ReportedFilter>("all")
  const [completeOnly, setCompleteOnly] = useState(false)

  const { periods, rows } = useMemo(
    () => (insights ? buildRows(insights) : { periods: [], rows: [] }),
    [insights],
  )

  const visibleRows = useMemo(() => {
    let next = rows
    if (group !== "all") {
      const target = group === "ratios" ? "ratios" : group
      next = next.filter((row) => row.group === target)
    }
    if (reported === "reported") next = next.filter((row) => !row.hasDerived)
    if (reported === "derived") next = next.filter((row) => row.hasDerived)
    if (completeOnly) {
      next = next.filter((row) =>
        row.cells.every(
          (cell) =>
            cell.obs && cell.obs.value !== null && cell.obs.observation_type !== "UNAVAILABLE",
        ),
      )
    }
    return next
  }, [rows, group, reported, completeOnly])

  const charts = useMemo(
    () => (insights ? buildCharts(insights, unit) : []),
    [insights, unit],
  )

  if (!insights || insights.observations.length === 0) {
    return (
      <section id="financial-data" className="section-anchor">
        <PanelHead
          title="Financial Performance"
          subtitle="Reported financials by period"
        />
        <EmptyCopy text="No financial statement observations are available for this company." />
      </section>
    )
  }

  const reportedCount = insights.observations.filter(
    (o) => o.observation_type === "REPORTED",
  ).length

  return (
    <section id="financial-data" className="section-anchor">
      <PanelHead
        title="Financial Performance"
        subtitle={`${reportedCount} reported figures across ${periods.length} reporting period${periods.length !== 1 ? "s" : ""}`}
      />

      {insights.comparability_notes.length > 0 && (
        <ul className="fin-comparability">
          {insights.comparability_notes.map((note) => (
            <li key={note}>{formatPitNote(note)}</li>
          ))}
        </ul>
      )}

      <div className="fin-controls" role="group" aria-label="Table controls">
        <div className="unit-selector">
          <span className="control-label">Unit</span>
          {UNIT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              className={unit === opt.value ? "unit-btn active" : "unit-btn"}
              onClick={() => setUnit(opt.value)}
              aria-pressed={unit === opt.value}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="unit-selector">
          <span className="control-label">Group</span>
          {GROUP_OPTIONS.map((opt) => {
            const count =
              opt.value === "all"
                ? rows.length
                : rows.filter((row) => row.group === opt.value).length
            if (opt.value !== "all" && count === 0) return null
            return (
              <button
                key={opt.value}
                type="button"
                className={group === opt.value ? "unit-btn active" : "unit-btn"}
                onClick={() => setGroup(opt.value)}
                aria-pressed={group === opt.value}
              >
                {opt.label}
                <span className="filter-count">{count}</span>
              </button>
            )
          })}
        </div>
        <div className="unit-selector">
          <span className="control-label">Basis</span>
          {REPORTED_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              className={reported === opt.value ? "unit-btn active" : "unit-btn"}
              onClick={() => setReported(opt.value)}
              aria-pressed={reported === opt.value}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="unit-selector">
          <span className="control-label">Availability</span>
          <button
            type="button"
            className={completeOnly ? "unit-btn active" : "unit-btn"}
            onClick={() => setCompleteOnly((value) => !value)}
            aria-pressed={completeOnly}
          >
            Fully reported rows only
          </button>
        </div>
      </div>

      {periods.length > 0 && rows.length > 0 && visibleRows.length === 0 && (
        <EmptyCopy text="No metrics match the current group, basis or availability filters." />
      )}

      {visibleRows.length > 0 && periods.length > 0 && (
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Financial results table">
          <table className="fin-table">
            <caption className="visually-hidden">
              Reported financial metrics by reporting period
            </caption>
            <thead>
              <tr>
                <th scope="col">Metric</th>
                {periods.map((p) => (
                  <th scope="col" key={p.periodEnd}>{p.label}</th>
                ))}
                <th scope="col">Latest YoY</th>
              </tr>
            </thead>
            {(() => {
              const reportedRows = visibleRows.filter((row) => !row.hasDerived)
              const derivedRows = visibleRows.filter((row) => row.hasDerived)
              const colCount = periods.length + 2
              return (
                <>
                  {reportedRows.length > 0 && (
                    <tbody className="fin-tbody-group">
                      <tr className="fin-group-row">
                        <th colSpan={colCount} scope="colgroup">
                          Reported figures
                        </th>
                      </tr>
                      {reportedRows.map((row) => (
                        <ResearchTableRow
                          key={row.metric}
                          row={row}
                          periods={periods}
                        />
                      ))}
                    </tbody>
                  )}
                  {derivedRows.length > 0 && (
                    <tbody className="fin-tbody-group">
                      <tr className="fin-group-row fin-group-derived">
                        <th colSpan={colCount} scope="colgroup">
                          Derived metrics
                        </th>
                      </tr>
                      {derivedRows.map((row) => (
                        <ResearchTableRow
                          key={row.metric}
                          row={row}
                          periods={periods}
                        />
                      ))}
                    </tbody>
                  )}
                </>
              )
            })()}
          </table>
        </div>
      )}

      {charts.length > 0 && (
        <div className="fin-charts">
          {charts.map((chart) => (
            <ChartBlock key={chart.key} chart={chart} />
          ))}
        </div>
      )}

      <p className="fin-footnote">
        Values as reported or derived from filings at each period end; empty cells were not reported.
        Derived metrics are marked and their computation appears in the expandable row detail.
      </p>
    </section>
  )
}
