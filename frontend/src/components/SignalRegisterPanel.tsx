/**
 * RESEARCH OBSERVATIONS — dense professional register.
 *
 * One row per recorded observation:
 *   Observation | Domain | Period | Direction | Reliability | Evidence
 *
 * Human-readable language only. Raw values ("240097600000.0",
 * "66.666666666666...") never reach this table; confidence is percent-
 * formatted and severity is shown as a restrained tag.
 */

import { Fragment, useMemo, useState } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"
import type { CompanyResearch } from "../api/types"
import type { ContractSignal } from "../api/types"
import { formatConfidence, formatEvidenceObservation, formatLabel, formatTitle } from "../lib/format"
import { directionTone } from "../lib/signal"
import { EmptyCopy, FilterChips, PanelHead, Tag } from "./ui"

function directionLabel(direction: string): string {
  if (!direction) return "\u2014"
  return formatLabel(direction)
}

export default function SignalRegisterPanel({ data }: { data: CompanyResearch }) {
  const signals: ContractSignal[] = data.signals
  const [category, setCategory] = useState<string>("all")
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const categories = useMemo(() => {
    const counts = new Map<string, number>()
    for (const signal of signals) {
      counts.set(signal.category, (counts.get(signal.category) ?? 0) + 1)
    }
    return [...counts.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [signals])

  if (signals.length === 0) {
    return (
      <div className="section-anchor" id="signals">
        <PanelHead
          title="Key observations"
          subtitle="Observations derived from the evidence record"
        />
        <EmptyCopy text="No research observations were produced for this company." />
      </div>
    )
  }

  const visible =
    category === "all"
      ? signals
      : signals.filter((signal) => signal.category === category)

  return (
    <div className="section-anchor" id="signals">
      <PanelHead
        title="Key observations"
        subtitle={`${signals.length} observation${signals.length !== 1 ? "s" : ""} derived from the evidence record`}
      />

      {categories.length > 1 && (
        <FilterChips
          ariaLabel="Filter observations by domain"
          options={[
            { value: "all", label: "All", count: signals.length },
            ...categories.map(([value, count]) => ({
              value,
              label: formatLabel(value),
              count,
            })),
          ]}
          value={category}
          onChange={setCategory}
        />
      )}

      {visible.length === 0 ? (
        <EmptyCopy text="No observations match the selected domain." />
      ) : (
        <div className="table-scroll">
          <table className="observations-table">
            <caption className="visually-hidden">
              Research observations with domain, period, direction and reliability
            </caption>
            <thead>
              <tr>
                <th scope="col">Observation</th>
                <th scope="col">Domain</th>
                <th scope="col">Observed</th>
                <th scope="col">Direction</th>
                <th scope="col">Reliability</th>
                <th scope="col">Evidence</th>
                <th scope="col" aria-label="Explanation" />
              </tr>
            </thead>
            <tbody>
              {visible.map((signal) => {
                const open = expandedId === signal.signal_id
                const seriesCount =
                  signal.supporting_features.length + signal.supporting_metrics.length
                return (
                  <Fragment key={signal.signal_id}>
                    <tr className={open ? "observation-row expanded" : "observation-row"}>
                      <td className="observation-cell">{formatTitle(signal.title, signal.symbol)}</td>
                      <td className="feed-type">{formatLabel(signal.category)}</td>
                      <td className="feed-date">
                        {formatEvidenceObservation(signal.observation_at)}
                      </td>
                      <td>
                        <Tag
                          text={directionLabel(signal.direction)}
                          tone={directionTone(signal.direction)}
                        />
                      </td>
                      <td className="num">{formatConfidence(signal.confidence)}</td>
                      <td className="num">
                        {seriesCount > 0 ? `${seriesCount} data series` : "\u2014"}
                      </td>
                      <td>
                        <button
                          type="button"
                          className="row-expand-btn"
                          onClick={() => setExpandedId(open ? null : signal.signal_id)}
                          aria-expanded={open}
                          aria-controls={`observation-detail-${signal.signal_id}`}
                          aria-label={open ? "Hide explanation" : "Show explanation"}
                        >
                          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        </button>
                      </td>
                    </tr>
                    {open && (
                      <tr className="observation-detail-row">
                        <td colSpan={7} id={`observation-detail-${signal.signal_id}`}>
                          <p className="observation-explanation">{signal.explanation}</p>
                          {(signal.supporting_features.length > 0 ||
                            signal.supporting_metrics.length > 0) && (
                            <p className="observation-basis mono">
                              Backed by:{" "}
                              {[...signal.supporting_features, ...signal.supporting_metrics]
                                .map((name) => formatLabel(name))
                                .join(" · ")}
                            </p>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
