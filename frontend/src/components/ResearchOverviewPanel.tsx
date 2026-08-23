/**
 * RESEARCH OVERVIEW — the reading layer of the company workspace.
 *
 * Clearly distinguished sections, in order:
 *   Research context · What matters · Supporting evidence · Counter-evidence ·
 *   Research tensions · What could change · Uncertainty / unknowns ·
 *   Coverage summary.
 *
 * Neutral evidence language throughout: no company score, no weighted
 * evidence score, no positive/negative weighting, no recommendation, and no
 * "good/bad company" verdicts. Direction counts are recorded facts with an
 * explicit disclaimer.
 */

import { useState } from "react"
import type { CompanyResearch } from "../api/types"
import {
  formatIso,
  formatIsoShort,
  formatSourceNote,
  formatTitle,
  humanizeNarrative,
  splitMeasureUncertainty,
} from "../lib/format"
import { PanelHead } from "./ui"

const FEATURE_MEASURE = /^validated (research measure|feature):/i
const RECENT_CHANGE_COUNT = 4
const KEY_OBSERVATION_COUNT = 4
/** Narrative lists longer than this collapse behind a show-all control. */
const NARRATIVE_PREVIEW_COUNT = 8

function isFeatureMeasure(value: string): boolean {
  return FEATURE_MEASURE.test(value)
}

/** Most recent dated events, newest first — "what changed" summary row set. */
function recentChanges(data: CompanyResearch): Array<{ key: string; date: string | null; title: string }> {
  const entries = [...(data.timeline?.entries ?? [])]
    .sort((a, b) =>
      (b.timeline_at ?? b.published_at ?? "").localeCompare(
        a.timeline_at ?? a.published_at ?? "",
      ),
    )
    .slice(0, RECENT_CHANGE_COUNT)
  return entries.map((entry) => ({
    key: entry.entry_id,
    date: entry.timeline_at ?? entry.published_at,
    title: formatTitle(entry.title, entry.symbol),
  }))
}

function RecentChangesBlock({
  changes,
}: {
  changes: Array<{ key: string; date: string | null; title: string }>
}) {
  if (changes.length === 0) return null
  return (
    <div className="overview-section">
      <h4>What changed</h4>
      <ul className="overview-changes">
        {changes.map((change) => (
          <li key={change.key}>
            <span className="feed-date">
              {change.date ? formatIsoShort(change.date) : "—"}
            </span>
            <span className="overview-change-title">{change.title}</span>
          </li>
        ))}
      </ul>
      <p className="coverage-link-note">
        Full event history is in <a href="#company-events">Events</a>.
      </p>
    </div>
  )
}

function NarrativeList({
  label,
  items,
  emptyText,
}: {
  label: string
  items: string[]
  emptyText: string
}) {
  const [expanded, setExpanded] = useState(false)
  const visible = expanded ? items : items.slice(0, NARRATIVE_PREVIEW_COUNT)
  const hidden = items.length - visible.length
  return (
    <div className="narrative-col">
      <h4>
        {label}
        {items.length > 0 && <span className="narrative-count">{items.length}</span>}
      </h4>
      {items.length === 0 ? (
        <p className="narrative-empty">{emptyText}</p>
      ) : (
        <>
          <ul>
            {visible.map((item) => (
              <li key={item}>{humanizeNarrative(formatTitle(item))}</li>
            ))}
          </ul>
          {hidden > 0 && (
            <button
              type="button"
              className="narrative-toggle"
              onClick={() => setExpanded(true)}
            >
              Show {hidden} more item{hidden !== 1 ? "s" : ""}
            </button>
          )}
        </>
      )}
    </div>
  )
}

/** Chip cloud for uniform "measure has limited evidence reliability" items. */
const MEASURE_CHIP_PREVIEW = 12

function UncertaintyBlock({ items }: { items: string[] }) {
  const [expanded, setExpanded] = useState(false)
  const { measures, other } = splitMeasureUncertainty(items)
  const visibleMeasures = expanded ? measures : measures.slice(0, MEASURE_CHIP_PREVIEW)
  const hiddenMeasures = measures.length - visibleMeasures.length

  return (
    <div className="narrative-col">
      <h4>
        Uncertainty &amp; unknowns
        {items.length > 0 && <span className="narrative-count">{items.length}</span>}
      </h4>
      {items.length === 0 ? (
        <p className="narrative-empty">
          No unresolved uncertainties were flagged by this research pass.
        </p>
      ) : (
        <>
          {measures.length > 0 && (
            <div className="uncertainty-measures">
              <p className="uncertainty-lead">
                {measures.length} recorded measure{measures.length !== 1 ? "s" : ""} have
                limited evidence reliability:
              </p>
              <ul className="measure-chips">
                {visibleMeasures.map((name) => (
                  <li key={name} className="measure-chip">
                    {name}
                  </li>
                ))}
              </ul>
              {hiddenMeasures > 0 && (
                <button
                  type="button"
                  className="narrative-toggle"
                  onClick={() => setExpanded(true)}
                >
                  Show {hiddenMeasures} more measure{hiddenMeasures !== 1 ? "s" : ""}
                </button>
              )}
            </div>
          )}
          {other.length > 0 && (
            <ul>
              {other.map((item) => (
                <li key={item}>{humanizeNarrative(formatTitle(item))}</li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}

export default function ResearchOverviewPanel({ data }: { data: CompanyResearch }) {
  const narrative = data.narrative
  const assessment = data.assessment
  const pit = data.point_in_time
  const evidenceCounts = data.evidence
  const status = data.research_status

  if (!narrative) {
    return (
      <section className="section-anchor" id="research-overview">
        <PanelHead title="Research Overview" subtitle="What the recorded evidence shows at this point in time" />
        <p className="empty-copy">No research overview was produced for this company.</p>
      </section>
    )
  }

  const rawSupporting = narrative.supporting_evidence
  const measures = rawSupporting.filter(isFeatureMeasure)
  const supporting = rawSupporting.filter((item) => !isFeatureMeasure(item))

  const coverageStats: Array<{ label: string; value: string | number }> = [
    { label: "Evidence items", value:
      (evidenceCounts.positive_count ?? 0) +
      (evidenceCounts.negative_count ?? 0) +
      (evidenceCounts.neutral_count ?? 0) },
    { label: "Research observations", value: data.signals.length },
    { label: "Financial records", value: data.data_quality.financial_record_count },
    { label: "Sources", value: data.source_statuses.length },
    { label: "Coverage entries", value: status?.coverage.item_count ?? 0 },
    { label: "Event categories without coverage", value: status?.coverage.missing_categories.length ?? 0 },
  ]

  return (
    <section className="section-anchor" id="research-overview">
      <PanelHead
        title="Research Overview"
        subtitle={`What the recorded evidence shows as of ${pit.effective_as_of ? formatIso(pit.effective_as_of) : "the requested point in time"}`}
      />

      {/* 1. Research context */}
      <div className="overview-section overview-context">
        <h4>Research context</h4>
        <p className="overview-thesis">{narrative.thesis || assessment.thesis || "\u2014"}</p>
        <div className="overview-chips">
          <span className="tag blue">
            {pit.pit_checks_passed ? "Point-in-time verified" : "PIT checks failed"}
          </span>
          <span className="tag slate">
            Evidence window: {pit.evidence_included} included · {pit.future_evidence_excluded} future excluded
          </span>
          <span className="tag slate">{data.company.as_of ? `Requested as of ${data.company.as_of.slice(0, 10)}` : ""}</span>
        </div>
        <p className="overview-direction-note">
          Recorded evidence currently includes {evidenceCounts.positive_count} positive-direction,{" "}
          {evidenceCounts.negative_count} negative-direction and {evidenceCounts.neutral_count} neutral
          item(s). This is a count of recorded evidence, not a score or a recommendation.
        </p>
      </div>

      {/* 2. What changed — latest dated events in the record */}
      <RecentChangesBlock changes={recentChanges(data)} />

      {/* 3. Key observations — headline register entries */}
      {data.signals.length > 0 && (
        <div className="overview-section">
          <h4>
            Key observations
            <span className="narrative-count">{data.signals.length}</span>
          </h4>
          <ul className="overview-key-observations">
            {data.signals.slice(0, KEY_OBSERVATION_COUNT).map((signal) => (
              <li key={signal.signal_id}>{formatTitle(signal.title, signal.symbol)}</li>
            ))}
          </ul>
          {data.signals.length > KEY_OBSERVATION_COUNT && (
            <p className="coverage-link-note">
              All {data.signals.length} observations are itemised in the register below.
            </p>
          )}
        </div>
      )}

      {/* 4. Source notes behind the context */}
      {narrative.strongest_evidence.length > 0 && (
        <div className="overview-section">
          <h4>Source notes</h4>
          <ul className="overview-matters">
            {narrative.strongest_evidence.map((item) => (
              <li key={item}>{formatSourceNote(item)}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 3+4. Supporting / counter-evidence */}
      {(supporting.length > 0 || measures.length > 0 || narrative.contradicting_evidence.length > 0) && (
        <div className="overview-narrative-grid two-col">
          <NarrativeList
            label="Supporting evidence"
            items={supporting}
            emptyText="No supporting evidence beyond validated measures has been recorded."
          />
          <NarrativeList
            label="Counter-evidence"
            items={narrative.contradicting_evidence}
            emptyText="No counter-evidence has been recorded."
          />
        </div>
      )}
      {measures.length > 0 && (
        <p className="measure-rollup">
          {measures.length} validated research measure(s) across financial and market
          measures — itemised in the <a href="#evidence">Evidence Record</a> below.
        </p>
      )}

      {/* 5. Research tensions */}
      {(assessment.conflict_detected || narrative.has_conflict) && (
        <div className="overview-tensions" role="note">
          <h4>Research tensions</h4>
          <p>
            Supporting and counter-evidence are both recorded for this company. The record
            holds this conflict openly rather than resolving it; review both lists above
            before weighing direction.
          </p>
        </div>
      )}

      {/* 6. What could change */}
      {narrative.what_could_change_thesis.length > 0 && (
        <div className="overview-section">
          <h4>What could change this context</h4>
          <ul className="overview-watchlist">
            {narrative.what_could_change_thesis.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 7. Uncertainty / unknowns */}
      {(narrative.uncertainty.length > 0 || narrative.evidence_gaps.length > 0 || narrative.key_risks.length > 0) && (
        <div className="overview-narrative-grid two-col">
          <UncertaintyBlock items={[...narrative.uncertainty, ...narrative.evidence_gaps]} />
          <NarrativeList
            label="Recorded risks"
            items={narrative.key_risks}
            emptyText="No risks were recorded from the evidence."
          />
        </div>
      )}

      {/* 8. Coverage summary */}
      <div className="overview-coverage-summary">
        <h4>Coverage summary</h4>
        <dl className="coverage-stat-strip">
          {coverageStats.map((stat) => (
            <div key={stat.label} className="coverage-stat">
              <dd>{stat.value}</dd>
              <dt>{stat.label}</dt>
            </div>
          ))}
        </dl>
        <p className="coverage-link-note">
          Full availability detail — limited, missing, stale, insufficient and conflicting —
          is in <a href="#data-coverage">Coverage</a>.
        </p>
      </div>

      <p className="overview-disclaimer">
        Direction describes recorded evidence; it is not a company score or recommendation.
      </p>
    </section>
  )
}
