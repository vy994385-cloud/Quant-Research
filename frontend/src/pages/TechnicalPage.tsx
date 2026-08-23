/**
 * Technical / Market-Movement Research page.
 * Fetches deep technical indicators per company from the backend.
 * Displays trend, momentum, volatility, volume, support/resistance, and observations.
 * No scores, no recommendations, no trade signals.
 */

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  Activity,
  FileSearch,
  Search,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from "lucide-react"
import { fetchDiscovery, fetchDeepTechnicals } from "../api/client"
import { ApiError } from "../api/client"
import type {
  CompanyDeepTechnicalResponse,
  DeepTechnicalResult,
  DiscoveryItem,
  TechnicalIndicatorSet,
  TechnicalObservation,
} from "../api/types"
import { formatIso, formatLabel, formatSourceName } from "../lib/format"
import { Tag, SectionDivider } from "../components/ui"

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

function fmtVal(v: string | null | undefined): string {
  if (v === null || v === undefined) return "\u2014"
  const n = parseNum(v)
  if (n === null) return v
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 })
}

function directionIcon(d: string) {
  if (d === "BULLISH" || d === "POSITIVE" || d === "OVERSOLD") return <ArrowUpRight size={12} />
  if (d === "BEARISH" || d === "NEGATIVE" || d === "OVERBOUGHT") return <ArrowDownRight size={12} />
  return <Minus size={12} />
}

function directionTone(d: string): "green" | "red" | "amber" | "slate" {
  if (d === "BULLISH" || d === "POSITIVE" || d === "OVERSOLD") return "green"
  if (d === "BEARISH" || d === "NEGATIVE" || d === "OVERBOUGHT") return "red"
  if (d === "NEUTRAL") return "slate"
  return "amber"
}

/* ── Indicator Row ────────────────────────────────────────────────────── */

function IndicatorRow({
  label,
  value,
  signal,
  detail,
}: {
  label: string
  value: string | null | undefined
  signal?: string | null
  detail?: string
}) {
  const v = fmtVal(value)
  return (
    <div className="tech-indicator-row">
      <span className="tech-indicator-label">{label}</span>
      <span className="tech-indicator-value mono">{v}</span>
      {signal && (
        <Tag text={formatLabel(signal)} tone={directionTone(signal)} />
      )}
      {detail && <span className="tech-indicator-detail">{detail}</span>}
    </div>
  )
}

/* ── Indicator Section ────────────────────────────────────────────────── */

function IndicatorSection({
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
    <section id={id} className="tech-section">
      <div className="tech-section-head">
        <h3>{title}</h3>
        {subtitle && <span>{subtitle}</span>}
      </div>
      <div className="tech-section-body">{children}</div>
    </section>
  )
}

/* ── Observation List ─────────────────────────────────────────────────── */

function ObservationList({ observations }: { observations: TechnicalObservation[] }) {
  if (observations.length === 0) return null

  const bySeverity = {
    high: observations.filter((o) => o.severity === "HIGH"),
    medium: observations.filter((o) => o.severity === "MEDIUM"),
    low: observations.filter((o) => o.severity === "LOW"),
  }

  return (
    <div className="tech-observations">
      <SectionDivider label="TECHNICAL OBSERVATIONS" />
      {(["high", "medium", "low"] as const).map((sev) => {
        const obs = bySeverity[sev]
        if (obs.length === 0) return null
        return (
          <div key={sev} className="tech-obs-group">
            <div className="tech-obs-group-head">
              <strong>{sev.toUpperCase()} SEVERITY</strong>
              <span>{obs.length} observations</span>
            </div>
            <div className="tech-obs-list">
              {obs.map((o) => (
                <div key={o.observation_id} className="tech-obs-row">
                  <span className="tech-obs-head">
                    {directionIcon(o.direction)}
                    <strong>{o.indicator}</strong>
                    <Tag text={formatLabel(o.signal)} tone={directionTone(o.direction)} />
                  </span>
                  <p className="tech-obs-explanation">{o.explanation}</p>
                  <div className="tech-obs-meta">
                    <span>Period: {o.period}</span>
                    {o.value && <span>Value: {o.value}</span>}
                    <span>Source: {formatSourceName(o.source)}</span>
                    {o.as_of && <span>As-of: {formatIso(o.as_of)}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ── Main Component ──────────────────────────────────────────────────── */

export default function TechnicalPage() {
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)
  const [techData, setTechData] = useState<CompanyDeepTechnicalResponse | null>(null)
  const [techLoading, setTechLoading] = useState(false)
  const [techError, setTechError] = useState<string | null>(null)

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

  const loadTechnicals = useCallback(async (sym: string) => {
    setSelectedSymbol(sym)
    setTechData(null)
    setTechLoading(true)
    setTechError(null)
    try {
      const result = await fetchDeepTechnicals(sym)
      setTechData(result)
    } catch (err) {
      setTechError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error ? err.message : "Failed to load technicals",
      )
    } finally {
      setTechLoading(false)
    }
  }, [])

  const tech: DeepTechnicalResult | null = techData?.deep_technicals ?? null
  const indicators: TechnicalIndicatorSet | null = tech?.indicators ?? null
  const observations = tech?.observation_set?.signal_observations ?? []

  return (
    <div className="page-technical">
      <section className="page-hero">
        <h1>Technical Research</h1>
        <p className="page-subtitle">
          Market-movement research: trend, momentum, volatility, volume, support/resistance.
          All observations are informational. No scores, no recommendations, no trade signals.
        </p>
      </section>

      {loading && (
        <div className="loading-state" role="status">
          <Activity className="spin" size={26} />
          <strong>Loading technical data</strong>
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
                    onClick={() => void loadTechnicals(item.symbol)}
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

          {/* RIGHT: Technical content */}
          <div className="fi-content">
            {!selectedSymbol && (
              <div className="empty-state">
                <BarChart3 size={28} />
                <strong>Select a company</strong>
                <p>Choose a company from the list to view its technical research.</p>
              </div>
            )}

            {selectedSymbol && techLoading && (
              <div className="loading-state" role="status">
                <Activity className="spin" size={26} />
                <strong>Loading technicals</strong>
                <span>Fetching technical data for {selectedSymbol}...</span>
              </div>
            )}

            {selectedSymbol && techError && (
              <div className="empty-state error" role="alert">
                <FileSearch size={28} />
                <strong>Technical data unavailable</strong>
                <p>{techError}</p>
                <p className="error-hint">
                  This indicator set could not be produced for {selectedSymbol}. The rest of
                  the research record for this company is unaffected.
                </p>
              </div>
            )}

            {selectedSymbol && tech && !techLoading && (
              <>
                {!indicators ? (
                  <div className="empty-state">
                    <BarChart3 size={28} />
                    <strong>No technical data</strong>
                    <p>No technical indicators are available for {selectedSymbol}.</p>
                  </div>
                ) : (
                  <>
                    {/* Header info */}
                    <div className="tech-header">
                      <div className="tech-header-row">
                        <span><strong>{tech.symbol}</strong></span>
                        <span>Trading date: {formatIso(tech.trading_date)}</span>
                        <span>Bars used: {tech.bars_used}</span>
                        <span>As-of: {formatIso(tech.as_of)}</span>
                      </div>
                      {tech.notes.length > 0 && (
                        <div className="tech-notes">
                          {tech.notes.map((n, i) => <span key={i}>{n}</span>)}
                        </div>
                      )}
                      {tech.missing_indicators.length > 0 && (
                        <div className="tech-missing">
                          <span>Missing indicators: {tech.missing_indicators.join(", ")}</span>
                        </div>
                      )}
                    </div>

                    {/* 52-Week Range & Drawdown */}
                    <IndicatorSection id="price-context" title="Price Context" subtitle="52-week range, drawdown, gaps">
                      <IndicatorRow label="52-Week High" value={indicators.high_52w} />
                      <IndicatorRow label="52-Week Low" value={indicators.low_52w} />
                      <IndicatorRow label="% from 52W High" value={indicators.pct_from_52w_high} detail="Percentage distance from 52-week high" />
                      <IndicatorRow label="% from 52W Low" value={indicators.pct_from_52w_low} detail="Percentage distance from 52-week low" />
                      <IndicatorRow label="52W Signal" value={indicators.high_low_signal} signal={indicators.high_low_signal} />
                      <IndicatorRow label="Current Drawdown" value={indicators.current_drawdown} detail="Drawdown from recent high" />
                      <IndicatorRow label="Max Drawdown (20d)" value={indicators.max_drawdown_20d} />
                      <IndicatorRow label="Recovery %" value={indicators.recovery_pct} />
                      <IndicatorRow label="Gap Type" value={indicators.gap_type} />
                      <IndicatorRow label="Gap %" value={indicators.gap_pct} />
                    </IndicatorSection>

                    {/* Trend */}
                    <IndicatorSection id="trend" title="Trend" subtitle="Regime, strength, alignment">
                      <IndicatorRow label="Trend Regime" value={indicators.regime} signal={indicators.regime} />
                      <IndicatorRow label="Trend Strength" value={indicators.trend_strength} />
                      <IndicatorRow label="SMA Alignment" value={indicators.sma_alignment} signal={indicators.sma_alignment} />
                      <IndicatorRow label="EMA Alignment" value={indicators.ema_alignment} signal={indicators.ema_alignment} />
                    </IndicatorSection>

                    {/* Moving Averages */}
                    <IndicatorSection id="moving-averages" title="Moving Averages" subtitle="SMA and EMA values with price distance">
                      <IndicatorRow label="SMA 5" value={indicators.sma_5} detail={indicators.price_vs_sma_5_pct ? `${fmtPct(indicators.price_vs_sma_5_pct)} vs price` : undefined} />
                      <IndicatorRow label="SMA 10" value={indicators.sma_10} />
                      <IndicatorRow label="SMA 20" value={indicators.sma_20} detail={indicators.price_vs_sma_20_pct ? `${fmtPct(indicators.price_vs_sma_20_pct)} vs price` : undefined} />
                      <IndicatorRow label="SMA 50" value={indicators.sma_50} detail={indicators.price_vs_sma_50_pct ? `${fmtPct(indicators.price_vs_sma_50_pct)} vs price` : undefined} />
                      <IndicatorRow label="SMA 100" value={indicators.sma_100} />
                      <IndicatorRow label="SMA 200" value={indicators.sma_200} />
                      <IndicatorRow label="EMA 9" value={indicators.ema_9} detail={indicators.price_vs_ema_9_pct ? `${fmtPct(indicators.price_vs_ema_9_pct)} vs price` : undefined} />
                      <IndicatorRow label="EMA 12" value={indicators.ema_12} />
                      <IndicatorRow label="EMA 20" value={indicators.ema_20} detail={indicators.price_vs_ema_20_pct ? `${fmtPct(indicators.price_vs_ema_20_pct)} vs price` : undefined} />
                      <IndicatorRow label="EMA 26" value={indicators.ema_26} />
                      <IndicatorRow label="EMA 50" value={indicators.ema_50} detail={indicators.price_vs_ema_50_pct ? `${fmtPct(indicators.price_vs_ema_50_pct)} vs price` : undefined} />
                      <IndicatorRow label="EMA 200" value={indicators.ema_200} />
                    </IndicatorSection>

                    {/* Momentum: RSI */}
                    <IndicatorSection id="rsi" title="RSI" subtitle="14-period Relative Strength Index">
                      <IndicatorRow label="RSI (14)" value={indicators.rsi_14} signal={indicators.rsi_signal} />
                      <IndicatorRow label="Signal" value={indicators.rsi_signal} signal={indicators.rsi_signal} />
                    </IndicatorSection>

                    {/* Momentum: MACD */}
                    <IndicatorSection id="macd" title="MACD" subtitle="Moving Average Convergence Divergence">
                      <IndicatorRow label="MACD Line" value={indicators.macd_line} />
                      <IndicatorRow label="Signal Line" value={indicators.macd_signal_line} />
                      <IndicatorRow label="Histogram" value={indicators.macd_histogram} />
                      <IndicatorRow label="Crossover" value={indicators.macd_crossover} signal={indicators.macd_crossover} />
                    </IndicatorSection>

                    {/* Momentum: Stochastic & Williams */}
                    <IndicatorSection id="other-momentum" title="Other Momentum" subtitle="Stochastic, Williams %R, CCI">
                      <IndicatorRow label="Stochastic %K" value={indicators.stochastic_k} />
                      <IndicatorRow label="Stochastic %D" value={indicators.stochastic_d} />
                      <IndicatorRow label="Stochastic Signal" value={indicators.stochastic_signal} signal={indicators.stochastic_signal} />
                      <IndicatorRow label="Williams %R" value={indicators.williams_r_14} />
                      <IndicatorRow label="Williams Signal" value={indicators.williams_r_signal} signal={indicators.williams_r_signal} />
                      <IndicatorRow label="CCI (20)" value={indicators.cci_20} />
                      <IndicatorRow label="CCI Signal" value={indicators.cci_signal} signal={indicators.cci_signal} />
                    </IndicatorSection>

                    {/* Volatility: ATR, Bollinger, ADX */}
                    <IndicatorSection id="volatility" title="Volatility" subtitle="ATR, Bollinger Bands, ADX">
                      <IndicatorRow label="ATR (14)" value={indicators.atr_14} />
                      <IndicatorRow label="ATR %" value={indicators.atr_pct} detail="ATR as percentage of price" />
                      <IndicatorRow label="Bollinger Upper" value={indicators.bollinger_upper} />
                      <IndicatorRow label="Bollinger Middle" value={indicators.bollinger_middle} />
                      <IndicatorRow label="Bollinger Lower" value={indicators.bollinger_lower} />
                      <IndicatorRow label="Bollinger Bandwidth" value={indicators.bollinger_bandwidth} />
                      <IndicatorRow label="Bollinger %B" value={indicators.bollinger_pct_b} />
                      <IndicatorRow label="Bollinger Signal" value={indicators.bollinger_signal} signal={indicators.bollinger_signal} />
                      <IndicatorRow label="ADX (14)" value={indicators.adx_14} />
                      <IndicatorRow label="+DI" value={indicators.adx_plus_di} />
                      <IndicatorRow label="-DI" value={indicators.adx_minus_di} />
                      <IndicatorRow label="ADX Signal" value={indicators.adx_signal} signal={indicators.adx_signal} />
                    </IndicatorSection>

                    {/* Volume */}
                    <IndicatorSection id="volume" title="Volume" subtitle="OBV, AD Line, MFI, divergence">
                      <IndicatorRow label="OBV" value={indicators.obv?.toString() ?? null} />
                      <IndicatorRow label="AD Line" value={indicators.ad_line?.toString() ?? null} />
                      <IndicatorRow label="MFI (14)" value={indicators.mfi_14} signal={indicators.mfi_signal} />
                      <IndicatorRow label="MFI Signal" value={indicators.mfi_signal} signal={indicators.mfi_signal} />
                      <IndicatorRow label="Price-Volume Divergence" value={indicators.price_volume_divergence} signal={indicators.price_volume_divergence} />
                    </IndicatorSection>

                    {/* Support / Resistance */}
                    <IndicatorSection id="pivots" title="Pivot Points" subtitle="Standard pivot levels">
                      <IndicatorRow label="Pivot" value={indicators.pivot} />
                      <IndicatorRow label="R1" value={indicators.r1} />
                      <IndicatorRow label="R2" value={indicators.r2} />
                      <IndicatorRow label="R3" value={indicators.r3} />
                      <IndicatorRow label="S1" value={indicators.s1} />
                      <IndicatorRow label="S2" value={indicators.s2} />
                      <IndicatorRow label="S3" value={indicators.s3} />
                      <IndicatorRow label="Breakout Signal" value={indicators.breakout_signal} signal={indicators.breakout_signal} />
                    </IndicatorSection>

                    {/* Returns */}
                    <IndicatorSection id="returns" title="Period Returns" subtitle="Historical return periods">
                      <IndicatorRow label="1-Day Return" value={indicators.return_1d} />
                      <IndicatorRow label="5-Day Return" value={indicators.return_5d} />
                      <IndicatorRow label="10-Day Return" value={indicators.return_10d} />
                      <IndicatorRow label="20-Day Return" value={indicators.return_20d} />
                      <IndicatorRow label="50-Day Return" value={indicators.return_50d} />
                      <IndicatorRow label="100-Day Return" value={indicators.return_100d} />
                      <IndicatorRow label="200-Day Return" value={indicators.return_200d} />
                    </IndicatorSection>

                    {/* Observations */}
                    <ObservationList observations={observations} />

                    {/* Note */}
                    <div className="fi-note">
                      <BarChart3 size={13} />
                      <span>
                        Technical observations are informational. Each observation includes
                        the indicator, period, signal direction, severity, and source.
                        No scores, no recommendations, no trade signals.
                      </span>
                    </div>
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
