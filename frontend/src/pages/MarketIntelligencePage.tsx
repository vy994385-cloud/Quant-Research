/**
 * Market Intelligence page.
 * Focuses on observed market behavior: returns, 52-week context,
 * trend/volatility regimes, volume, drawdowns, gaps, divergence.
 *
 * Does NOT duplicate TechnicalPage (RSI/MACD/Bollinger/ADX/ATR/pivots/MAs).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  Search,
  TrendingUp,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  AlertTriangle,
} from "lucide-react"
import { fetchDiscovery, fetchDeepTechnicals, fetchPriceHistory, fetchResearch } from "../api/client"
import { ApiError } from "../api/client"
import type {
  CompanyDeepTechnicalResponse,
  CompanyResearch,
  DeepTechnicalResult,
  DiscoveryItem,
  TechnicalIndicatorSet,
  PriceHistoryResponse,
} from "../api/types"
import { formatIso, formatLabel } from "../lib/format"
import { Section, Tag } from "../components/ui"
import { LoadingState, EmptyState, ErrorState } from "../components/States"
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

function fmtCompact(v: number): string {
  const abs = Math.abs(v)
  const suffix = abs >= 1e9 ? "B" : abs >= 1e6 ? "M" : abs >= 1e3 ? "K" : ""
  const divisor = abs >= 1e9 ? 1e9 : abs >= 1e6 ? 1e6 : abs >= 1e3 ? 1e3 : 1
  return `${(v / divisor).toLocaleString("en-IN", { maximumFractionDigits: 2 })}${suffix}`
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
  unit,
}: {
  label: string
  value: string | null | undefined
  pct?: string | null
  regime?: string | null
  availability?: DataAvailability
  unit?: string
}) {
  const avail = availability ?? availabilityFor(value)
  return (
    <div className="mi-metric">
      <div className="mi-metric-head">
        <span className="mi-metric-label">{label}</span>
        <DataStatus availability={avail} />
      </div>
      <div className="mi-metric-body">
        <span className="mi-metric-value mono">{value == null ? "—" : `${fmtVal(value)}${unit ?? ""}`}</span>
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
  const normalizedGapType = (gapType ?? "").toUpperCase()
  const hasGap = Boolean(normalizedGapType && normalizedGapType !== "NONE" && normalizedGapType !== "NO_GAP")
  if (!hasGap) return null
  const isUp = (gapType ?? "").toUpperCase().includes("UP")
  return (
    <div className={`mi-gap ${isUp ? "up" : "down"}`}>
      {isUp ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
      <span>
        {formatLabel(gapType ?? "")} gap of {fmtPct(gapPct)}
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


function PriceChart({ history, loading, error }: {
  history: PriceHistoryResponse | null
  loading: boolean
  error: string | null
}) {
  const [range, setRange] = useState<"3M" | "6M" | "1Y" | "ALL">("1Y")
  const [show20, setShow20] = useState(true)
  const [show50, setShow50] = useState(true)
  const [show200, setShow200] = useState(false)

  const bars = useMemo(() => {
    const all = history?.bars ?? []
    if (range === "ALL" || all.length === 0) return all
    const days = range === "3M" ? 92 : range === "6M" ? 184 : 366
    const cutoff = new Date(all[all.length - 1].trading_date)
    cutoff.setDate(cutoff.getDate() - days)
    return all.filter((bar) => new Date(bar.trading_date) >= cutoff)
  }, [history, range])

  const series = useMemo(() => {
    const allBars = history?.bars ?? []
    const firstVisibleIndex = bars.length ? allBars.findIndex((bar) => bar.trading_date === bars[0].trading_date) : 0
    const allCloses = allBars.map((bar) => Number(bar.close))
    const closes = bars.map((bar) => Number(bar.close))
    const max = Math.max(...closes.filter(Number.isFinite))
    const min = Math.min(...closes.filter(Number.isFinite))
    const spread = max - min || 1
    const x = (index: number) => 48 + (index / Math.max(bars.length - 1, 1)) * 820
    const y = (value: number) => 18 + ((max - value) / spread) * 166
    const line = (values: Array<number | null>) => values
      .map((value, index) => value == null || !Number.isFinite(value) ? null : `${x(index)},${y(value)}`)
      .filter(Boolean).join(" ")
    const sma = (period: number) => closes.map((_, index) => {
      const endIndex = firstVisibleIndex + index
      if (endIndex + 1 < period) return null
      const window = allCloses.slice(endIndex + 1 - period, endIndex + 1)
      return window.length === period && window.every(Number.isFinite) ? window.reduce((sum, value) => sum + value, 0) / period : null
    })
    const peak = closes.map((_, index) => Math.max(...closes.slice(0, index + 1)))
    const drawdown = closes.map((value, index) => peak[index] > 0 ? ((value / peak[index]) - 1) * 100 : 0)
    const worstDrawdown = Math.min(...drawdown, -1)
    const drawdownPoints = drawdown.map((value, index) => `${x(index)},${18 + ((0 - value) / Math.abs(worstDrawdown)) * 48}`).join(" ")
    const drawdownArea = `48,12 ${drawdownPoints} 868,12`
    const maxVolume = Math.max(...bars.map((bar) => bar.volume), 1)
    return {
      close: line(closes),
      sma20: line(sma(20)),
      sma50: line(sma(50)),
      sma200: line(sma(200)),
      drawdown: drawdownPoints,
      drawdownArea,
      volumes: bars.map((bar, index) => ({
        x: x(index),
        y: 226 - (bar.volume / maxVolume) * 30,
        height: (bar.volume / maxVolume) * 30,
      })),
      first: bars[0]?.trading_date,
      last: bars[bars.length - 1]?.trading_date,
      latest: closes[closes.length - 1],
      min,
      max,
    }
  }, [bars, history])

  if (loading) return <div className="mi-chart-state">Loading historical price bars…</div>
  if (error) return <div className="mi-chart-state">Price history unavailable: {error}</div>
  if (bars.length === 0) return <div className="mi-chart-state">No historical OHLCV bars were returned for this analysis cutoff.</div>

  return (
    <section className="mi-price-chart" aria-label="Historical price and volume chart">
      <div className="mi-chart-head">
        <div><span className="mi-chart-kicker">PRICE HISTORY</span><strong>{fmtVal(String(series.latest))}</strong><small>Latest close · {series.last ? formatIso(series.last) : "—"}</small></div>
        <div className="mi-chart-ranges" aria-label="Chart date range">
          {(["3M", "6M", "1Y", "ALL"] as const).map((item) => <button key={item} className={range === item ? "active" : ""} onClick={() => setRange(item)}>{item}</button>)}
        </div>
      </div>
      <div className="mi-chart-toggles">
        <label><input type="checkbox" checked={show20} onChange={(e) => setShow20(e.target.checked)} /> SMA 20</label>
        <label><input type="checkbox" checked={show50} onChange={(e) => setShow50(e.target.checked)} /> SMA 50</label>
        <label><input type="checkbox" checked={show200} onChange={(e) => setShow200(e.target.checked)} /> SMA 200</label>
      </div>
      <svg className="mi-chart-svg" viewBox="0 0 900 244" role="img" aria-label="Closing price with moving average overlays and daily volume">
        <line x1="48" y1="18" x2="868" y2="18" className="mi-chart-gridline" />
        <line x1="48" y1="101" x2="868" y2="101" className="mi-chart-gridline" />
        <line x1="48" y1="184" x2="868" y2="184" className="mi-chart-gridline" />
        <text x="42" y="21" textAnchor="end" className="mi-chart-axis">{fmtVal(String(series.max))}</text>
        <text x="42" y="187" textAnchor="end" className="mi-chart-axis">{fmtVal(String(series.min))}</text>
        {show200 && <polyline points={series.sma200} className="mi-chart-sma mi-chart-sma200" />}
        {show50 && <polyline points={series.sma50} className="mi-chart-sma mi-chart-sma50" />}
        {show20 && <polyline points={series.sma20} className="mi-chart-sma mi-chart-sma20" />}
        <polyline points={series.close} className="mi-chart-price" />
        {series.volumes.map((bar, index) => <rect key={index} x={bar.x - 1.5} y={bar.y} width="3" height={bar.height} className="mi-chart-volume" />)}
        <text x="48" y="242" className="mi-chart-axis">{series.first ? formatIso(series.first) : ""}</text>
        <text x="868" y="242" textAnchor="end" className="mi-chart-axis">{series.last ? formatIso(series.last) : ""}</text>
      </svg>
      <div className="mi-chart-legend">
        <span><i className="price" /> Close</span>
        {show20 && <span><i className="sma20" /> SMA 20</span>}
        {show50 && <span><i className="sma50" /> SMA 50</span>}
        {show200 && <span><i className="sma200" /> SMA 200</span>}
        <span><i className="volume" /> Volume</span>
      </div>
      <div className="mi-drawdown-strip">
        <span>Drawdown from rolling peak</span>
        <svg viewBox="0 0 900 72" role="img" aria-label="Drawdown from running historical peak">
          <line x1="48" y1="12" x2="868" y2="12" className="mi-chart-gridline" />
          <polygon points={series.drawdownArea} className="mi-chart-drawdown-area" />
          <polyline points={series.drawdown} className="mi-chart-drawdown" />
        </svg>
      </div>
      <p className="mi-chart-footnote">{history?.bars_returned ?? bars.length} daily bars returned · {history?.price_basis ?? "Provider OHLC"} · Moving averages use preceding available history, including bars before the selected display window. The OHLC line uses provider OHLC; adjusted-close treatment is not applied.</p>
    </section>
  )
}

/* ── Main Component ──────────────────────────────────────────────────── */

export default function MarketIntelligencePage() {
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)
  const [recentSymbols, setRecentSymbols] = useState<string[]>([])
  const [techData, setTechData] = useState<CompanyDeepTechnicalResponse | null>(null)
  const [researchData, setResearchData] = useState<CompanyResearch | null>(null)
  const [priceHistory, setPriceHistory] = useState<PriceHistoryResponse | null>(null)
  const [chartLoading, setChartLoading] = useState(false)
  const [chartError, setChartError] = useState<string | null>(null)
  const [dataLoading, setDataLoading] = useState(false)
  const [dataError, setDataError] = useState<string | null>(null)
  const requestSequence = useRef(0)

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
    const requestId = ++requestSequence.current
    setSelectedSymbol(sym)
    setRecentSymbols((previous) => [sym, ...previous.filter((item) => item !== sym)].slice(0, 5))
    setTechData(null)
    setResearchData(null)
    setPriceHistory(null)
    setChartError(null)
    setChartLoading(true)
    setDataLoading(true)
    setDataError(null)
    try {
      const [tech, research] = await Promise.all([
        fetchDeepTechnicals(sym),
        fetchResearch(sym),
      ])
      if (requestId !== requestSequence.current) return
      setTechData(tech)
      setResearchData(research)
      void fetchPriceHistory(sym).then((history) => { if (requestId === requestSequence.current) setPriceHistory(history) }).catch((err: unknown) => { if (requestId === requestSequence.current) setChartError(err instanceof Error ? err.message : "Price history request failed") }).finally(() => { if (requestId === requestSequence.current) setChartLoading(false) })
    } catch (err) {
      if (requestId !== requestSequence.current) return
      setChartLoading(false)
      setDataError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error ? err.message : "Failed to load market data",
      )
    } finally {
      if (requestId === requestSequence.current) setDataLoading(false)
    }
  }, [])

  const tech: DeepTechnicalResult | null = techData?.deep_technicals ?? null
  const ind: TechnicalIndicatorSet | null = tech?.indicators ?? null
  const marketObs = researchData?.intelligence?.market_intelligence?.observations ?? []

  return (
    <div className="page-market-intelligence">
      <section className="page-hero mi-page-hero">
        <p className="page-kicker">MARKETS</p>
        <h1>Market Overview</h1>
        <p className="page-subtitle">
          Market-feed availability and company-level price context. Select a company to inspect its historical market behaviour and calculations.
        </p>
      </section>

      {loading && <LoadingState label="Loading market data" />}

      {error && <ErrorState error={error} />}

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
              {recentSymbols.length > 0 && (
                <div className="mi-recent-companies">
                  <span className="mi-recent-label">RECENTLY OPENED</span>
                  <div className="mi-recent-list">
                    {recentSymbols.map((symbol) => (
                      <button
                        key={symbol}
                        type="button"
                        className={selectedSymbol === symbol ? "active" : ""}
                        onClick={() => void loadCompany(symbol)}
                      >
                        {symbol}
                      </button>
                    ))}
                  </div>
                </div>
              )}
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
              <section className="mi-default-overview">
                <header className="mi-default-heading">
                  <div>
                    <span className="mi-default-kicker">MARKET DESK</span>
                    <h2>India market overview</h2>
                    <p>Start with the available research universe. Select a company to open its price and technical analysis.</p>
                  </div>
                  <span className="mi-default-note">Research coverage · not live market quotes</span>
                </header>
                <div className="mi-market-feed-notice">
                  <div><span className="mi-feed-indicator" /><strong>India market feeds are not integrated yet</strong></div>
                  <p>Market levels, breadth, volatility and sector returns will appear here only when timestamped source data is available. Your research universe below is available now.</p>
                  <div className="mi-feed-items"><span>NIFTY 50 · Pending feed</span><span>SENSEX · Pending feed</span><span>India VIX · Pending feed</span><span>Market breadth · Pending feed</span><span>Sector returns · Pending feed</span></div>
                </div>
                <section className="mi-default-next-step">
                  <div><strong>Company-level analysis is available</strong><p>Use the company list to the left to open price history, period returns, trend context, drawdowns and indicator coverage.</p></div>
                  <span>{researchable.length} tracked companies · {new Set(researchable.map((company) => company.sector || "Unclassified")).size} sectors</span>
                </section>
              </section>
            )}

            {selectedSymbol && dataLoading && (
              <LoadingState label={`Fetching market observations for ${selectedSymbol}...`} />
            )}

            {selectedSymbol && dataError && (
              <ErrorState
                error={dataError}
                retryLabel={`Retry for ${selectedSymbol}`}
                onRetry={() => void loadCompany(selectedSymbol)}
              />
            )}

            {selectedSymbol && !dataLoading && !dataError && !ind && (
              <EmptyState
                icon={BarChart3}
                title="No market data available"
                description={`No market observations are available for ${selectedSymbol}.`}
              />
            )}

            {selectedSymbol && ind && !dataLoading && (
              <>
                {/* Header */}
                <div className="mi-header">
                  <div className="mi-header-row">
                    <span className="mi-company-symbol"><strong>{tech?.symbol}</strong></span>
                    <span>Latest trading date: {formatIso(tech?.trading_date ?? "")}</span>
                    <span>Calculation run: {formatIso(tech?.as_of ?? "")}</span>
                    <span>Source: Yahoo Finance</span>
                  </div>
                </div>

                <PriceChart history={priceHistory} loading={chartLoading} error={chartError} />

                <details className="mi-methodology">
                  <summary>How these metrics are calculated</summary>
                  <div className="mi-methodology-grid">
                    <article><strong>Trend regime & strength</strong><p>Compares the latest close with up to six simple moving averages (5, 10, 20, 50, 100 and 200 bars). Regime labels are based on how many averages price is above or below; strength is the share of available averages price is above. This is a rule-based description, not a forecast.</p></article>
                    <article><strong>ATR volatility</strong><p>14-period Average True Range uses the greatest of high–low, high–previous-close and low–previous-close. ATR % expresses that range as a percentage of the latest close. It measures magnitude, not direction.</p></article>
                    <article><strong>Current drawdown</strong><p>Calculated from the highest close in the fetched history to the latest close. It is not necessarily a lifetime or full 52-week drawdown; its scope is limited by the returned price history.</p></article>
                    <article><strong>Money Flow Index</strong><p>MFI(14) compares positive and negative typical-price × volume flows over 14 periods. Values at or above 80 are labelled overbought; values at or below 20 are labelled oversold.</p></article>
                    <article><strong>Price–volume divergence</strong><p>A simple five-bar check: price rising while the latest volume falls versus five bars earlier is labelled bearish divergence; price falling while volume rises is labelled bullish divergence. It is a heuristic, not a statistical confirmation.</p></article>
                    <article><strong>Gap events</strong><p>Compares the latest session open with the previous session close. A gap is recorded when the absolute difference is at least 1%; smaller moves are classified as no gap.</p></article>
                    <article><strong>52-week context</strong><p>Uses up to 252 returned daily bars, taking the highest high and lowest low in that window. If fewer bars are available, the displayed range is shorter and should not be interpreted as a complete 52-week range.</p></article>
                    <article><strong>Returns</strong><p>Period returns compare the latest close with the close 1, 5, 10, 20, 50, 100 or 200 bars earlier. They are price returns and do not include dividends.</p></article>
                  </div>
                </details>

                {/* 1. MARKET OVERVIEW */}
                <Section id="overview" title="Market Overview" subtitle="Price context and key market metrics">
                  <div className="mi-section-body">
                  <div className="mi-overview-grid">
                    <MarketMetric label="Trend Regime" value={null} regime={ind.regime ? formatLabel(ind.regime) : null} availability={ind.regime ? "available" : "missing"} />
                    <MarketMetric label="Trend Strength" value={ind.trend_strength == null ? null : String(Number(ind.trend_strength) * 100)} unit="%" />
                    <MarketMetric label="Volatility (ATR %)" value={ind.atr_pct} unit="%" />
                    <MarketMetric label="Current Drawdown" value={ind.current_drawdown} unit="%" />
                  </div>
                  </div>
                </Section>

                {/* 2. RETURNS */}
                <Section id="returns" title="Period Returns" subtitle="Observed price changes over multiple time horizons">
                  <div className="mi-section-body">
                  <div className="mi-returns-section">
                    <ReturnBar label="1-Day" value={ind.return_1d} />
                    <ReturnBar label="5-Day" value={ind.return_5d} />
                    <ReturnBar label="10-Day" value={ind.return_10d} />
                    <ReturnBar label="20-Day" value={ind.return_20d} />
                    <ReturnBar label="50-Day" value={ind.return_50d} />
                    <ReturnBar label="100-Day" value={ind.return_100d} />
                    <ReturnBar label="200-Day" value={ind.return_200d} />
                  </div>
                  </div>
                </Section>

                {/* 3. TREND & VOLATILITY CONTEXT */}
                <Section id="trend-volatility" title="Trend & Volatility" subtitle="Regime classification and trend assessment">
                  <div className="mi-section-body">
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
                          <span className="mono">{ind.trend_strength == null ? "—" : `${(Number(ind.trend_strength) * 100).toFixed(1)}%`}</span>
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
                  </div>
                </Section>

                {/* 4. VOLUME & ACTIVITY */}
                <Section id="volume" title="Volume & Activity" subtitle="Trading volume behavior and gap events">
                  <div className="mi-section-body">
                  <div className="mi-volume-grid">
                    <div className="mi-volume-card">
                      <div className="mi-trend-vol-head">
                        <BarChart3 size={14} />
                        <span>Volume</span>
                      </div>
                      <div className="mi-trend-vol-body">
                        <div className="mi-trend-vol-row">
                          <span>On-Balance Volume</span>
                          <span className="mono">{ind.obv !== null ? fmtCompact(ind.obv) : "\u2014"}</span>
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
                        {!ind.gap_type || ["NONE", "NO_GAP"].includes(ind.gap_type.toUpperCase()) ? (
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
                            text={ind.price_volume_divergence ? formatLabel(ind.price_volume_divergence) : "Unknown"}
                            tone={regimeTone(ind.price_volume_divergence)}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                  </div>
                </Section>

                {/* 5. 52-WEEK CONTEXT */}
                <Section id="52week" title="52-Week Context" subtitle="Distance from yearly highs and lows">
                  <div className="mi-section-body">
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
                  </div>
                </Section>

                {/* 6. MARKET OBSERVATIONS (from research intelligence) */}
                {marketObs.length > 0 && (
                  <Section id="observations" title="Market Observations" subtitle="Text observations from research intelligence">
                    <div className="mi-section-body">
                    <ObservationTextList observations={marketObs} />
                    </div>
                  </Section>
                )}

                {/* 7. DATA QUALITY */}
                <Section id="data-quality" title="Data Quality" subtitle="Availability and freshness of market data">
                  <div className="mi-section-body">
                  <div className="mi-data-quality">
                    <div className="mi-dq-row">
                      <span>Daily observations used in calculations</span>
                      <span className="mono">{tech?.bars_used ?? "\u2014"}</span>
                    </div>
                    <div className="mi-dq-row">
                      <span>Available indicators</span>
                      <span className="mono">{tech?.available_indicators.length ?? 0}</span>
                    </div>
                    {tech && tech.missing_indicators.length > 0 && (
                      <div className="mi-dq-row warn">
                        <span>Unavailable calculations</span>
                        <span className="mono">{tech.missing_indicators.map(formatLabel).join(", ")}</span>
                      </div>
                    )}
                    <div className="mi-dq-row">
                      <span>Market data provider</span>
                      <span className="mono">Yahoo Finance provider</span>
                    </div>
                    <div className="mi-dq-row">
                      <span>Provider retrieval timestamp</span>
                      <span className="mono">Not exposed by this endpoint</span>
                    </div>
                    <div className="mi-dq-row">
                      <span>Calculation run timestamp</span>
                      <span className="mono">{tech?.as_of ? formatIso(tech.as_of) : "Unavailable"}</span>
                    </div>
                    <div className="mi-dq-row">
                      <span>History scope</span>
                      <span className="mono">Up to 800 calendar days requested · {tech?.bars_used ?? 0} returned bars used</span>
                    </div>
                    <div className="mi-dq-row">
                      <span>Latest trading date</span>
                      <span className="mono">{tech?.trading_date ? formatIso(tech.trading_date) : "Unavailable"}</span>
                    </div>
                    <div className="mi-dq-row">
                      <span>Calculation scope</span>
                      <span className="mono">Daily OHLCV bars · point-in-time filtered</span>
                    </div>
                    {tech && tech.notes.length > 0 && (
                      <div className="mi-dq-notes">
                        {tech.notes.map((n, i) => <span key={i}>{n}</span>)}
                      </div>
                    )}
                  </div>
                  </div>
                </Section>

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
