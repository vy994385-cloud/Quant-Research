/**
 * Deep financial insights: per-series comparable reporting-period views,
 * per-metric observations (REPORTED / DERIVED / UNAVAILABLE), and
 * explicit derivations. Descriptive only — never a trade signal.
 */

import type {
  DeepFinancialInsights,
  DeepMetricObservation,
  DeepFinancialSeries,
} from "../api/types"
import { formatIso } from "../lib/format"
import { EmptyCopy, PanelHead, Tag } from "./ui"

function metricTone(type: string): "green" | "red" | "amber" | "blue" | "slate" {
  switch (type) {
    case "REPORTED":
      return "green"
    case "DERIVED":
      return "blue"
    case "UNAVAILABLE":
      return "amber"
    default:
      return "slate"
  }
}

function DeltaBadge({ obs }: { obs: DeepMetricObservation }) {
  if (obs.delta_pct === null) return null

  const pct = Number(obs.delta_pct)
  const isPositive = pct > 0
  const tone = isPositive ? "green" : pct < 0 ? "red" : "slate"

  return (
    <span className={`tag ${tone}`}>
      {isPositive ? "+" : ""}
      {(pct * 100).toFixed(1)}%
    </span>
  )
}

function ObservationRow({ obs }: { obs: DeepMetricObservation }) {
  return (
    <div className="obs-row">
      <div className="obs-head">
        <strong>{obs.metric}</strong>
        <Tag text={obs.observation_type} tone={metricTone(obs.observation_type)} />
        <DeltaBadge obs={obs} />
      </div>
      {obs.value !== null && (
        <div className="obs-value">{obs.value}</div>
      )}
      {obs.previous_value !== null && (
        <div className="obs-previous">prev: {obs.previous_value}</div>
      )}
      {obs.derivation && (
        <div className="obs-derivation">{obs.derivation}</div>
      )}
    </div>
  )
}

function SeriesCard({ series }: { series: DeepFinancialSeries }) {
  return (
    <div className="panel series-card">
      <PanelHead
        title={`${series.period_type} / ${series.consolidation}`}
        subtitle={`${series.period_count} periods | ${series.metrics.length} metrics`}
      />
      <div className="series-meta">
        {series.period_ends.map((p) => (
          <span key={p} className="tag slate">{formatIso(p)}</span>
        ))}
      </div>
    </div>
  )
}

export default function DeepFinancialsPanel({
  insights,
}: {
  insights: DeepFinancialInsights | null
}) {
  if (insights === null) {
    return (
      <section id="deep-financial" className="section-anchor">
        <EmptyCopy text="No deep financial insights are available for this company." />
      </section>
    )
  }

  const reported = insights.observations.filter(
    (o) => o.observation_type === "REPORTED",
  )
  const derived = insights.observations.filter(
    (o) => o.observation_type === "DERIVED",
  )
  const unavailable = insights.observations.filter(
    (o) => o.observation_type === "UNAVAILABLE",
  )

  return (
    <section id="deep-financial" className="section-anchor">
      <PanelHead
        title="Deep financial insights"
        subtitle="Per-period comparable series with explicit derivations"
      />

      {insights.comparability_notes.length > 0 && (
        <div className="comparability-notes">
          {insights.comparability_notes.map((note) => (
            <div className="note-row" key={note}>
              <strong>Comparability note:</strong> {note}
            </div>
          ))}
        </div>
      )}

      <div className="series-grid">
        {insights.series.map((s) => (
          <SeriesCard key={s.series_id} series={s} />
        ))}
      </div>

      <div className="metric-summary">
        <div className="tag green">{reported.length} reported</div>
        <div className="tag blue">{derived.length} derived</div>
        <div className="tag amber">{unavailable.length} unavailable</div>
      </div>

      <div className="observations-list">
        {insights.observations.map((obs) => (
          <ObservationRow key={obs.observation_id} obs={obs} />
        ))}
      </div>
    </section>
  )
}
