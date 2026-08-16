/**
 * Signals: the full point-in-time research signal ledger, grouped by
 * category with direction, severity, confidence, and supporting context.
 */

import type { CompanyResearch } from "../api/types"
import { formatConfidence, formatEvidenceObservation, formatLabel } from "../lib/format"
import { EmptyCopy, Tag } from "./ui"
import { signalTone } from "../lib/signal"

export default function SignalsPanel({
  data,
}: {
  data: CompanyResearch
}) {
  const signals = data.signals

  const byCategory = new Map<string, typeof signals>()

  for (const signal of signals) {
    const bucket = byCategory.get(signal.category) ?? []
    bucket.push(signal)
    byCategory.set(signal.category, bucket)
  }

  const categories = [...byCategory.entries()].sort(([a], [b]) =>
    a.localeCompare(b),
  )

  if (signals.length === 0) {
    return (
      <section id="signals" className="section-anchor">
        <div className="panel">
          <EmptyCopy text="No research signals were produced for this company." />
        </div>
      </section>
    )
  }

  return (
    <section id="signals" className="section-anchor">
      {categories.map(([category, items]) => (
        <div className="panel signal-group" key={category}>
          <div className="panel-head">
            <h3>{formatLabel(category)}</h3>
            <span>
              {items.length} signal{items.length === 1 ? "" : "s"}
            </span>
          </div>
          <div className="signal-list">
            {items.map((signal) => (
              <article className="signal-row" key={signal.signal_id}>
                <div className="signal-row-head">
                  <strong>{signal.title}</strong>
                  <span className="signal-tags">
                    <Tag
                      text={formatLabel(signal.direction)}
                      tone={signalTone(signal.direction)}
                    />
                    <Tag text={signal.severity} tone="slate" />
                    <Tag
                      text={`${formatConfidence(signal.confidence)} confidence`}
                      tone="slate"
                    />
                  </span>
                </div>
                <p>{signal.explanation}</p>
                <div className="signal-meta">
                  <span>Observed {formatEvidenceObservation(signal.observation_at)}</span>
                  {signal.supporting_features.length > 0 ? (
                    <span>
                      Features: {signal.supporting_features.map(formatLabel).join(", ")}
                    </span>
                  ) : null}
                  {signal.supporting_metrics.length > 0 ? (
                    <span>
                      Metrics: {signal.supporting_metrics.map(formatLabel).join(", ")}
                    </span>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </div>
      ))}
    </section>
  )
}
