import { useEffect, useState } from "react"
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Building2,
  ChevronRight,
  CircleAlert,
  FileText,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react"

import "./App.css"

const API_URL = "http://127.0.0.1:8000"

type ResearchData = {
  company: {
    symbol: string
    name: string
    as_of: string
  }
  research_score: {
    total: string
    signal: string
    confidence: string
    components: Record<string, string>
  }
  intelligence: {
    direction: string
    signal_count: number
    material_signal_count: number
    positive_signal_count: number
    negative_signal_count: number
    signals: Array<{
      code: string
      title: string
      description: string
      direction: string
      materiality: number
      confidence: string
    }>
  }
  financial_trends: Array<{
    metric: string
    direction: string
    observations: number
    average_change: string
    consistency: string
    explanation: string
  }>
  observations: {
    financial: string[]
    ownership: string[]
    management: string[]
    events: string[]
    market: string[]
    risk: string[]
  }
  evidence: Array<{
    source_name: string
    source_type: string
    title: string
    published_date: string
    reliability_tier: number
    reference: string
  }>
  is_trade_signal: boolean
}

function App() {
  const [data, setData] = useState<ResearchData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  async function loadResearch() {
    try {
      setLoading(true)
      setError("")

      const response = await fetch(`${API_URL}/api/research/demo`)

      if (!response.ok) {
        throw new Error(`API returned ${response.status}`)
      }

      const result: ResearchData = await response.json()
      setData(result)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to research API",
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadResearch()
  }, [])

  if (loading) {
    return (
      <div className="loading-screen">
        <RefreshCw size={24} />
        <span>Loading research intelligence...</span>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="error-screen">
        <CircleAlert size={30} />

        <h2>Research API unavailable</h2>

        <p>{error || "No research data returned."}</p>

        <button onClick={loadResearch}>
          <RefreshCw size={15} />
          Retry
        </button>
      </div>
    )
  }

  const score = Number(data.research_score.total)

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">Q</div>

          <div>
            <strong>Quant Research</strong>
            <span>Research Intelligence Terminal</span>
          </div>
        </div>

        <div className="topbar-actions">
          <div className="api-status">
            <span />
            API Connected
          </div>

          <button
            className="icon-button"
            onClick={loadResearch}
            aria-label="Refresh research"
          >
            <RefreshCw size={17} />
          </button>

          <div className="avatar">VY</div>
        </div>
      </header>

      <main className="dashboard">
        <section className="search-row">
          <div>
            <p className="eyebrow">COMPANY RESEARCH</p>

            <h1>Research workspace</h1>

            <p className="subheading">
              Evidence-driven analysis across fundamentals, risk and market
              behaviour.
            </p>
          </div>

          <div className="search-box">
            <Search size={18} />

            <span>Search company or symbol</span>

            <kbd>⌘ K</kbd>
          </div>
        </section>

        <section className="company-card">
          <div className="company-main">
            <div className="company-icon">
              <Building2 size={25} />
            </div>

            <div>
              <div className="symbol-row">
                <h2>{data.company.symbol}</h2>

                <span
                  className={`status-pill ${
                    data.research_score.signal.toLowerCase() === "positive"
                      ? "positive"
                      : ""
                  }`}
                >
                  {data.research_score.signal}
                </span>
              </div>

              <p>{data.company.name}</p>

              <small>Research date · {data.company.as_of}</small>
            </div>
          </div>

          <div className="trade-protection">
            <ShieldCheck size={18} />

            <div>
              <strong>
                {data.is_trade_signal ? "Trade signal" : "Research only"}
              </strong>

              <span>
                {data.is_trade_signal
                  ? "Automated signal available"
                  : "No automated trade signal"}
              </span>
            </div>
          </div>
        </section>

        <section className="hero-grid">
          <div className="score-card">
            <div className="card-heading">
              <div>
                <p className="eyebrow">RESEARCH SCORE</p>
                <h3>Overall assessment</h3>
              </div>

              <BarChart3 size={21} />
            </div>

            <div className="score-content">
              <div
                className="score-ring"
                style={{
                  background: `radial-gradient(circle at center, #0d1219 57%, transparent 58%), conic-gradient(#61d695 0 ${Math.min(
                    score,
                    100,
                  )}%, #1c2732 ${Math.min(score, 100)}% 100%)`,
                }}
              >
                <div>
                  <strong>{score.toFixed(0)}</strong>
                  <span>/100</span>
                </div>
              </div>

              <div className="score-summary">
                <span className="large-positive">
                  {data.research_score.signal}
                </span>

                <p>
                  Composite research score based on fundamentals, trends,
                  cash flow, balance sheet, risk, management and market
                  behaviour.
                </p>

                <div className="confidence">
                  <span>Confidence</span>

                  <strong>
                    {Number(data.research_score.confidence).toFixed(1)}%
                  </strong>
                </div>
              </div>
            </div>
          </div>

          <div className="intelligence-card">
            <div className="card-heading">
              <div>
                <p className="eyebrow">COMPANY INTELLIGENCE</p>
                <h3>What changed?</h3>
              </div>

              <span className="mixed-pill">
                {data.intelligence.direction}
              </span>
            </div>

            <div className="signal-summary">
              <div>
                <strong>{data.intelligence.signal_count}</strong>
                <span>Total signals</span>
              </div>

              <div>
                <strong>{data.intelligence.positive_signal_count}</strong>
                <span>Positive</span>
              </div>

              <div>
                <strong>{data.intelligence.negative_signal_count}</strong>
                <span>Negative</span>
              </div>
            </div>

            <div className="signal-list">
              {data.intelligence.signals.map((signal) => (
                <div className="signal-item" key={signal.code}>
                  <div
                    className={`signal-icon ${
                      signal.direction === "POSITIVE"
                        ? "signal-positive"
                        : "signal-negative"
                    }`}
                  >
                    {signal.direction === "POSITIVE" ? (
                      <ArrowUpRight size={17} />
                    ) : (
                      <ArrowDownRight size={17} />
                    )}
                  </div>

                  <div className="signal-copy">
                    <strong>{signal.title}</strong>

                    <span>{signal.description}</span>
                  </div>

                  <div className="materiality">
                    M{signal.materiality}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="section-header">
          <div>
            <p className="eyebrow">FINANCIAL ENGINE</p>
            <h2>Financial trends</h2>
          </div>

          <button className="text-button">
            View all
            <ChevronRight size={15} />
          </button>
        </section>

        <section className="trend-grid">
          {data.financial_trends.map((trend) => (
            <div className="trend-card" key={trend.metric}>
              <div className="trend-top">
                <span>{formatMetric(trend.metric)}</span>

                {trend.direction === "INCREASING" ? (
                  <ArrowUpRight size={18} />
                ) : trend.direction === "DECREASING" ? (
                  <ArrowDownRight size={18} />
                ) : (
                  <Activity size={18} />
                )}
              </div>

              <strong className="trend-value">
                {formatChange(trend.average_change)}
              </strong>

              <div className="trend-meta">
                <span>{trend.direction}</span>

                <span>{trend.consistency}% consistency</span>
              </div>

              <div className="trend-bar">
                <div
                  style={{
                    width: `${Math.min(
                      Number(trend.consistency),
                      100,
                    )}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </section>

        <section className="lower-grid">
          <div className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">OBSERVATIONS</p>
                <h3>Research snapshot</h3>
              </div>
            </div>

            <ObservationGroup
              title="Financial"
              items={data.observations.financial}
            />

            <ObservationGroup
              title="Ownership"
              items={data.observations.ownership}
            />

            <ObservationGroup
              title="Management"
              items={data.observations.management}
            />

            <ObservationGroup
              title="Events"
              items={data.observations.events}
            />

            <ObservationGroup
              title="Market"
              items={data.observations.market}
            />

            <ObservationGroup
              title="Risk"
              items={data.observations.risk}
              warning
            />
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">EVIDENCE</p>
                <h3>Source quality</h3>
              </div>

              <FileText size={20} />
            </div>

            {data.evidence.map((item) => (
              <div
                className="evidence-card"
                key={item.reference}
              >
                <div className="evidence-icon">
                  <FileText size={17} />
                </div>

                <div>
                  <strong>{item.title}</strong>

                  <span>{item.source_name}</span>

                  <small>
                    Tier {item.reliability_tier} · {item.source_type} ·{" "}
                    {item.published_date}
                  </small>
                </div>
              </div>
            ))}

            <div className="evidence-footer">
              <ShieldCheck size={16} />

              Evidence is retained with the research snapshot.
            </div>
          </div>
        </section>

        <section className="component-section">
          <div className="section-header">
            <div>
              <p className="eyebrow">SCORE BREAKDOWN</p>
              <h2>Research components</h2>
            </div>
          </div>

          <div className="component-grid">
            {Object.entries(data.research_score.components).map(
              ([name, value]) => (
                <div className="component-card" key={name}>
                  <div>
                    <span>{formatMetric(name)}</span>

                    <strong>{value}</strong>
                  </div>

                  <div className="component-track">
                    <div
                      style={{
                        width: `${Math.min(
                          Number(value),
                          100,
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              ),
            )}
          </div>
        </section>
      </main>
    </div>
  )
}

function ObservationGroup({
  title,
  items,
  warning = false,
}: {
  title: string
  items: string[]
  warning?: boolean
}) {
  if (!items.length) {
    return null
  }

  return (
    <div className="observation-group">
      <div className="observation-title">
        <span>{title}</span>

        {warning && <CircleAlert size={13} />}
      </div>

      {items.map((item) => (
        <div className="observation" key={item}>
          <span />
          {item}
        </div>
      ))}
    </div>
  )
}

function formatMetric(metric: string) {
  return metric
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatChange(value: string) {
  const number = Number(value)

  if (Number.isNaN(number)) {
    return value
  }

  const sign = number > 0 ? "+" : ""

  return `${sign}${number.toLocaleString()}`
}

export default App