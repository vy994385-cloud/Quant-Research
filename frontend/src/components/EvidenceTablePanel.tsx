/**
 * EVIDENCE — professional research table of the point-in-time record.
 *
 * One deduplicated, searchable table: date, event/claim, type, verification,
 * direction, source. Visually identical events (same normalized title + date +
 * source) collapse into a single row. Selecting a row opens a side drawer with
 * the full record — body text, reliability confidence, point-in-time
 * timestamps and technical provenance.
 *
 * No raw confidence decimals, no provenance IDs in the primary view.
 */

import { useMemo, useState } from "react"
import { ChevronRight, Search } from "lucide-react"
import type {
  CompanyResearch,
  ContractEvidence,
  TimelineEntry,
} from "../api/types"
import { formatConfidence, formatIso, formatIsoShort, formatLabel, formatSourceName, formatTitle } from "../lib/format"
import { directionTone } from "../lib/signal"
import { EmptyCopy, PanelHead, Tag } from "./ui"
import Drawer from "./Drawer"
import type { Tone } from "../lib/signal"

interface EvidenceRecord {
  key: string
  date: string | null
  title: string
  description: string
  type: string
  verification: string
  verificationTone: Tone
  semantic: string | null
  direction: string
  stance: string | null
  sourceName: string
  sourceUrl: string | null
  sourceTier: number | null
  /** Technical layer: shown only when expanded. */
  provenanceId: string | null
  checksum: string | null
  timestamps: Array<[string, string]>
  confidence: string | null
}

function normalizeTitle(title: string): string {
  return title.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim()
}

function timelineVerificationTone(status: string): Tone {
  switch (status) {
    case "CONFIRMED": return "green"
    case "CONTRADICTED": return "red"
    case "ALLEGED":
    case "UNVERIFIED":
    case "REPORTED": return "amber"
    default: return "slate"
  }
}

function reliabilityTone(reliability: string): Tone {
  switch (reliability) {
    case "VALIDATED": return "green"
    case "ACQUIRED": return "blue"
    case "INFERRED": return "amber"
    default: return "slate"
  }
}

function recordsFromTimeline(entries: TimelineEntry[], symbol?: string): EvidenceRecord[] {
  return entries.map((entry) => ({
    key: entry.entry_id,
    date: entry.timeline_at ?? entry.published_at ?? null,
    title: formatTitle(entry.title, symbol),
    description: entry.description,
    type: formatLabel(entry.intel_category),
    verification: entry.verification_status,
    verificationTone: timelineVerificationTone(entry.verification_status),
    semantic: entry.semantic_category,
    direction: entry.direction && entry.direction !== "UNKNOWN" ? entry.direction : "",
    stance: entry.stance && entry.stance !== "NEUTRAL" ? entry.stance : null,
    sourceName: formatSourceName(entry.source.source_name),
    sourceUrl: entry.source.source_url,
    sourceTier: entry.source.reliability_tier ?? null,
    provenanceId: entry.provenance_id,
    checksum: entry.checksum,
    timestamps: [
      ["Published", entry.published_at],
      ["Available", entry.available_at],
      ["Effective", entry.effective_at],
    ].filter((p): p is [string, string] => Boolean(p[1])),
    confidence: null,
  }))
}

function recordsFromEvidence(items: ContractEvidence[]): EvidenceRecord[] {
  return items.map((item) => ({
    key: item.evidence_id,
    date: item.observation_at,
    title: formatTitle(item.title, item.symbol),
    description: item.explanation,
    type: formatLabel(item.evidence_type),
    verification: item.reliability,
    verificationTone: reliabilityTone(item.reliability),
    semantic: null,
    direction: item.direction,
    stance: null,
    sourceName: formatSourceName(item.source_ids[0]),
    sourceUrl: null,
    sourceTier: null,
    provenanceId: item.provenance_ids[0] ?? null,
    checksum: null,
    timestamps: [["Observed", item.observation_at]].filter(
      (p): p is [string, string] => Boolean(p[1]),
    ),
    confidence: item.confidence,
  }))
}

/** Collapse visually identical events across feeds. */
function dedupeRecords(records: EvidenceRecord[]): EvidenceRecord[] {
  const byIdentity = new Map<string, EvidenceRecord>()

  for (const record of records) {
    const day = record.date ? record.date.slice(0, 10) : ""
    const identity = `${normalizeTitle(record.title)}|${day}|${record.sourceName}`
    const existing = byIdentity.get(identity)

    if (!existing) {
      byIdentity.set(identity, record)
      continue
    }
    // Merge: keep the richer body text and first-seen identity.
    if (!existing.description && record.description) {
      byIdentity.set(identity, { ...existing, description: record.description })
    }
  }

  // Newest first. Within one timestamp, dated events read before the bulk
  // feature/signal records that share it, so the top of the table stays
  // scannable; derived records remain fully listed below them.
  const typeWeight = (record: EvidenceRecord): number =>
    record.type === "Feature" || record.type === "Signal" ? 1 : 0
  return [...byIdentity.values()].sort((a, b) => {
    if (!a.date && !b.date) return a.title.localeCompare(b.title)
    if (!a.date) return 1
    if (!b.date) return -1
    const byDate = b.date.localeCompare(a.date)
    if (byDate !== 0) return byDate
    return typeWeight(a) - typeWeight(b) || a.title.localeCompare(b.title)
  })
}

type DirectionFilter = "ALL" | "POSITIVE" | "NEGATIVE" | "NEUTRAL"

function EvidenceDetail({ record }: { record: EvidenceRecord }) {
  return (
    <div className="evidence-detail">
      {record.description && <p className="evidence-detail-desc">{record.description}</p>}
      <dl className="evidence-detail-meta">
        {record.confidence && (
          <div>
            <dt>Reliability confidence</dt>
            <dd>{formatConfidence(record.confidence)}</dd>
          </div>
        )}
        {record.semantic && (
          <div>
            <dt>Basis</dt>
            <dd>{formatLabel(record.semantic)}</dd>
          </div>
        )}
        {record.stance && (
          <div>
            <dt>Stance</dt>
            <dd>{formatLabel(record.stance)}</dd>
          </div>
        )}
        {record.sourceTier !== null && (
          <div>
            <dt>Source tier</dt>
            <dd>{record.sourceTier}</dd>
          </div>
        )}
        {record.timestamps.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{formatIso(value)}</dd>
          </div>
        ))}
        <div>
          <dt>Source</dt>
          <dd>
            {record.sourceUrl ? (
              <a href={record.sourceUrl} target="_blank" rel="noopener noreferrer">
                {record.sourceName}
              </a>
            ) : (
              record.sourceName
            )}
          </dd>
        </div>
      </dl>
      {(record.provenanceId || record.checksum) && (
        <p className="evidence-provenance mono">
          {record.provenanceId && <span>provenance {record.provenanceId} </span>}
          {record.checksum && <span>checksum {record.checksum}</span>}
        </p>
      )}
    </div>
  )
}

function RecordRow({
  record,
  onOpen,
}: {
  record: EvidenceRecord
  onOpen: (key: string) => void
}) {
  return (
    <tr className="evidence-row">
      <td className="evidence-date">{record.date ? formatIsoShort(record.date) : "\u2014"}</td>
      <td className="evidence-event">
        <button
          type="button"
          className="evidence-expand"
          onClick={() => onOpen(record.key)}
          aria-haspopup="dialog"
          title="Open full evidence record"
        >
          <ChevronRight size={13} aria-hidden />
          <span>{record.title}</span>
        </button>
      </td>
      <td className="evidence-type">{record.type}</td>
      <td className="evidence-verification">
        <Tag text={formatLabel(record.verification)} tone={record.verificationTone} />
      </td>
      <td className="evidence-direction">
        {record.direction ? (
          <Tag text={formatLabel(record.direction)} tone={directionTone(record.direction)} />
        ) : (
          "\u2014"
        )}
      </td>
      <td className="evidence-source">
        {record.sourceName}
      </td>
    </tr>
  )
}

const DIRECTION_FILTERS: DirectionFilter[] = ["ALL", "POSITIVE", "NEGATIVE", "NEUTRAL"]

export default function EvidenceTablePanel({ data }: { data: CompanyResearch }) {
  const [filter, setFilter] = useState<DirectionFilter>("ALL")
  const [query, setQuery] = useState("")
  const [selectedKey, setSelectedKey] = useState<string | null>(null)

  const records = useMemo(() => {
    const fromTimeline = recordsFromTimeline(data.timeline?.entries ?? [], data.company.symbol)
    const fromEvidence = [
      ...recordsFromEvidence(data.evidence.positive),
      ...recordsFromEvidence(data.evidence.negative),
      ...recordsFromEvidence(data.evidence.neutral),
    ]
    // Timeline entries are the canonical event record; standalone evidence
    // items that describe the same event are dropped as duplicates.
    return dedupeRecords([...fromTimeline, ...fromEvidence])
  }, [data])

  const filtered = useMemo(() => {
    let next = records
    if (filter !== "ALL") next = next.filter((r) => r.direction === filter)
    const needle = query.trim().toLowerCase()
    if (needle) {
      next = next.filter(
        (r) =>
          r.title.toLowerCase().includes(needle) ||
          r.description.toLowerCase().includes(needle) ||
          r.sourceName.toLowerCase().includes(needle) ||
          r.type.toLowerCase().includes(needle),
      )
    }
    return next
  }, [records, filter, query])

  const selectedRecord = useMemo(
    () => records.find((record) => record.key === selectedKey) ?? null,
    [records, selectedKey],
  )

  const counts = useMemo(() => {
    const map = new Map<string, number>()
    for (const record of records) {
      const dir = record.direction || "OTHER"
      map.set(dir, (map.get(dir) ?? 0) + 1)
    }
    return map
  }, [records])

  if (records.length === 0) {
    return (
      <section id="evidence" className="section-anchor">
        <PanelHead
          title="Evidence Record"
          subtitle="Dated events and claims with verification status and source"
        />
        <EmptyCopy text="No evidence was returned for this company at this point in time." />
      </section>
    )
  }

  return (
    <section id="evidence" className="section-anchor">
      <PanelHead
        title="Evidence Record"
        subtitle={`${records.length} dated events and claims · ${counts.get("POSITIVE") ?? 0} positive · ${counts.get("NEGATIVE") ?? 0} negative`}
      />

      <div className="evidence-filters" role="group" aria-label="Filter evidence by direction">
        {DIRECTION_FILTERS.map((option) => (
          <button
            key={option}
            type="button"
            className={`unit-btn ${filter === option ? "active" : ""}`}
            onClick={() => setFilter(option)}
            aria-pressed={filter === option}
          >
            {option === "ALL" ? "All" : formatLabel(option)}
            <span className="filter-count">
              {option === "ALL" ? records.length : option === "NEUTRAL" ? (records.length - (counts.get("POSITIVE") ?? 0) - (counts.get("NEGATIVE") ?? 0)) : (counts.get(option) ?? 0)}
            </span>
          </button>
        ))}
        <label className="evidence-search">
          <Search size={13} aria-hidden />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search events, sources…"
            aria-label="Search evidence"
          />
        </label>
      </div>

      {filtered.length === 0 ? (
        <EmptyCopy text={`No ${formatLabel(filter).toLowerCase()} evidence in this record.`} />
      ) : (
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Evidence table">
          <table className="evidence-table">
            <caption className="visually-hidden">
              Dated events and claims with type, verification, direction, and source
            </caption>
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Event / claim</th>
                <th scope="col">Type</th>
                <th scope="col">Verification</th>
                <th scope="col">Direction</th>
                <th scope="col">Source</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((record) => (
                <RecordRow key={record.key} record={record} onOpen={setSelectedKey} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Drawer
        open={selectedRecord !== null}
        onClose={() => setSelectedKey(null)}
        title="Evidence record"
        subtitle={selectedRecord ? selectedRecord.title : undefined}
      >
        {selectedRecord && <EvidenceDetail record={selectedRecord} />}
      </Drawer>
    </section>
  )
}
