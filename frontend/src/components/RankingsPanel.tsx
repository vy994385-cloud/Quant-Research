/**
 * Rankings: per-company horizon rankings (intraday / swing / long-term) with
 * evidence-coverage badges, plus a cross-company universe comparison table
 * driven by /api/v1/rankings/{horizon}.
 */

import { useEffect, useState } from "react"
import {
  BarChart3,
  ChevronDown,
  Loader2,
  TriangleAlert,
} from "lucide-react"
import { ApiError, HORIZONS, fetchUniverseRankings } from "../api/client"
import type { CompanyResearch, Ranking, UniverseRankings } from "../api/types"
import {
  formatConfidence,
  formatLabel,
  formatNumber,
} from "../lib/format"
import { EmptyCopy, PanelHead, ScoreDonut, Tag } from "./ui"
import { signalColor, signalTone } from "../lib/signal"

const HORIZON_ORDER = ["intraday", "swing", "long_term"]

function RankingCard({ ranking }: { ranking: Ranking }) {
  const degraded = ranking.missing_components.length > 0

  return (
    <article className={`panel rank-card ${degraded ? "rank-degraded" : ""}`}>
      <div className="rank-head">
        <h3>{formatLabel(ranking.horizon)}</h3>
        <Tag
          text={formatLabel(ranking.signal)}
          tone={signalTone(ranking.signal)}
        />
      </div>
      <div className="rank-body">
        <ScoreDonut
          value={Number(ranking.score)}
          color={signalColor(ranking.signal)}
        />
        <div className="rank-meta">
          <span>
            Confidence <b>{formatConfidence(ranking.confidence)}</b>
          </span>
          <span>
            Coverage <b>{formatNumber(ranking.coverage)}%</b>
          </span>
        </div>
      </div>
      {degraded ? (
        <div className="rank-degraded-note">
          <TriangleAlert size={13} />
          <span>
            Missing evidence: {ranking.missing_components.map(formatLabel).join(", ")}
          </span>
        </div>
      ) : null}
      <details className="rank-components">
        <summary>
          Component scores
          <ChevronDown size={14} />
        </summary>
        <div className="rank-components-grid">
          {Object.entries(ranking.components).map(([key, value]) => (
            <span key={key}>
              <b>{formatNumber(value)}</b>
              {formatLabel(key)}
            </span>
          ))}
        </div>
      </details>
    </article>
  )
}

export default function RankingsPanel({
  data,
}: {
  data: CompanyResearch
}) {
  const [view, setView] = useState<"company" | "universe">("company")
  const [horizon, setHorizon] = useState<string>("LONG_TERM")
  const [universe, setUniverse] = useState<UniverseRankings | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const rankings = data.rankings

  useEffect(() => {
    let cancelled = false

    if (view !== "universe") return

    fetchUniverseRankings(horizon)
      .then((response) => {
        if (cancelled) return
        setUniverse(response)
        setLoading(false)
      })
      .catch((requestError: unknown) => {
        if (cancelled) return
        setError(
          requestError instanceof ApiError
            ? `${requestError.message} (${requestError.code})`
            : "The universe comparison is unavailable.",
        )
        setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [view, horizon])

  function openUniverse() {
    setError(null)
    setLoading(true)
    setView("universe")
  }

  function selectHorizon(option: string) {
    setError(null)
    setLoading(true)
    setHorizon(option)
  }

  const results = universe?.results ?? []

  return (
    <section id="rankings" className="section-anchor">
      <div className="sub-tabs">
        <button
          className={view === "company" ? "sub-tab-active" : ""}
          onClick={() => setView("company")}
        >
          Company rankings
        </button>
        <button
          className={view === "universe" ? "sub-tab-active" : ""}
          onClick={openUniverse}
        >
          Universe comparison
        </button>
      </div>

      {view === "company" ? (
        <div className="rankings-grid">
          {HORIZON_ORDER.map((horizonKey) =>
            rankings[horizonKey] ? (
              <RankingCard key={horizonKey} ranking={rankings[horizonKey]} />
            ) : null,
          )}
        </div>
      ) : (
        <div className="panel universe-panel">
          <PanelHead
            title={`Universe rankings — ${formatLabel(horizon)}`}
            subtitle="Deterministic comparison across the supported research universe; sorted by score descending."
          />
          <div className="horizon-tabs">
            {HORIZONS.map((option) => (
              <button
                key={option}
                className={horizon === option ? "horizon-active" : ""}
                onClick={() => selectHorizon(option)}
                disabled={loading}
              >
                {formatLabel(option)}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="universe-loading">
              <Loader2 className="spin" size={18} />
              Ranking the universe at {formatLabel(horizon)}…
            </div>
          ) : error ? (
            <EmptyCopy text={error} />
          ) : (
            <div className="universe-table-wrap">
              <table className="universe-table">
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Score</th>
                    <th>Signal</th>
                    <th>Confidence</th>
                    <th>Coverage</th>
                    <th>Missing evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((result) => (
                    <tr key={result.symbol}>
                      <td>
                        <b>{result.symbol}</b>
                        <small>{result.company_name ?? ""}</small>
                      </td>
                      <td>
                        <span className="universe-score">
                          <i
                            style={{
                              width: `${Math.min(100, Number(result.score))}%`,
                              background: signalColor(result.signal),
                            }}
                          />
                          <b>{formatNumber(result.score)}</b>
                        </span>
                      </td>
                      <td>
                        <Tag
                          text={formatLabel(result.signal)}
                          tone={signalTone(result.signal)}
                        />
                      </td>
                      <td>{formatConfidence(result.confidence)}</td>
                      <td>{formatNumber(result.coverage)}%</td>
                      <td>
                        {result.missing_components.length > 0 ? (
                          <span className="missing-badge">
                            {result.missing_components.map(formatLabel).join(", ")}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="universe-footer">
            <BarChart3 size={14} />
            <span>As of {universe ? universe.as_of : "—"}</span>
          </div>
        </div>
      )}
    </section>
  )
}
