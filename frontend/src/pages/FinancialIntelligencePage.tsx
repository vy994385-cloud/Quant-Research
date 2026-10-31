/**
 * Financial Intelligence page: deep financial research workspace.
 * Fetches actual deep financial insights per company from CompanyResearch.
 * Structured sections: overview, trend charts, fundamentals tables, balance sheet, observations.
 * Every derived metric exposes: period, source, calculation status.
 * No scores or rankings.
 */

/* Chart palette — aligned with design tokens in index.css */
const CHART = {
  primary: "#2563a8",
  positive: "#059669",
  amber: "#d97706",
  grid: "#e2e8f0",
  axis: "#718096",
  border: "#d8dee6",
} as const

/** Rows visible in the All Observations disclosure before "Show all". */
const OBS_PREVIEW_COUNT = 12

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  TrendingUp,
  Search,
  FileSearch,
  ArrowDownRight,
  ArrowUpRight,
  Minus,
} from "lucide-react"
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts"
import { fetchDiscovery, fetchResearch } from "../api/client"
import { ApiError } from "../api/client"
import type { CompanyResearch, DeepMetricObservation, DiscoveryItem } from "../api/types"
import { formatCrore, formatCroreNumber, formatIso, formatLabel, pluralize, toCrore } from "../lib/format"
import { observationTypeTone } from "../lib/signal"
import { Tag, Section } from "../components/ui"
import { LoadingState, EmptyState, ErrorState } from "../components/States"

/* ── Helpers ──────────────────────────────────────────────────────────── */

function parseNum(v: string | null | undefined): number | null {
  if (v == null) return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

function fmtPct(v: string | null | undefined): string {
  const n = parseNum(v)
  if (n === null) return "\u2014"
  return `${n >= 0 ? "+" : ""}${(n * 100).toFixed(1)}%`
}

/** Ratio-scale values (margins) render as percentages, never raw decimals. */
function fmtRatio(v: string | null | undefined): string {
  const n = parseNum(v)
  if (n === null) return "\u2014"
  return `${(n * 100).toFixed(1)}%`
}

function fmtValue(v: string | null | undefined): string {
  const n = parseNum(v)
  if (n === null) return "\u2014"
  return formatCrore(v, { withSymbol: false })
}

/**
 * Period ids arrive as internal record ids ("HDFCBANK:2026-03-31:ANNUAL:UNKNOWN").
 * Extract the embedded date and render it as a readable period label; the
 * short style ("Mar 26") suits chart ticks, the full style table headers.
 */
function periodLabel(periodId: string | null | undefined, style: "short" | "full" = "full"): string {
  if (!periodId) return "\u2014"
  const match = /(\d{4})-(\d{2})-(\d{2})/.exec(periodId)
  if (!match) return periodId
  if (style === "short") {
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return `${monthNames[Number(match[2]) - 1] ?? match[2]} ${match[1].slice(2)}`
  }
  return formatIso(match[0])
}

/** Period basis extracted from the internal record id ("…:ANNUAL:…"). */
function periodType(periodId: string | null | undefined): "annual" | "quarterly" | "other" {
  if (!periodId) return "other"
  const match = /:\s*(ANNUAL|QUARTERLY|MONTHLY)\b/i.exec(periodId)
  if (!match) return "other"
  return match[1].toLowerCase() === "annual" ? "annual" : "quarterly"
}

const REVENUE_METRICS = ["revenue", "total_revenue", "net_revenue", "operating_revenue"]
const OPERATING_INCOME_METRICS = ["operating_income", "operating_profit", "ebit", "ebitda"]
const NET_INCOME_METRICS = ["net_income", "net_profit", "profit_after_tax", "PAT"]
const MARGIN_METRICS = ["operating_margin", "net_margin", "gross_margin", "ebitda_margin"]
const CASH_FLOW_METRICS = ["cash_from_operations", "operating_cash_flow", "CFO", "free_cash_flow", "FCF"]
const CAPEX_METRICS = ["capital_expenditure", "capex", "capital_expenditures"]
const BALANCE_CASH = ["cash_and_equivalents", "cash", "total_cash"]
const BALANCE_ASSETS = ["total_assets", "current_assets", "non_current_assets", "fixed_assets"]
const BALANCE_LIABILITIES = ["total_liabilities", "current_liabilities", "non_current_liabilities", "working_capital"]
const BALANCE_DEBT = ["total_debt", "long_term_debt", "short_term_debt"]
const BALANCE_EQUITY = ["total_equity", "shareholders_equity", "stockholders_equity"]
const BALANCE_RECEIVABLES = ["accounts_receivable", "trade_receivables", "receivables"]
const BALANCE_INVENTORY = ["inventory", "inventories"]
const BALANCE_PAYABLES = ["accounts_payable", "trade_payables", "payables"]

const CURRENCY_METRICS = [
  ...REVENUE_METRICS,
  ...OPERATING_INCOME_METRICS,
  ...NET_INCOME_METRICS,
  ...CASH_FLOW_METRICS,
  ...CAPEX_METRICS,
  ...BALANCE_CASH,
  ...BALANCE_ASSETS,
  ...BALANCE_LIABILITIES,
  ...BALANCE_DEBT,
  ...BALANCE_EQUITY,
  ...BALANCE_RECEIVABLES,
  ...BALANCE_INVENTORY,
  ...BALANCE_PAYABLES,
]

/**
 * Ratio-scale detection for the observation disclosure: margins, returns and
 * coverage ratios read as percentages. Margin patterns win first because
 * names like "ebitda_margin" substring-match the currency candidate "ebitda".
 */
function isRatioMetric(obs: DeepMetricObservation): boolean {
  const m = obs.metric.toLowerCase()
  // Only known ratio/percentage semantics are rendered as percentages.
  // Treating every unrecognised metric as a ratio caused absolute values such
  // as total_assets to be multiplied by 100 and displayed as enormous percent.
  return (
    m.includes("margin") ||
    m.endsWith("_ratio") ||
    m.includes("return_on") ||
    m.endsWith("_yield") ||
    m.includes("growth") ||
    m.includes("conversion") ||
    m === "roe" ||
    m === "roce"
  )
}

/**
 * Value formatting for the observation disclosure: ratio-scale metrics read
 * as percentages, statement figures follow the crore convention, and any
 * other metric keeps grouped digits — raw floats never leak into the UI.
 */
export function fmtObsValue(obs: DeepMetricObservation, value: string | null): string {
  if (value === null) return "\u2014"
  if (isRatioMetric(obs)) return fmtRatio(value)
  if (matchMetric(obs, CURRENCY_METRICS)) return fmtValue(value)
  const n = parseNum(value)
  return n === null ? "\u2014" : n.toLocaleString("en-IN", { maximumFractionDigits: 2 })
}

function matchMetric(obs: DeepMetricObservation, candidates: string[]): boolean {
  const m = obs.metric.toLowerCase()
  return candidates.some((c) => m.includes(c.toLowerCase()))
}

function findObs(observations: DeepMetricObservation[], candidates: string[]): DeepMetricObservation | undefined {
  return observations.find((o) => matchMetric(o, candidates) && o.value !== null)
}

function getMetricGroup(observations: DeepMetricObservation[], candidates: string[]): DeepMetricObservation[] {
  return observations.filter((o) => matchMetric(o, candidates))
}

/* ── Trend Chart ──────────────────────────────────────────────────────── */

function TrendChart({
  title,
  data,
  lines,
  unit,
}: {
  title: string
  data: Array<Record<string, string | number | null>>
  lines: Array<{ key: string; color: string; label: string }>
  unit?: "currency" | "pct"
}) {
  if (data.length === 0) return null

  const tickFormatter = (v: number) =>
    unit === "pct" ? `${Math.round(v * 100)}%` : Math.round(v).toLocaleString("en-IN")
  const tooltipFormatter = (value: number | string) => {
    const n = typeof value === "number" ? value : Number(value)
    if (!Number.isFinite(n)) return String(value ?? "\u2014")
    return unit === "pct"
      ? fmtRatio(String(n))
      : `${formatCroreNumber(n)} Cr`
  }

  return (
    <div className="fi-chart-card">
      <div className="fi-chart-head">
        <strong>{title}</strong>
        {unit && <span className="fi-chart-unit">{unit === "pct" ? "% of revenue" : "₹ crore"}</span>}
      </div>
      <div className="fi-chart-body">
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
            <XAxis dataKey="period" tick={{ fontSize: 10, fill: CHART.axis }} />
            <YAxis
              tick={{ fontSize: 10, fill: CHART.axis }}
              tickFormatter={(v: number) => tickFormatter(v)}
              width={unit === "pct" ? 44 : 64}
              tickCount={4}
            />
            <Tooltip
              contentStyle={{ fontSize: 11, borderRadius: 4, border: `1px solid ${CHART.border}` }}
              formatter={(value, name) => [tooltipFormatter(value as number), String(name ?? "")]}
            />
            <Legend wrapperStyle={{ fontSize: 10 }} />
            {lines.map((l) => (
              <Line
                key={l.key}
                type="monotone"
                dataKey={l.key}
                stroke={l.color}
                strokeWidth={2}
                dot={{ r: 3 }}
                name={l.label}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

/* ── Financial Overview ───────────────────────────────────────────────── */

function FinancialOverview({
  observations,
  periodEnds,
}: {
  observations: DeepMetricObservation[]
  periodEnds: string[]
}) {
  const latestPeriod = periodEnds[periodEnds.length - 1]
  const latestObs = observations.filter((o) => o.period_end === latestPeriod && o.value !== null)

  const revenue = findObs(latestObs, REVENUE_METRICS)
  const opIncome = findObs(latestObs, OPERATING_INCOME_METRICS)
  const netIncome = findObs(latestObs, NET_INCOME_METRICS)
  const opMargin = findObs(latestObs, MARGIN_METRICS)
  const cfo = findObs(latestObs, ["cash_from_operations", "operating_cash_flow", "CFO"])
  const fcf = findObs(latestObs, ["free_cash_flow", "FCF"])

  return (
    <Section title="Financial overview" className="fi-overview">
      <div className="fi-overview-meta">
        <span>Latest period: <strong>{latestPeriod ? formatIso(latestPeriod) : "\u2014"}</strong></span>
        <span>{latestObs.length} observations available</span>
      </div>
      <div className="fi-overview-grid">
        <div className="fi-overview-tile">
          <span className="fi-overview-label">Revenue</span>
          <span className="fi-overview-value mono">{revenue ? fmtValue(revenue.value) : "\u2014"}</span>
          {revenue && revenue.delta_pct && <span className={`fi-overview-delta ${(parseNum(revenue.delta_pct) ?? 0) >= 0 ? "pos" : "neg"}`}>{fmtPct(revenue.delta_pct)}</span>}
          {revenue && <span className="fi-overview-sub">{periodLabel(revenue.period_id)}</span>}
        </div>
        <div className="fi-overview-tile">
          <span className="fi-overview-label">Operating Income</span>
          <span className="fi-overview-value mono">{opIncome ? fmtValue(opIncome.value) : "\u2014"}</span>
          {opIncome && opIncome.delta_pct && <span className={`fi-overview-delta ${(parseNum(opIncome.delta_pct) ?? 0) >= 0 ? "pos" : "neg"}`}>{fmtPct(opIncome.delta_pct)}</span>}
          {opIncome && <span className="fi-overview-sub">{periodLabel(opIncome.period_id)}</span>}
        </div>
        <div className="fi-overview-tile">
          <span className="fi-overview-label">Net Income</span>
          <span className="fi-overview-value mono">{netIncome ? fmtValue(netIncome.value) : "\u2014"}</span>
          {netIncome && netIncome.delta_pct && <span className={`fi-overview-delta ${(parseNum(netIncome.delta_pct) ?? 0) >= 0 ? "pos" : "neg"}`}>{fmtPct(netIncome.delta_pct)}</span>}
          {netIncome && <span className="fi-overview-sub">{periodLabel(netIncome.period_id)}</span>}
        </div>
        <div className="fi-overview-tile">
          <span className="fi-overview-label">{opMargin ? formatLabel(opMargin.metric) : "Operating Margin"}</span>
          <span className="fi-overview-value mono">{opMargin ? fmtRatio(opMargin.value) : "\u2014"}</span>
          {opMargin && opMargin.delta_pct && <span className={`fi-overview-delta ${(parseNum(opMargin.delta_pct) ?? 0) >= 0 ? "pos" : "neg"}`}>{fmtPct(opMargin.delta_pct)}</span>}
          {opMargin && <span className="fi-overview-sub">{periodLabel(opMargin.period_id)}</span>}
        </div>
        <div className="fi-overview-tile">
          <span className="fi-overview-label">Operating Cash Flow</span>
          <span className="fi-overview-value mono">{cfo ? fmtValue(cfo.value) : "\u2014"}</span>
          {cfo && <span className="fi-overview-sub">{periodLabel(cfo.period_id)}</span>}
        </div>
        <div className="fi-overview-tile">
          <span className="fi-overview-label">Free Cash Flow</span>
          <span className="fi-overview-value mono">{fcf ? fmtValue(fcf.value) : "\u2014"}</span>
          {fcf && <span className="fi-overview-sub">{periodLabel(fcf.period_id)}</span>}
        </div>
      </div>
    </Section>
  )
}

/* ── Fundamentals Table ───────────────────────────────────────────────── */

function FundamentalsTable({
  observations,
  candidates,
  label,
  scale = "currency",
}: {
  observations: DeepMetricObservation[]
  candidates: string[]
  label: string
  scale?: "currency" | "ratio"
}) {
  const matching = getMetricGroup(observations, candidates).filter((o) => o.value !== null)
  if (matching.length === 0) return null

  const byPeriod = new Map<string, DeepMetricObservation[]>()
  for (const obs of matching) {
    const list = byPeriod.get(obs.period_id) ?? []
    list.push(obs)
    byPeriod.set(obs.period_id, list)
  }

  const periods = [...byPeriod.keys()].sort()

  return (
    <Section title={label} className="fi-table-section">
      <div className="fi-table-wrap">
        <table className="fi-table">
          <thead>
            <tr>
              <th>Metric</th>
              {periods.map((p) => (
                <th key={p}>{periodLabel(p)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[...new Set(matching.map((o) => o.metric))].map((metric) => {
              const metricObs = matching.filter((o) => o.metric === metric)
              return (
                <tr key={metric}>
                  <td className="fi-table-metric">
                    {formatLabel(metric)}
                    {metricObs.some((o) => o.observation_type === "DERIVED") && (
                      <Tag text="Derived" tone="blue" />
                    )}
                  </td>
                  {periods.map((p) => {
                    const obs = metricObs.find((o) => o.period_id === p)
                    return (
                      <td key={p} className="mono">
                        {obs ? (
                          <span className="fi-table-cell">
                            {scale === "ratio" ? fmtRatio(obs.value) : fmtValue(obs.value)}
                            {obs.delta_pct && (
                              <span className={`fi-table-delta ${(parseNum(obs.delta_pct) ?? 0) >= 0 ? "pos" : "neg"}`}>
                                {fmtPct(obs.delta_pct)}
                              </span>
                            )}
                          </span>
                        ) : "\u2014"}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Section>
  )
}

/* ── Balance Sheet Section ────────────────────────────────────────────── */

function BalanceSheetSection({ observations }: { observations: DeepMetricObservation[] }) {
  const groups = [
    { label: "Cash & Equivalents", candidates: BALANCE_CASH },
    { label: "Total Debt", candidates: BALANCE_DEBT },
    { label: "Total Equity", candidates: BALANCE_EQUITY },
    { label: "Accounts Receivable", candidates: BALANCE_RECEIVABLES },
    { label: "Inventory", candidates: BALANCE_INVENTORY },
    { label: "Accounts Payable", candidates: BALANCE_PAYABLES },
  ]

  const hasAny = groups.some((g) => findObs(observations, g.candidates))
  if (!hasAny) return null

  return (
    <Section title="Balance sheet" className="fi-balance-sheet">
      <div className="fi-balance-grid">
        {groups.map((g) => {
          const obs = findObs(observations, g.candidates)
          return (
            <div key={g.label} className="fi-balance-tile">
              <span className="fi-balance-label">{g.label}</span>
              <span className="fi-balance-value mono">{obs ? fmtValue(obs.value) : "\u2014"}</span>
              {obs && obs.delta_pct && (
                <span className={`fi-balance-delta ${(parseNum(obs.delta_pct) ?? 0) >= 0 ? "pos" : "neg"}`}>
                  {fmtPct(obs.delta_pct)}
                </span>
              )}
              {obs && <span className="fi-balance-sub">{periodLabel(obs.period_id)}</span>}
            </div>
          )
        })}
      </div>
    </Section>
  )
}

/* ── Financial Observations ───────────────────────────────────────────── */

function FinancialObservations({ observations }: { observations: DeepMetricObservation[] }) {
  const anomalies = observations.filter((o) => o.observation_type === "DERIVED" && o.derivation)
  const unavailable = observations.filter((o) => o.observation_type === "UNAVAILABLE")
  const improving = observations.filter((o) => o.delta_pct !== null && parseNum(o.delta_pct) !== null && parseNum(o.delta_pct)! > 0 && !matchMetric(o, MARGIN_METRICS))
  const deteriorating = observations.filter((o) => o.delta_pct !== null && parseNum(o.delta_pct) !== null && parseNum(o.delta_pct)! < 0 && !matchMetric(o, MARGIN_METRICS))

  return (
    <Section title="Financial observations" className="fi-observations-section">

      {improving.length > 0 && (
        <div className="fi-obs-group">
          <div className="fi-obs-group-head">
            <ArrowUpRight size={13} />
            <strong>Improving Trends</strong>
            <span>{improving.length} metrics with positive change</span>
          </div>
          <div className="fi-obs-list">
            {improving.slice(0, 10).map((obs) => (
              <div key={obs.observation_id} className="fi-obs-row">
                <span className="fi-obs-metric">{formatLabel(obs.metric)}</span>
                <span className="fi-obs-change pos mono">{fmtPct(obs.delta_pct)}</span>
                <span className="fi-obs-period">{periodLabel(obs.period_id)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {deteriorating.length > 0 && (
        <div className="fi-obs-group">
          <div className="fi-obs-group-head">
            <ArrowDownRight size={13} />
            <strong>Deteriorating Trends</strong>
            <span>{deteriorating.length} metrics with negative change</span>
          </div>
          <div className="fi-obs-list">
            {deteriorating.slice(0, 10).map((obs) => (
              <div key={obs.observation_id} className="fi-obs-row">
                <span className="fi-obs-metric">{formatLabel(obs.metric)}</span>
                <span className="fi-obs-change neg mono">{fmtPct(obs.delta_pct)}</span>
                <span className="fi-obs-period">{periodLabel(obs.period_id)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {anomalies.length > 0 && (
        <div className="fi-obs-group">
          <div className="fi-obs-group-head">
            <Minus size={13} />
            <strong>Derived Observations</strong>
            <span>{anomalies.length} calculated metrics</span>
          </div>
          <div className="fi-obs-list">
            {anomalies.slice(0, 10).map((obs) => (
              <div key={obs.observation_id} className="fi-obs-row">
                <span className="fi-obs-metric">{formatLabel(obs.metric)}</span>
                <Tag text="Derived" tone="blue" />
                {obs.derivation && <span className="fi-obs-derivation">{obs.derivation}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {unavailable.length > 0 && (
        <div className="fi-obs-group">
          <div className="fi-obs-group-head">
            <FileSearch size={13} />
            <strong>Unavailable Data</strong>
            <span>{unavailable.length} metrics not available</span>
          </div>
          <div className="fi-obs-list">
            {unavailable.slice(0, 10).map((obs) => (
              <div key={obs.observation_id} className="fi-obs-row">
                <span className="fi-obs-metric">{formatLabel(obs.metric)}</span>
                <Tag text="Unavailable" tone="slate" />
                <span className="fi-obs-period">{periodLabel(obs.period_id)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {improving.length === 0 && deteriorating.length === 0 && anomalies.length === 0 && unavailable.length === 0 && (
        <div className="fi-empty-obs">
          No financial observations to display.
        </div>
      )}
    </Section>
  )
}

/* ── Main Component ──────────────────────────────────────────────────── */

export default function FinancialIntelligencePage() {
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)
  const [research, setResearch] = useState<CompanyResearch | null>(null)
  const [researchLoading, setResearchLoading] = useState(false)
  const [researchError, setResearchError] = useState<string | null>(null)
  const [periodBasis, setPeriodBasis] = useState<"all" | "annual" | "quarterly">("annual")
  const [showAllObs, setShowAllObs] = useState(false)
  const [chartView, setChartView] = useState<"revenue" | "profitability" | "margins">("revenue")

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

  const researchable = useMemo(
    () => items.filter((i) => i.research_available),
    [items],
  )

  const filteredCompanies = useMemo(() => {
    const q = query.toLowerCase()
    if (!q) return researchable
    return researchable.filter(
      (i) =>
        i.symbol.toLowerCase().includes(q) ||
        (i.company_name ?? "").toLowerCase().includes(q) ||
        i.sector.toLowerCase().includes(q),
    )
  }, [researchable, query])

  const loadResearch = useCallback(async (sym: string) => {
    setSelectedSymbol(sym)
    setResearch(null)
    setResearchLoading(true)
    setResearchError(null)
    setShowAllObs(false)
    try {
      const result = await fetchResearch(sym)
      setResearch(result)
    } catch (err) {
      setResearchError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error ? err.message : "Failed to load research",
      )
    } finally {
      setResearchLoading(false)
    }
  }, [])

  const insights = research?.deep_financial_insights
  const reported = useMemo(
    () => insights?.observations.filter((o) => o.observation_type === "REPORTED") ?? [],
    [insights],
  )
  const derived = useMemo(
    () => insights?.observations.filter((o) => o.observation_type === "DERIVED") ?? [],
    [insights],
  )
  const unavailable = useMemo(
    () => insights?.observations.filter((o) => o.observation_type === "UNAVAILABLE") ?? [],
    [insights],
  )

  /* ── Period-basis scoping ───────────────────────────────────────────
     Annual and quarterly results are not directly comparable, so every
     analytical section draws from one coherent basis. ───────────────── */
  const scopedObservations = useMemo(() => {
    if (!insights) return []
    if (periodBasis === "all") return insights.observations
    return insights.observations.filter((o) => periodType(o.period_id) === periodBasis)
  }, [insights, periodBasis])

  /* ── Chart data: group observations by canonical series → period ──── */
  const chartData = useMemo(() => {
    const observations = scopedObservations.filter((o) => o.value !== null)
    const allPeriods = [...new Set(observations.map((o) => o.period_id))].sort()

    /**
     * Rows are keyed by canonical series names so every backend alias
     * ("total_revenue", "profit_after_tax", …) feeds the matching line;
     * otherwise lines silently disappear whenever naming differs. Exact
     * alias matches win over loose substring matches.
     */
    function pickSeries(periodObs: DeepMetricObservation[], aliases: string[]): DeepMetricObservation | undefined {
      for (const alias of aliases) {
        const exact = periodObs.find((o) => o.metric.toLowerCase() === alias.toLowerCase())
        if (exact) return exact
      }
      for (const alias of aliases) {
        const loose = periodObs.find((o) => matchMetric(o, [alias]))
        if (loose) return loose
      }
      return undefined
    }

    function buildChartData(
      seriesDefs: Array<{ canonical: string; aliases: string[] }>,
      scale: "currency" | "pct" = "currency",
    ) {
      return allPeriods.map((period) => {
        const row: Record<string, string | number | null> = { period: periodLabel(period, "short") }
        const periodObs = observations.filter((o) => o.period_id === period)
        for (const def of seriesDefs) {
          const obs = pickSeries(periodObs, def.aliases)
          // Charts plot crore-scale values so axis ticks stay compact and
          // consistent with the "₹ crore" unit label.
          if (obs && obs.value !== null) {
            row[def.canonical] = scale === "pct" ? parseNum(obs.value) : toCrore(obs.value)
          }
        }
        return row
      }).filter((row) => {
        const keys = Object.keys(row).filter((k) => k !== "period")
        return keys.some((k) => row[k] !== null && row[k] !== undefined)
      })
    }

    return {
      revenue: buildChartData([{ canonical: "revenue", aliases: REVENUE_METRICS }]),
      profit: buildChartData([
        { canonical: "operating_income", aliases: OPERATING_INCOME_METRICS },
        { canonical: "net_income", aliases: NET_INCOME_METRICS },
      ]),
      margin: buildChartData(
        [
          { canonical: "operating_margin", aliases: ["operating_margin"] },
          { canonical: "net_margin", aliases: ["net_margin"] },
          { canonical: "gross_margin", aliases: ["gross_margin"] },
        ],
        "pct",
      ),
    }
  }, [scopedObservations])

  return (
    <div className="page-financial-intelligence">
      <section className="page-hero">
        <p className="page-kicker">Research</p>
        <h1>Financial Intelligence</h1>
        <p className="page-subtitle">
          Deep financial research: revenue trends, profitability, margins, cash flow, balance sheet.
          Each observation includes source provenance and period context. No scores or rankings.
        </p>
      </section>

      {loading && (
        <LoadingState label="Loading financial data" />
      )}

      {error && (
        <ErrorState error={error} />
      )}

      {!loading && !error && (
        <div className="fi-layout">
          {/* LEFT: Company selector */}
          <div className="fi-sidebar">
            <div className="panel">
              <div className="panel-head">
                <h3>Select Company</h3>
                <span>{researchable.length} companies</span>
              </div>
              <div className="fi-search">
                <Search size={14} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Filter companies..."
                  aria-label="Filter companies"
                />
              </div>
              <div className="fi-company-list">
                {filteredCompanies.map((item) => (
                  <button
                    key={item.symbol}
                    className={`fi-company-item ${selectedSymbol === item.symbol ? "active" : ""}`}
                    onClick={() => void loadResearch(item.symbol)}
                  >
                    <TrendingUp size={13} />
                    <div>
                      <strong>{item.symbol}</strong>
                      <small>{item.company_name ?? item.symbol}</small>
                    </div>
                  </button>
                ))}
                {filteredCompanies.length === 0 && (
                  <div className="fi-empty-list">
                    <Search size={14} />
                    <span>No matching companies</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* RIGHT: Financial intelligence content */}
          <div className="fi-content">
            {!selectedSymbol && (
              <EmptyState title="Select a company" description="Choose a company from the list to view its deep financial observations." />
            )}

            {selectedSymbol && researchLoading && (
              <LoadingState label={`Fetching financial data for ${selectedSymbol}...`} />
            )}

            {selectedSymbol && researchError && (
              <ErrorState error={researchError} />
            )}

            {selectedSymbol && research && !researchLoading && (
              <>
                {!insights ? (
                  <EmptyState title="No deep financial data" description={`No deep financial insights are available for ${selectedSymbol}.`} />
                ) : (
                  <>
                    {/* ── 1. FINANCIAL CONTEXT ──────────────────────────── */}
                    <Section title="Financial context" subtitle="Comparability notes and data coverage for this company">
                      {insights.comparability_notes.length > 0 ? (
                        <div className="fi-comparability">
                          {insights.comparability_notes.map((note, i) => (
                            <div className="fi-comparability-note" key={i}>
                              <span>{note}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="fi-comparability-note"><span>No comparability issues recorded.</span></div>
                      )}
                      <div className="fi-context-meta">
                        <span>{insights.series.length} series</span>
                        <span>{insights.observations.length} observations</span>
                        <span>{reported.length} reported</span>
                        <span>{derived.length} derived</span>
                        {unavailable.length > 0 && <span>{unavailable.length} unavailable</span>}
                      </div>
                    </Section>

                    {/* ── 2. LATEST SNAPSHOT ────────────────────────────── */}
                    <FinancialOverview
                      observations={scopedObservations}
                      periodEnds={insights.series[0]?.period_ends ?? []}
                    />

                    {/* ── 3. HISTORICAL PERFORMANCE ──────────────────────── */}
                    {chartData.revenue.length > 0 && (
                      <Section title="Historical performance" subtitle="Trend analysis across recorded periods">
                        <div className="fi-chart-controls">
                          <div className="filter-chips" role="group" aria-label="Chart view">
                            {(["revenue", "profitability", "margins"] as const).map((value) => (
                              <button
                                key={value}
                                type="button"
                                className={chartView === value ? "filter-chip active" : "filter-chip"}
                                onClick={() => setChartView(value)}
                                aria-pressed={chartView === value}
                              >
                                {value.charAt(0).toUpperCase() + value.slice(1)}
                              </button>
                            ))}
                          </div>
                        </div>
                        {chartView === "revenue" && chartData.revenue.length > 0 && (
                          <TrendChart title="Revenue Trend" data={chartData.revenue} lines={[{ key: "revenue", color: CHART.primary, label: "Revenue" }]} unit="currency" />
                        )}
                        {chartView === "profitability" && chartData.profit.length > 0 && (
                          <TrendChart title="Profitability Trend" data={chartData.profit} lines={[{ key: "operating_income", color: CHART.primary, label: "Operating Income" }, { key: "net_income", color: CHART.positive, label: "Net Income" }]} unit="currency" />
                        )}
                        {chartView === "margins" && chartData.margin.length > 0 && (
                          <TrendChart title="Margin Trend" data={chartData.margin} lines={[{ key: "operating_margin", color: CHART.primary, label: "Operating Margin" }, { key: "net_margin", color: CHART.positive, label: "Net Margin" }, { key: "gross_margin", color: CHART.amber, label: "Gross Margin" }]} unit="pct" />
                        )}
                      </Section>
                    )}

                    {/* ── 4. REPORTED FINANCIAL HISTORY ─────────────────── */}
                    <FundamentalsTable
                      observations={scopedObservations}
                      candidates={REVENUE_METRICS}
                      label="Revenue"
                    />
                    <FundamentalsTable
                      observations={scopedObservations}
                      candidates={[...OPERATING_INCOME_METRICS, ...NET_INCOME_METRICS]}
                      label="Profitability"
                    />
                    <FundamentalsTable
                      observations={scopedObservations}
                      candidates={[...CASH_FLOW_METRICS, ...CAPEX_METRICS]}
                      label="Cash flow"
                    />
                    <BalanceSheetSection observations={scopedObservations} />

                    {/* ── 5. DERIVED METRICS ────────────────────────────── */}
                    {derived.length > 0 && (
                      <Section title="Derived metrics" subtitle="Calculated from reported values">
                        <div className="fi-obs-list">
                          {derived.slice(0, showAllObs ? derived.length : 10).map((obs) => (
                            <div key={obs.observation_id} className="fi-obs-row">
                              <span className="fi-obs-metric">{formatLabel(obs.metric)}</span>
                              <span className="fi-obs-value mono">{fmtObsValue(obs, obs.value)}</span>
                              {obs.derivation && <span className="fi-obs-derivation">{obs.derivation}</span>}
                              <Tag text={periodLabel(obs.period_id)} tone="slate" />
                            </div>
                          ))}
                        </div>
                        {derived.length > 10 && (
                          <button type="button" className="refresh-button" onClick={() => setShowAllObs((v) => !v)}>
                            {showAllObs ? "Show fewer" : `Show all ${derived.length} derived metrics`}
                          </button>
                        )}
                      </Section>
                    )}

                    {/* ── 6. RESEARCH OBSERVATIONS ──────────────────────── */}
                    <FinancialObservations observations={scopedObservations} />

                    {/* ── 7. FINANCIAL TENSIONS ─────────────────────────── */}
                    {(() => {
                      const improving = scopedObservations.filter((o) => o.delta_pct !== null && parseNum(o.delta_pct) !== null && parseNum(o.delta_pct)! > 0 && !matchMetric(o, MARGIN_METRICS))
                      const deteriorating = scopedObservations.filter((o) => o.delta_pct !== null && parseNum(o.delta_pct) !== null && parseNum(o.delta_pct)! < 0 && !matchMetric(o, MARGIN_METRICS))
                      const hasTensions = improving.length > 0 && deteriorating.length > 0
                      if (!hasTensions) return null
                      return (
                        <Section title="Financial tensions" subtitle="Conflicting signals across metrics — evidence of mixed trajectory">
                          <div className="fi-tensions-grid">
                            <div className="fi-tension-col">
                              <div className="fi-tension-head pos">
                                <ArrowUpRight size={13} />
                                <strong>Improving</strong>
                                <span>{improving.length} metrics</span>
                              </div>
                              <div className="fi-obs-list">
                                {improving.slice(0, 6).map((obs) => (
                                  <div key={obs.observation_id} className="fi-obs-row">
                                    <span className="fi-obs-metric">{formatLabel(obs.metric)}</span>
                                    <span className="fi-obs-change pos mono">{fmtPct(obs.delta_pct)}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                            <div className="fi-tension-col">
                              <div className="fi-tension-head neg">
                                <ArrowDownRight size={13} />
                                <strong>Deteriorating</strong>
                                <span>{deteriorating.length} metrics</span>
                              </div>
                              <div className="fi-obs-list">
                                {deteriorating.slice(0, 6).map((obs) => (
                                  <div key={obs.observation_id} className="fi-obs-row">
                                    <span className="fi-obs-metric">{formatLabel(obs.metric)}</span>
                                    <span className="fi-obs-change neg mono">{fmtPct(obs.delta_pct)}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        </Section>
                      )
                    })()}

                    {/* ── 8. FULL OBSERVATION RECORD ────────────────────── */}
                    {scopedObservations.length > 0 && (
                      <Section title="Full observation record" meta={<span>{pluralize(scopedObservations.length, "data point")}</span>}>
                        <div className="fi-period-controls">
                          <span className="fi-period-label">Period basis</span>
                          <div className="filter-chips" role="group" aria-label="Period basis">
                            {([
                              ["annual", "Annual"],
                              ["quarterly", "Quarterly"],
                              ["all", "All"],
                            ] as const).map(([value, label]) => (
                              <button
                                key={value}
                                type="button"
                                className={periodBasis === value ? "filter-chip active" : "filter-chip"}
                                onClick={() => setPeriodBasis(value)}
                                aria-pressed={periodBasis === value}
                              >
                                {label}
                              </button>
                            ))}
                          </div>
                        </div>
                        {scopedObservations.length === 0 && insights.observations.length > 0 && (
                          <div className="fi-empty-obs">
                            No {periodBasis === "quarterly" ? "quarterly" : "annual"}-basis observations recorded
                            for this company yet — switch the period basis above.
                          </div>
                        )}
                        <div className="fi-observations">
                          {(showAllObs ? scopedObservations : scopedObservations.slice(0, OBS_PREVIEW_COUNT)).map((obs) => (
                            <div key={obs.observation_id} className="obs-row">
                              <div className="obs-head">
                                <strong>{formatLabel(obs.metric)}</strong>
                                <Tag text={formatLabel(obs.observation_type)} tone={observationTypeTone(obs.observation_type)} />
                                <Tag text={periodLabel(obs.period_id)} tone="slate" />
                              </div>
                              <div className="obs-values">
                                <span className="obs-value-item">
                                  <span className="obs-value-label">Current</span>
                                  <span className="obs-value-data mono">{fmtObsValue(obs, obs.value)}</span>
                                </span>
                                <span className="obs-value-item">
                                  <span className="obs-value-label">Previous</span>
                                  <span className="obs-value-data mono">{fmtObsValue(obs, obs.previous_value)}</span>
                                </span>
                                {obs.delta !== null && obs.delta_pct !== null ? (
                                  <span className="obs-value-item">
                                    <span className="obs-value-label">Change</span>
                                    <span className="obs-value-data mono">
                                      {isRatioMetric(obs)
                                        ? fmtPct(obs.delta_pct)
                                        : `${fmtValue(obs.delta)} (${fmtPct(obs.delta_pct)})`}
                                    </span>
                                  </span>
                                ) : null}
                              </div>
                              {obs.derivation ? (
                                <div className="obs-derivation">
                                  <span className="obs-derivation-label">Derivation:</span>
                                  <span className="obs-derivation-text mono">{obs.derivation}</span>
                                </div>
                              ) : null}
                              <div className="obs-meta">
                                {obs.published_at && <span>Published {formatIso(obs.published_at)}</span>}
                                {obs.available_at && <span>Available {formatIso(obs.available_at)}</span>}
                                {obs.provenance_id && <span>Provenance recorded</span>}
                              </div>
                            </div>
                          ))}
                        </div>
                        {scopedObservations.length > OBS_PREVIEW_COUNT && (
                          <button
                            type="button"
                            className="refresh-button"
                            onClick={() => setShowAllObs((v) => !v)}
                          >
                            {showAllObs
                              ? "Show fewer"
                              : `Show all ${pluralize(scopedObservations.length, "observation")}`}
                          </button>
                        )}
                      </Section>
                    )}

                    {/* ── 9. SOURCE / PIT ──────────────────────────────── */}
                    <Section title="Source and point-in-time" subtitle="Data provenance and freshness">
                      <div className="fi-source-grid">
                        <div className="fi-source-item">
                          <span className="fi-source-label">Observations</span>
                          <span className="fi-source-value mono">{insights.observations.length}</span>
                        </div>
                        <div className="fi-source-item">
                          <span className="fi-source-label">Series</span>
                          <span className="fi-source-value mono">{insights.series.length}</span>
                        </div>
                        <div className="fi-source-item">
                          <span className="fi-source-label">Reported</span>
                          <span className="fi-source-value mono">{reported.length}</span>
                        </div>
                        <div className="fi-source-item">
                          <span className="fi-source-label">Derived</span>
                          <span className="fi-source-value mono">{derived.length}</span>
                        </div>
                        <div className="fi-source-item">
                          <span className="fi-source-label">Unavailable</span>
                          <span className="fi-source-value mono">{unavailable.length}</span>
                        </div>
                      </div>
                      <div className="fi-note">
                        <span>
                          Each observation includes source provenance and period context.
                          Derived metrics are calculated from reported values. No scores, no rankings.
                        </span>
                      </div>
                    </Section>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
