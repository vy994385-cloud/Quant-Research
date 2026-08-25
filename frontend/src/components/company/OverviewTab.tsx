/**
 * COMPANY OVERVIEW TAB — the analyst dashboard.
 *
 * Reading order:
 *   Research snapshot → What changed → Key evidence → Financial snapshot →
 *   Business evidence → Market context → Technology → Coverage limitations
 *
 * This is the understanding layer: every block summarizes its detail tab and
 * links into it. Full tables and registers never repeat here.
 */

import { useMemo } from "react"
import { ArrowRight } from "lucide-react"
import type { CompanyResearch, DeepFinancialInsights } from "../../api/types"
import {
  formatCrore,
  formatIsoShort,
  formatLabel,
  formatSourceNote,
  formatTitle,
  humanizeNarrative,
} from "../../lib/format"
import { directionTone } from "../../lib/signal"
import { Tag } from "../ui"

/** Metrics shown in the financial snapshot, in reading order. */
const SNAPSHOT_METRICS = [
  "revenue",
  "net_profit",
  "operating_cash_flow",
  "free_cash_flow",
  "total_assets",
  "total_debt",
] as const

const RATIO_SNAPSHOT_METRICS = ["operating_margin", "net_margin"] as const

const BUSINESS_AREAS = [
  { key: "business_quality", label: "Business quality" },
  { key: "competitive_position", label: "Competitive position" },
  { key: "customer_intelligence", label: "Customers" },
  { key: "management_intelligence", label: "Management" },
  { key: "capital_allocation", label: "Capital allocation" },
] as const

function latestObservation(insights: DeepFinancialInsights | null, metric: string) {
  if (!insights) return null
  let latest = null
  for (const obs of insights.observations) {
    if (obs.metric !== metric || obs.value === null || obs.observation_type === "UNAVAILABLE") continue
    if (!latest || obs.period_end > latest.period_end) latest = obs
  }
  return latest
}

function formatMetric(metric: string, raw: string | null): string {
  if (raw === null) return "\u2014"
  if ((RATIO_SNAPSHOT_METRICS as readonly string[]).includes(metric)) {
    const numeric = Number(raw)
    return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(1)}%` : "\u2014"
  }
  return formatCrore(raw)
}

export default function OverviewTab({
  data,
  onOpenTab,
}: {
  data: CompanyResearch
  onOpenTab: (tab: string) => void
}) {
  const narrative = data.narrative
  const pit = data.point_in_time
  const freshness = data.research_status?.freshness

  const changes = useMemo(() => {
    return [...(data.timeline?.entries ?? [])]
      .sort((a, b) =>
        (b.timeline_at ?? b.published_at ?? "").localeCompare(
          a.timeline_at ?? a.published_at ?? "",
        ),
      )
      .slice(0, 5)
      .map((entry) => ({
        key: entry.entry_id,
        date: entry.timeline_at ?? entry.published_at,
        title: formatTitle(entry.title, entry.symbol),
      }))
  }, [data.timeline])

  const financialSnapshot = useMemo(
    () =>
      [...SNAPSHOT_METRICS, ...RATIO_SNAPSHOT_METRICS]
        .map((metric) => {
          const obs = latestObservation(data.deep_financial_insights, metric)
          return {
            metric,
            label: formatLabel(metric),
            value: obs ? formatMetric(metric, obs.value) : null,
            periodEnd: obs?.period_end ?? null,
          }
        })
        .filter((entry) => entry.value !== null),
    [data.deep_financial_insights],
  )

  const snapshotPeriod = useMemo(() => {
    const insights = data.deep_financial_insights
    if (!insights) return null
    const ends = new Set(
      insights.observations.map((obs) => obs.period_end),
    )
    return [...ends].sort().at(-1) ?? null
  }, [data.deep_financial_insights])

  const businessAreas = useMemo(
    () =>
      BUSINESS_AREAS.map((area) => ({
        ...area,
        section: data.intelligence[area.key],
      })),
    [data.intelligence],
  )
  const supportedBusinessAreas = businessAreas.filter(
    (area) => area.section && area.section.observations.length > 0,
  )
  const limitedBusinessAreaCount =
    BUSINESS_AREAS.length - supportedBusinessAreas.length

  const market = data.intelligence.market_intelligence
  const techSections = [
    { label: "Innovation & R&D", section: data.intelligence.innovation },
    { label: "Future technology", section: data.intelligence.future_technology },
  ].filter((section) => section.section && section.section.observations.length > 0)

  const staleSources = data.source_statuses.filter((source) => source.stale).length
  const missingCategories = data.research_status?.coverage.missing_categories.length ?? 0
  const conflictDetected =
    data.assessment.conflict_detected || Boolean(narrative?.has_conflict)

  return (
    <div className="company-overview">
      {/* Research snapshot */}
      <section className="ov-block ov-snapshot">
        <h3 className="ov-heading">Research snapshot</h3>
        <p className="ov-thesis">
          {narrative?.thesis || data.assessment.thesis || "No research context was produced for this company at this point in time."}
        </p>
        <div className="ov-chips">
          <Tag
            text={pit.pit_checks_passed ? "Point-in-time verified" : "PIT checks failed"}
            tone={pit.pit_checks_passed ? "blue" : "slate"}
          />
          <Tag
            text={`Evidence window: ${pit.evidence_included} included · ${pit.future_evidence_excluded} future excluded`}
            tone="slate"
          />
          {data.assessment.research_ready && <Tag text="Research ready" tone="green" />}
          {conflictDetected && <Tag text="Conflicting evidence recorded" tone="amber" />}
        </div>
        <p className="ov-direction-note">
          Recorded evidence includes {data.evidence.positive_count} positive-direction,{" "}
          {data.evidence.negative_count} negative-direction and {data.evidence.neutral_count}{" "}
          neutral item(s). This is a count of recorded evidence, not a score or recommendation.
        </p>
      </section>

      {/* What changed */}
      {changes.length > 0 && (
        <section className="ov-block">
          <h3 className="ov-heading">
            What changed
            <button type="button" className="ov-link" onClick={() => onOpenTab("events")}>
              All events <ArrowRight size={12} />
            </button>
          </h3>
          <ul className="ov-changes">
            {changes.map((change) => (
              <li key={change.key}>
                <span className="feed-date">{change.date ? formatIsoShort(change.date) : "—"}</span>
                <span>{change.title}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Key evidence */}
      {data.signals.length > 0 && (
        <section className="ov-block">
          <h3 className="ov-heading">
            Key evidence
            <button type="button" className="ov-link" onClick={() => onOpenTab("evidence")}>
              Full record <ArrowRight size={12} />
            </button>
          </h3>
          <ul className="ov-key-evidence">
            {data.signals.slice(0, 5).map((signal) => (
              <li key={signal.signal_id}>
                <Tag
                  text={formatLabel(signal.direction)}
                  tone={directionTone(signal.direction)}
                />
                <span>{formatTitle(signal.title, signal.symbol)}</span>
                <small className="feed-type">{formatLabel(signal.category)}</small>
              </li>
            ))}
          </ul>
          {narrative && narrative.strongest_evidence.length > 0 && (
            <>
              <h4 className="ov-subheading">Source notes behind this context</h4>
              <ul className="ov-source-notes">
                {narrative.strongest_evidence.slice(0, 4).map((item) => (
                  <li key={item}>{formatSourceNote(item)}</li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}

      {/* Financial snapshot */}
      {financialSnapshot.length > 0 && (
        <section className="ov-block">
          <h3 className="ov-heading">
            Financial snapshot
            {snapshotPeriod && (
              <span className="ov-period">latest period ending {formatIsoShort(snapshotPeriod)}</span>
            )}
            <button type="button" className="ov-link" onClick={() => onOpenTab("financials")}>
              Financials <ArrowRight size={12} />
            </button>
          </h3>
          <dl className="ov-fin-grid">
            {financialSnapshot.map((entry) => (
              <div key={entry.metric} className="ov-fin-cell">
                <dt>{entry.label}</dt>
                <dd>{entry.value}</dd>
              </div>
            ))}
          </dl>
          <p className="ov-footnote">
            Values as reported or derived at each period end; full history and derivations are in
            the Financials tab.
          </p>
        </section>
      )}

      {/* Business evidence */}
      {(supportedBusinessAreas.length > 0 || limitedBusinessAreaCount > 0) && (
        <section className="ov-block">
          <h3 className="ov-heading">
            Business evidence
            <button type="button" className="ov-link" onClick={() => onOpenTab("business")}>
              Business tab <ArrowRight size={12} />
            </button>
          </h3>
          {supportedBusinessAreas.length > 0 ? (
            <ul className="ov-business-list">
              {supportedBusinessAreas.slice(0, 4).map((area) => (
                <li key={area.key}>
                  <strong>{area.label}</strong>
                  <span>
                    {humanizeNarrative(area.section!.observations[0]).length > 180
                      ? `${humanizeNarrative(area.section!.observations[0]).slice(0, 177)}…`
                      : humanizeNarrative(area.section!.observations[0])}
                  </span>
                  {area.section!.observations.length > 1 && (
                    <small className="feed-type">
                      +{area.section!.observations.length - 1} more observation
                      {area.section!.observations.length !== 2 ? "s" : ""}
                    </small>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="ov-limited">No evidence-backed business observations are recorded.</p>
          )}
          {limitedBusinessAreaCount > 0 && (
            <p className="ov-limited-line">
              {limitedBusinessAreaCount} of {BUSINESS_AREAS.length} business areas have limited
              coverage — itemised in the Business tab.
            </p>
          )}
        </section>
      )}

      {/* Market context */}
      <section className="ov-block">
        <h3 className="ov-heading">
          Market context
          <button type="button" className="ov-link" onClick={() => onOpenTab("market")}>
            Market tab <ArrowRight size={12} />
          </button>
        </h3>
        {market && market.observations.length > 0 ? (
          <ul className="ov-market-notes">
            {market.observations.slice(0, 3).map((observation) => (
              <li key={observation}>{humanizeNarrative(observation)}</li>
            ))}
          </ul>
        ) : (
          <p className="ov-limited">No market intelligence observations are currently supported.</p>
        )}
      </section>

      {/* Technology */}
      <section className="ov-block">
        <h3 className="ov-heading">
          Technology
          <button type="button" className="ov-link" onClick={() => onOpenTab("technology")}>
            Technology tab <ArrowRight size={12} />
          </button>
        </h3>
        {techSections.length > 0 ? (
          <ul className="ov-tech-list">
            {techSections.map((section) => (
              <li key={section.label}>
                <strong>{section.label}</strong>
                <span>{humanizeNarrative(section.section!.observations[0])}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="ov-limited">
            No technology or innovation activity is currently supported by recorded evidence.
          </p>
        )}
      </section>

      {/* Conflicts / Uncertainty */}
      {(conflictDetected || data.provider_failures.length > 0) && (
        <section className="ov-block">
          <h3 className="ov-heading">Conflicts &amp; Uncertainty</h3>
          <div className="ov-chips">
            {conflictDetected && (
              <Tag text="Conflicting evidence recorded" tone="amber" />
            )}
            {data.provider_failures.length > 0 && (
              <Tag
                text={`${data.provider_failures.length} provider failure${data.provider_failures.length !== 1 ? "s" : ""} isolated`}
                tone="slate"
              />
            )}
          </div>
          {data.provider_failures.length > 0 && (
            <p className="ov-limited-line">
              {data.provider_failures.length} research provider{data.provider_failures.length !== 1 ? "s" : ""} failed
              and were isolated from this snapshot ({data.provider_failures.join(", ")}).
            </p>
          )}
          {!pit.pit_checks_passed && (
            <p className="ov-pit-warning">
              Point-in-time checks did not all pass for this snapshot; review evidence timestamps
              with extra caution.
            </p>
          )}
        </section>
      )}

      {/* Coverage limitations */}
      <section className="ov-block">
        <h3 className="ov-heading">
          Research limitations
          <button type="button" className="ov-link" onClick={() => onOpenTab("coverage")}>
            Coverage matrix <ArrowRight size={12} />
          </button>
        </h3>
        <div className="ov-chips">
          <Tag
            text={
              freshness?.stale
                ? `Latest publication ${freshness.days_since_latest_published ?? "?"}d ago · stale`
                : freshness?.days_since_latest_published !== null &&
                    freshness?.days_since_latest_published !== undefined
                  ? `Updated ${freshness.days_since_latest_published}d ago`
                  : "Freshness not available"
            }
            tone={freshness?.stale ? "amber" : "green"}
          />
          {staleSources > 0 && <Tag text={`${staleSources} stale source${staleSources !== 1 ? "s" : ""}`} tone="amber" />}
          {missingCategories > 0 && (
            <Tag text={`${missingCategories} event categories without coverage`} tone="slate" />
          )}
          {data.provider_failures.length > 0 && (
            <Tag text={`${data.provider_failures.length} provider failures isolated`} tone="slate" />
          )}
          <Tag text={`${data.source_statuses.length} sources in record`} tone="slate" />
        </div>
      </section>
    </div>
  )
}
