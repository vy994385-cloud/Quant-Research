/**
 * CorporateActionsPanel: corporate actions from F6 /corporate-actions endpoint.
 * Shows dividends, buybacks, splits with dates and provenance.
 * Evidence-first: no fabricated content.
 */

import { useEffect, useState } from "react"
import { Landmark } from "lucide-react"
import { fetchCorporateActions, ApiError } from "../api/client"
import type { CompanyCorporateActionsResponse, CorporateActionItem } from "../api/types"
import { formatIso, formatLabel } from "../lib/format"
import { Tag } from "../components/ui"

function actionTone(t: string): "green" | "red" | "slate" {
  if (t === "DIVIDEND") return "green"
  if (t === "BUYBACK") return "green"
  if (t === "SPLIT" || t === "BONUS") return "slate"
  return "slate"
}

function ActionCard({ item }: { item: CorporateActionItem }) {
  return (
    <div className="ca-item">
      <div className="ca-item-head">
        <Tag text={formatLabel(item.action_type)} tone={actionTone(item.action_type)} />
        {item.source_name && <span className="ca-source">{item.source_name}</span>}
      </div>
      <strong>{item.title}</strong>
      {item.description && <p className="ca-desc">{item.description}</p>}
      <div className="ca-dates">
        {item.announcement_date && <span>Announced: {formatIso(item.announcement_date)}</span>}
        {item.effective_date && <span>Effective: {formatIso(item.effective_date)}</span>}
        {item.record_date && <span>Record: {formatIso(item.record_date)}</span>}
      </div>
      <div className="ca-meta">
        {item.value && <span>Value: {item.value}</span>}
        {item.ratio && <span>Ratio: {item.ratio}</span>}
      </div>
      {item.source_url && (
        <a className="ca-link" href={item.source_url} target="_blank" rel="noopener noreferrer">
          Source
        </a>
      )}
    </div>
  )
}

export default function CorporateActionsPanel({ symbol, asOf }: { symbol: string; asOf?: string }) {
  const [data, setData] = useState<CompanyCorporateActionsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [fetchTarget, setFetchTarget] = useState({ symbol, asOf })

  if (fetchTarget.symbol !== symbol || fetchTarget.asOf !== asOf) {
    setFetchTarget({ symbol, asOf })
    setData(null)
    setError(null)
    setLoading(true)
  }

  useEffect(() => {
    let cancelled = false
    fetchCorporateActions(symbol, asOf)
      .then((res) => { if (!cancelled) setData(res) })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load corporate actions")
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [symbol, asOf])

  if (loading) return <div className="panel-loading"><Landmark className="spin" size={18} /> Loading corporate actions...</div>
  if (error) return <div className="panel-error"><Landmark size={18} /> {error}</div>

  const ca = data?.corporate_actions
  if (!ca || ca.item_count === 0) {
    return (
      <div className="panel">
        <div className="panel-head"><h3>Corporate Actions</h3></div>
        <div className="panel-empty"><Landmark size={18} /> No corporate actions available for this company.</div>
      </div>
    )
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <h3>Corporate Actions</h3>
        <span>{ca.item_count} actions</span>
      </div>
      <div className="ca-list">
        {ca.items.map((item) => (
          <ActionCard key={item.action_id} item={item} />
        ))}
      </div>
      {ca.notes.length > 0 && (
        <div className="panel-notes">
          {ca.notes.map((n, i) => <div key={i}>{n}</div>)}
        </div>
      )}
    </div>
  )
}
