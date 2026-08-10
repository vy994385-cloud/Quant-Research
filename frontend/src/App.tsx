import { useEffect, useState } from "react"
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Building2,
  ChevronRight,
  CircleDollarSign,
  FileSearch,
  ShieldCheck,
  TrendingDown,
  TrendingUp
} from "lucide-react"

import "./App.css"

const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000"

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
    positive_periods: number
    negative_periods: number
    stable_periods: number
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
    published_date: string | null
    reliability_tier: number
    reference: string
  }>
  is_trade_signal: boolean
}

function App() {
  const [data, setData] = useState<ResearchData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [symbol, setSymbol] = useState("DEMO")

  useEffect(() => {
    loadResearch()
  }, [])

  async function loadResearch() {
    try {
      setLoading(true)
      setError("")

      const response = await fetch(
        `${API_URL}/api/research/demo`
      )

      if (!response.ok) {
        throw new Error("Research API request failed")
      }

      const result = await response.json()
      setData(result)
    } catch (err) {
      console.error(err)
      setError(
        "Unable to connect to the Quant Research API."
      )
    } finally {
      setLoading(false)
    }
  }

  function handleSearch(event: React.FormEvent) {
    event.preventDefault()

    if (symbol.trim().toUpperCase() !== "DEMO") {
      setError(
        "Live company search is the next integration. DEMO is currently available."
      )
      return
    }

    loadResearch()
  }

  if (loading) {
    return (
      <div className="app-shell">
        <div className="loading-screen">
          <Activity size={28} />
          <span>Loading research terminal...</span>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="app-shell">
        <div className="error-screen">
          <AlertTriangle size={30} />
          <h2>Research service unavailable</h2>
          <p>{error}</p>
          <button onClick={loadResearch}>
            Retry
          </button>
        </div>
      </div>
    )
  }

  const score = Number(data.research_score.total)

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            Q
          </div>

          <div>
            <strong>Quant Research</strong>
            <span>Evidence-driven intelligence</span>
          </div>
        </div>

        <nav>
          <button className="nav-active">
            Research
          </button>
          <button>Markets</button>
          <button>Backtests</button>
          <button>Watchlist</button>
        </nav>

        <div className="status">
          <span className="status-dot" />
          Research API online
        </div>
      </header>

      <main className="dashboard">
        <section className="hero">
          <div>
            <p className="eyebrow">
              COMPANY RESEARCH TERMINAL
            </p>

            <h1>
              Understand the business
              <br />
              before the market.
            </h1>

            <p className="hero-copy">
              Fundamental trends, market behaviour,
              intelligence signals and evidence in one
              research workspace.
            </p>
          </div>

          <form
            className="search-box"
            onSubmit={handleSearch}
          >
            <FileSearch size={20} />

            <input
              value={symbol}
              onChange={(event) =>
                setSymbol(event.target.value)
              }
              placeholder="Enter symbol..."
              aria-label="Company symbol"
            />

            <button type="submit">
              Research
              <ChevronRight size={17} />
            </button>
          </form>
        </section>

        {error && (
          <div className="notice">
            <AlertTriangle size={18} />
            {error}
          </div>
        )}

        <section className="company-header">
          <div className="company-title">
            <div className="company-icon">
              <Building2 size={28} />
            </div>

            <div>
              <div className="symbol">
                {data.company.symbol}
              </div>

              <h2>{data.company.name}</h2>

              <span>
                Research as of {data.company.as_of}
              </span>
            </div>
          </div>

          <div className="research-badge">
            <ShieldCheck size={17} />
            Descriptive research
          </div>
        </section>

        <section className="metric-grid">
          <MetricCard
            label="Research Score"
            value={data.research_score.total}
            suffix="/100"
            icon={<BarChart3 size={20} />}
          />

          <MetricCard
            label="Confidence"
            value={Number(
  data.research_score.confidence
).toFixed(2)}
            suffix="%"
            icon={<ShieldCheck size={20} />}
          />

          <MetricCard
            label="Positive Signals"
            value={String(
              data.intelligence.positive_signal_count
            )}
            icon={<TrendingUp size={20} />}
          />

          <MetricCard
            label="Risk Signals"
            value={String(
              data.intelligence.negative_signal_count
            )}
            icon={<AlertTriangle size={20} />}
          />
        </section>

        <section className="content-grid">
          <div className="panel score-panel">
            <PanelHeader
              title="Research score"
              subtitle="Weighted analytical assessment"
            />

            <div className="score-ring">
              <div>
                <strong>{score}</strong>
                <span>/ 100</span>
              </div>
            </div>

            <div className="score-signal">
              <span>Overall signal</span>
              <strong>
                {data.research_score.signal}
              </strong>
            </div>

            <div className="component-list">
              {Object.entries(
                data.research_score.components
              ).map(([name, value]) => (
                <div
                  className="component-row"
                  key={name}
                >
                  <span>
                    {formatLabel(name)}
                  </span>

                  <div className="progress">
                    <div
                      style={{
                        width: `${Number(value)}%`
                      }}
                    />
                  </div>

                  <strong>{value}</strong>
                </div>
              ))}
            </div>
          </div>

          <div className="panel">
            <PanelHeader
              title="Intelligence signals"
              subtitle={`${data.intelligence.signal_count} detected signals`}
            />

            <div className="signal-list">
              {data.intelligence.signals.map(
                (signal) => (
                  <div
                    className="signal-card"
                    key={signal.code}
                  >
                    <div
                      className={`signal-icon ${
                        signal.direction ===
                        "POSITIVE"
                          ? "positive"
                          : "negative"
                      }`}
                    >
                      {signal.direction ===
                      "POSITIVE" ? (
                        <TrendingUp size={18} />
                      ) : (
                        <TrendingDown size={18} />
                      )}
                    </div>

                    <div>
                      <strong>
                        {signal.title}
                      </strong>

                      <p>
                        {signal.description}
                      </p>

                      <small>
                        Confidence{" "}
                        {Number(
                          signal.confidence
                        ) * 100}
                        %
                      </small>
                    </div>
                  </div>
                )
              )}
            </div>
          </div>
        </section>

        <section className="panel">
          <PanelHeader
            title="Financial trends"
            subtitle="Historical direction and consistency"
          />

          <div className="trend-table">
            <div className="trend-header">
              <span>Metric</span>
              <span>Direction</span>
              <span>Change</span>
              <span>Consistency</span>
              <span>Periods</span>
            </div>

            {data.financial_trends.map(
              (trend) => (
                <div
                  className="trend-row"
                  key={trend.metric}
                >
                  <strong>
                    {formatLabel(trend.metric)}
                  </strong>

                  <span
                    className={
                      trend.direction ===
                      "INCREASING"
                        ? "positive-text"
                        : trend.direction ===
                          "DECREASING"
                        ? "negative-text"
                        : ""
                    }
                  >
                    {trend.direction}
                  </span>

                  <span>
                    {trend.average_change}
                  </span>

                  <span>
                    {trend.consistency}
                  </span>

                  <span>
                    {trend.observations}
                  </span>
                </div>
              )
            )}
          </div>
        </section>

        <section className="observation-grid">
          <ObservationPanel
            title="Financial"
            icon={<CircleDollarSign size={19} />}
            items={data.observations.financial}
          />

          <ObservationPanel
            title="Market"
            icon={<TrendingUp size={19} />}
            items={data.observations.market}
          />

          <ObservationPanel
            title="Risk"
            icon={<AlertTriangle size={19} />}
            items={data.observations.risk}
          />

          <ObservationPanel
            title="Ownership"
            icon={<Building2 size={19} />}
            items={data.observations.ownership}
          />
        </section>

        <section className="panel evidence-panel">
          <PanelHeader
            title="Evidence"
            subtitle="Research provenance"
          />

          {data.evidence.map((item) => (
            <div
              className="evidence-row"
              key={item.reference}
            >
              <ShieldCheck size={20} />

              <div>
                <strong>{item.title}</strong>
                <span>
                  {item.source_name} ·{" "}
                  {item.source_type}
                </span>
              </div>

              <span>
                Reliability Tier{" "}
                {item.reliability_tier}
              </span>
            </div>
          ))}
        </section>
      </main>
    </div>
  )
}

function MetricCard({
  label,
  value,
  suffix,
  icon
}: {
  label: string
  value: string
  suffix?: string
  icon: React.ReactNode
}) {
  return (
    <div className="metric-card">
      <div className="metric-icon">
        {icon}
      </div>

      <span>{label}</span>

      <strong>
        {value}
        {suffix && (
          <small>{suffix}</small>
        )}
      </strong>
    </div>
  )
}

function PanelHeader({
  title,
  subtitle
}: {
  title: string
  subtitle: string
}) {
  return (
    <div className="panel-header">
      <div>
        <h3>{title}</h3>
        <span>{subtitle}</span>
      </div>

      <ChevronRight size={18} />
    </div>
  )
}

function ObservationPanel({
  title,
  icon,
  items
}: {
  title: string
  icon: React.ReactNode
  items: string[]
}) {
  return (
    <div className="panel observation-panel">
      <div className="observation-title">
        {icon}
        <h3>{title}</h3>
      </div>

      {items.map((item) => (
        <div
          className="observation"
          key={item}
        >
          {item}
        </div>
      ))}
    </div>
  )
}

function formatLabel(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(
      /\b\w/g,
      (character) => character.toUpperCase()
    )
}

export default App
