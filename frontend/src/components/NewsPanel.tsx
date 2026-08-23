/**
 * NewsPanel: company news from F6 /news endpoint.
 * Shows recent news items with categories, direction, and source.
 * Evidence-first: no fabricated content, missing data shown explicitly.
 */

import { useEffect, useState } from "react"
import { Newspaper } from "lucide-react"
import { fetchCompanyNews, ApiError } from "../api/client"
import type { CompanyNewsResponse, CompanyNewsItem } from "../api/types"
import { formatIso, formatLabel } from "../lib/format"
import { directionTone } from "../lib/signal"
import { Tag } from "../components/ui"

function NewsItemCard({ item }: { item: CompanyNewsItem }) {
  return (
    <div className="news-item">
      <div className="news-item-head">
        <Tag text={formatLabel(item.category)} tone="slate" />
        <Tag text={formatLabel(item.direction)} tone={directionTone(item.direction)} />
        {item.source_name && <span className="news-source">{item.source_name}</span>}
      </div>
      <strong className="news-headline">{item.headline}</strong>
      {item.summary && <p className="news-summary">{item.summary}</p>}
      <div className="news-meta">
        {item.published_at && <span>Published: {formatIso(item.published_at)}</span>}
      </div>
      {item.source_url && (
        <a className="news-link" href={item.source_url} target="_blank" rel="noopener noreferrer">
          Source
        </a>
      )}
    </div>
  )
}

export default function NewsPanel({ symbol, asOf }: { symbol: string; asOf?: string }) {
  const [data, setData] = useState<CompanyNewsResponse | null>(null)
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
    fetchCompanyNews(symbol, asOf)
      .then((res) => { if (!cancelled) setData(res) })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load news")
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [symbol, asOf])

  if (loading) return <div className="panel-loading"><Newspaper className="spin" size={18} /> Loading news...</div>
  if (error) return <div className="panel-error"><Newspaper size={18} /> {error}</div>

  const news = data?.news
  if (!news || news.item_count === 0) {
    return (
      <div className="panel">
        <div className="panel-head"><h3>Company News</h3></div>
        <div className="panel-empty"><Newspaper size={18} /> No news available for this company.</div>
      </div>
    )
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <h3>Company News</h3>
        <span>{news.item_count} items</span>
      </div>
      <div className="news-list">
        {news.items.map((item) => (
          <NewsItemCard key={item.news_id} item={item} />
        ))}
      </div>
      {news.notes.length > 0 && (
        <div className="panel-notes">
          {news.notes.map((n, i) => <div key={i}>{n}</div>)}
        </div>
      )}
    </div>
  )
}
