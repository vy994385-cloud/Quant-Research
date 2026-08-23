/**
 * Market Intelligence page.
 * Focuses on observed market behavior: returns, 52-week context,
 * trend/volatility regimes, volume, drawdowns, gaps, divergence.
 *
 * Does NOT duplicate TechnicalPage (RSI/MACD/Bollinger/ADX/ATR/pivots/MAs).
 */

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  Activity,
  FileSearch,
  Search,
  TrendingUp,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  AlertTriangle,
} from "lucide-react"
import { fetchDiscovery, fetchDeepTechnicals, fetchResearch } from "../api/client"
import { ApiError } from "../api/client"
import type {
  CompanyDeepTechnicalResponse,
  CompanyResearch,
  DeepTechnicalResult,
  DiscoveryItem,
  TechnicalIndicatorSet,
} from "../api/types"
import { formatIso, formatLabel } from "../lib/format"
import { Tag } from "../components/ui"
import { DataStatus } from "../components/ResearchPrimitives"
import type { DataAvailability } from "../components/ResearchPrimitives"

/* ── Helpers ──────────────────────────────────────────────────────────── */

function parseNum(v: string | null | undefined): number | null {
  if (v === null || v === undefined) return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

function fmtPct(v: string | null | undefined): string {
  const n = parseNum(v)
  if (n === null) return "\u2014"
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`
}

/** Missing percentages stay neutral — only real values carry direction. */
function pctClass(v: string | null | undefined): "" | "pos" | "neg" {
  const n = parseNum(v)
  if (n === null) return ""
  return n >= 0 ? "pos" : "neg"
}

function fmtVal(v: string | null | undefined): string {
  if (v === null || v === undefined) return "\u2014"
  const n = parseNum(v)
  if (n === null) return v
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 })
}

function regimeTone(r: string | null | undefined): "green" | "red" | "amber" | "slate" {
  if (!r) return "slate"
  const up = r.toUpperCase()
  if (up.includes("UP") || up === "UPTREND") return "green"
  if (up.includes("DOWN") || up === "DOWNTREND") return "red"
  return "amber"
}

function availabilityFor(v: string | null | undefined): DataAvailability {
  if (v === null || v === undefined) return "missing"
  const n = parseNum(v)
  if (n !== null && !Number.isNaN(n)) return "available"
  return "partial"
}

/* ── Market Metric Row ────────────────────────────────────────────────── */

function MarketMetric({
  label,
  value,
  pct,
  regime,
  availability,
}: {
  label: string
  value: string | null | undefined
  pct?: string | null
  regime?: string | null
  availability?: DataAvailability
}) {
  const avail = availability ?? availabilityFor(value)
  return (
    <div className="mi-metric">
      <div className="mi-metric-head">
        <span className="mi-metric-label">{label}</span>
        <DataStatus availability={avail} />
      </div>
      <div className="mi-metric-body">
        <span className="mi-metric-value mono">{fmtVal(value)}</span>
        {pct !== undefined && (
          <span className={`mi-metric-pct ${pctClass(pct)}`}>
            {fmtPct(pct)}
          </span>
        )}
        {regime && <Tag text={formatLabel(regime)} tone={regimeTone(regime)} />}
      </div>
    </div>
  )
}

/* ── Section Card ─────────────────────────────────────────────────────── */

function SectionCard({
  id,
  title,
  subtitle,
  children,
}: {
  id: string
  title: string
  subtitle?: string
  children: React.ReactNode
}) {
  return (
    <section id={id} className="mi-section">
      <div className="mi-section-head">
        <h3>{title}</h3>
        {subtitle && <span>{subtitle}</span>}
      </div>
      <div className="mi-section-body">{children}</div>
    </section>
  )
}

/* ── Returns Bar ──────────────────────────────────────────────────────── */

function ReturnBar({
  label,
  value,
}: {
  label: string
  value: string | null | undefined
}) {
  const n = parseNum(value)
  const avail = availabilityFor(value)
  const width = n !== null ? Math.min(Math.abs(n) * 4, 100) : 0
  const isPos = n !== null && n >= 0

  return (
    <div className="mi-return-row">
      <span className="mi-return-label">{label}</span>
      <div className="mi-return-bar-wrap">
        <div className="mi-return-bar-track">
          {n !== null && (
            <div
              className={`mi-return-bar ${isPos ? "pos" : "neg"}`}
              style={{ width: `${width}%` }}
            />
          )}
        </div>
      </div>
      <span className={`mi-return-value mono ${avail === "missing" ? "unavail" : ""}`}>
        {avail === "missing" ? "\u2014" : fmtPct(value)}
      </span>
    </div>
  )
}

/* ── Gap Indicator ────────────────────────────────────────────────────── */

function GapIndicator({
  gapType,
  gapPct,
}: {
  gapType: string | null | undefined
  gapPct: string | null | undefined
}) {
  const hasGap = gapType && gapType !== "NONE" && gapType !== "none"
  if (!hasGap) return null
  const isUp = (gapType ?? "").toUpperCase().includes("UP")
  return (
    <div className={`mi-gap ${isUp ? "up" : "down"}`}>
      {isUp ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
      <span>
        {formatLabel(gapType)} gap of {fmtPct(gapPct)}
      </span>
    </div>
  )
}

/* ── Observation Text List ────────────────────────────────────────────── */

function ObservationTextList({ observations }: { observations: string[] }) {
  if (observations.length === 0) return null
  return (
    <div className="mi-obs-text-list">
      {observations.map((obs, i) => (
        <div key={i} className="mi-obs-text-row">
          <span className="mi-obs-text-bullet" />
          <span>{obs}</span>
        </div>
      ))}
    </div>
  )
}

/* ── Main Component ──────────────────────────────────────────────────── */

export default function MarketIntelligencePage() {
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)
  const [techData, setTechData] = useState<CompanyDeepTechnicalResponse | null>(null)
  const [researchData, setResearchData] = useState<CompanyResearch | null>(null)
  const [dataLoading, setDataLoading] = useState(false)
  const [dataError, setDataError] = useState<string | null>(null)

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

  const loadCompany = useCallback(async (sym: string) => {
    setSelectedSymbol(sym)
    setTechData(null)
    setResearchData(null)
    setDataLoading(true)
    setDataError(null)
    try {
      const [tech, research] = await Promise.all([
        fetchDeepTechnicals(sym),
        fetchResearch(sym),
      ])
      setTechData(tech)
      setResearchData(research)
    } catch (err) {
      setDataError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error ? err.message : "Failed to load market data",
      )
    } finally {
      setDataLoading(false)
    }
  }, [])

  const tech: DeepTechnicalResult | null = techData?.deep_technicals ?? null
  const ind: TechnicalIndicatorSet | null = tech?.indicators ?? null
  const marketObs = researchData?.intelligence?.market_intelligence?.observations ?? []

  return (
    <div className="page-market-intelligence">
      <section className="page-hero">
        <h1>Market Intelligence</h1>
        <p className="page-subtitle">
          Observed market behavior: price movement, returns, trend and volatility regimes,
          volume activity, drawdowns, and gap events. No scores, no recommendations, no trade signals.
        </p>
      </section>

      {loading && (
        <div className="loading-state" role="status">
          <Activity className="spin" size={26} />
          <strong>Loading market data</strong>
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
                    onClick={() => void loadCompany(item.symbol)}
                  >
                    <BarChart3 size={13} />
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

          {/* RIGHT: Market intelligence content */}
          <div className="fi-content">
            {!selectedSymbol && (
              <div className="empty-state">
                <BarChart3 size={28} />
                <strong>Select a company</strong>
                <p>Choose a company from the list to view market intelligence.</p>
              </div>
            )}

            {selectedSymbol && dataLoading && (
              <div className="loading-state" role="status">
                <Activity className="spin" size={26} />
                <strong>Loading market data</strong>
                <span>Fetching market observations for {selectedSymbol}...</span>
              </div>
            )}

            {selectedSymbol && dataError && (
              <div className="empty-state error" role="alert">
                <FileSearch size={28} />
                <strong>Market data unavailable</strong>
                <p>{dataError}</p>
                <p className="error-hint">
                  Market observations could not be produced for {selectedSymbol}. The rest of
                  the research record for this company is unaffected.
                </p>
              </div>
            )}

            {selectedSymbol && !dataLoading && !dataError && !ind && (
              <div className="empty-state">
                <BarChart3 size={28} />
                <strong>No market data available</strong>
                <p>No market observations are available for {selectedSymbol}.</p>
              </div>
            )}

            {selectedSymbol && ind && !dataLoading && (
              <>
                {/* Header */}
                <div className="mi-header">
                  <div className="mi-header-row">
                    <span><strong>{tech?.symbol}</strong></span>
                    <span>Trading date: {formatIso(tech?.trading_date ?? "")}</span>
                    <span>As-of: {formatIso(tech?.as_of ?? "")}</span>
                    {tech && <span>{tech.bars_used} bars analyzed</span>}
                  </div>
                </div>

                {/* 1. MARKET OVERVIEW */}
                <SectionCard id="overview" title="Market Overview" subtitle="Price context and key market metrics">
                  <div className="mi-overview-grid">
                    <MarketMetric label="52-Week High" value={ind.high_52w} />
                    <MarketMetric label="52-Week Low" value={ind.low_52w} />
                    <MarketMetric label="% From 52W High" value={ind.pct_from_52w_high} />
                    <MarketMetric label="% From 52W Low" value={ind.pct_from_52w_low} />
                    <MarketMetric label="Trend Regime" value={ind.regime} regime={ind.regime} />
                    <MarketMetric label="Trend Strength" value={ind.trend_strength} />
                    <MarketMetric label="Volatility (ATR %)" value={ind.atr_pct} />
                    <MarketMetric label="Current Drawdown" value={ind.current_drawdown} />
                  </div>
                </SectionCard>

                {/* 2. RETURNS */}
                <SectionCard id="returns" title="Period Returns" subtitle="Observed price changes over multiple time horizons">
                  <div className="mi-returns-section">
                    <ReturnBar label="1-Day" value={ind.return_1d} />
                    <ReturnBar label="5-Day" value={ind.return_5d} />
                    <ReturnBar label="10-Day" value={ind.return_10d} />
                    <ReturnBar label="20-Day" value={ind.return_20d} />
                    <ReturnBar label="50-Day" value={ind.return_50d} />
                    <ReturnBar label="100-Day" value={ind.return_100d} />
                    <ReturnBar label="200-Day" value={ind.return_200d} />
                  </div>
                </SectionCard>

                {/* 3. TREND & VOLATILITY CONTEXT */}
                <SectionCard id="trend-volatility" title="Trend & Volatility" subtitle="Regime classification and trend assessment">
                  <div className="mi-trend-vol-grid">
                    <div className="mi-trend-vol-card">
                      <div className="mi-trend-vol-head">
                        <TrendingUp size={14} />
                        <span>Trend</span>
                      </div>
                      <div className="mi-trend-vol-body">
                        <div className="mi-trend-vol-row">
                          <span>Regime</span>
                          <Tag text={ind.regime ? formatLabel(ind.regime) : "Unknown"} tone={regimeTone(ind.regime)} />
                        </div>
                        <div className="mi-trend-vol-row">
                          <span>Strength</span>
                          <span className="mono">{fmtVal(ind.trend_strength)}</span>
                        </div>
                        <div className="mi-trend-vol-row">
                          <span>SMA Alignment</span>
                          <span className="mono">{ind.sma_alignment ? formatLabel(ind.sma_alignment) : "\u2014"}</span>
                        </div>
                        <div className="mi-trend-vol-row">
                          <span>EMA Alignment</span>
                          <span className="mono">{ind.ema_alignment ? formatLabel(ind.ema_alignment) : "\u2014"}</span>
                        </div>
                      </div>
                    </div>
                    <div className="mi-trend-vol-card">
                      <div className="mi-trend-vol-head">
                        <BarChart3 size={14} />
                        <span>Volatility</span>
                      </div>
                      <div className="mi-trend-vol-body">
                        <div className="mi-trend-vol-row">
                          <span>ATR (14)</span>
                          <span className="mono">{fmtVal(ind.atr_14)}</span>
                        </div>
                        <div className="mi-trend-vol-row">
                          <span>ATR %</span>
                          <span className="mono">{fmtPct(ind.atr_pct)}</span>
                        </div>
                        <div className="mi-trend-vol-row">
                          <span>Bollinger Bandwidth</span>
                          <span className="mono">{fmtVal(ind.bollinger_bandwidth)}</span>
                        </div>
                        <div className="mi-trend-vol-row">
                          <span>Current Drawdown</span>
                          <span className="mono">{fmtPct(ind.current_drawdown)}</span>
                        </div>
                        <div className="mi-trend-vol-row">
                          <span>Max Drawdown (20d)</span>
                          <span className="mono">{fmtPct(ind.max_drawdown_20d)}</span>
                        </div>
                        <div className="mi-trend-vol-row">
                          <span>Recovery %</span>
                          <span className="mono">{fmtPct(ind.recovery_pct)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </SectionCard>

                {/* 4. VOLUME & ACTIVITY */}
                <SectionCard id="volume" title="Volume & Activity" subtitle="Trading volume behavior and gap events">
                  <div className="mi-volume-grid">
                    <div className="mi-volume-card">
                      <div className="mi-trend-vol-head">
                        <BarChart3 size={14} />
                        <span>Volume</span>
                      </div>
                      <div className="mi-trend-vol-body">
                        <div className="mi-trend-vol-row">
                          <span>On-Balance Volume</span>
                          <span className="mono">{ind.obv !== null ? ind.obv.toLocaleString() : "\u2014"}</span>
                        </div>
                        <div className="mi-trend-vol-row">
                          <span>MFI (14)</span>
                          <span className="mono">{fmtVal(ind.mfi_14)}</span>
                        </div>
                        <div className="mi-trend-vol-row">
                          <span>MFI Signal</span>
                          <Tag text={ind.mfi_signal ? formatLabel(ind.mfi_signal) : "Unknown"} tone={regimeTone(ind.mfi_signal)} />
                        </div>
                      </div>
                    </div>
                    <div className="mi-volume-card">
                      <div className="mi-trend-vol-head">
                        <AlertTriangle size={14} />
                        <span>Gap Events</span>
                      </div>
                      <div className="mi-trend-vol-body">
                        <GapIndicator gapType={ind.gap_type} gapPct={ind.gap_pct} />
                        {!ind.gap_type || ind.gap_type === "NONE" || ind.gap_type === "none" ? (
                          <div className="mi-trend-vol-row">
                            <span>No gap event detected</span>
                          </div>
                        ) : null}
                      </div>
                    </div>
                    <div className="mi-volume-card">
                      <div className="mi-trend-vol-head">
                        <TrendingUp size={14} />
                        <span>Divergence</span>
                      </div>
                      <div className="mi-trend-vol-body">
                        <div className="mi-trend-vol-row">
                          <span>Price-Volume</span>
                          <Tag
                            text={ind.price_volume_divergence ?? "Unknown"}
                            tone={regimeTone(ind.price_volume_divergence)}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </SectionCard>

                {/* 5. 52-WEEK CONTEXT */}
                <SectionCard id="52week" title="52-Week Context" subtitle="Distance from yearly highs and lows">
                  <div className="mi-52w-grid">
                    <div className="mi-52w-card">
                      <span className="mi-52w-label">52-Week High</span>
                      <span className="mi-52w-value mono">{fmtVal(ind.high_52w)}</span>
                      <span className={`mi-52w-delta ${parseNum(ind.pct_from_52w_high) !== null && parseNum(ind.pct_from_52w_high)! >= 0 ? "pos" : "neg"}`}>
                        {fmtPct(ind.pct_from_52w_high)}
                      </span>
                      <span className="mi-52w-note">from high</span>
                    </div>
                    <div className="mi-52w-card">
                      <span className="mi-52w-label">52-Week Low</span>
                      <span className="mi-52w-value mono">{fmtVal(ind.low_52w)}</span>
                      <span className={`mi-52w-delta ${parseNum(ind.pct_from_52w_low) !== null && parseNum(ind.pct_from_52w_low)! >= 0 ? "pos" : "neg"}`}>
                        {fmtPct(ind.pct_from_52w_low)}
                      </span>
                      <span className="mi-52w-note">from low</span>
                    </div>
                    <div className="mi-52w-card">
                      <span className="mi-52w-label">52W Signal</span>
                      <Tag text={ind.high_low_signal ? formatLabel(ind.high_low_signal) : "Unknown"} tone={regimeTone(ind.high_low_signal)} />
                    </div>
                  </div>
                </SectionCard>

                {/* 6. MARKET OBSERVATIONS (from research intelligence) */}
                {marketObs.length > 0 && (
                  <SectionCard id="observations" title="Market Observations" subtitle="Text observations from research intelligence">
                    <ObservationTextList observations={marketObs} />
                  </SectionCard>
                )}

                {/* 7. DATA QUALITY */}
                <SectionCard id="data-quality" title="Data Quality" subtitle="Availability and freshness of market data">
                  <div className="mi-data-quality">
                    <div className="mi-dq-row">
                      <span>Bars used</span>
                      <span className="mono">{tech?.bars_used ?? "\u2014"}</span>
                    </div>
                    <div className="mi-dq-row">
                      <span>Available indicators</span>
                      <span className="mono">{tech?.available_indicators.length ?? 0}</span>
                    </div>
                    {tech && tech.missing_indicators.length > 0 && (
                      <div className="mi-dq-row warn">
                        <span>Missing indicators</span>
                        <span className="mono">{tech.missing_indicators.join(", ")}</span>
                      </div>
                    )}
                    {tech && tech.notes.length > 0 && (
                      <div className="mi-dq-notes">
                        {tech.notes.map((n, i) => <span key={i}>{n}</span>)}
                      </div>
                    )}
                  </div>
                </SectionCard>

                {/* Note */}
                <div className="fi-note">
                  <BarChart3 size={13} />
                  <span>
                    Market observations are informational. Each observation reflects
                    measured market behavior over the stated period. No scores, no
                    recommendations, no trade signals. Missing data is shown explicitly.
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
