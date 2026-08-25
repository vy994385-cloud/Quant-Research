/**
 * Standardized output states — VISUAL SYSTEM 3.0.
 *
 * Each state has a distinct visual treatment:
 *   Loading      quiet pulsing marker, never blocking
 *   Empty        dashed neutral outline, actionable copy
 *   Unavailable  slate — missing data is not an error
 *   Stale        amber attention without alarm
 *   Conflict     amber with explicit conflict framing
 *   Error        red hairline + honest failure class + retry
 *
 * All states share one geometry: centered, labeled, no giant blank cards.
 */

import { Activity, Building2, TriangleAlert, XCircle, Clock, HelpCircle, GitMerge } from "lucide-react"
import { ApiError } from "../api/client"

type StateIcon = React.ComponentType<{ size?: number; className?: string }>

function StateShell({
  icon: Icon,
  tone = "",
  title,
  children,
  role,
}: {
  icon: StateIcon
  tone?: string
  title: string
  children?: React.ReactNode
  role?: string
}) {
  return (
    <div className={`empty-state ${tone}`.trim()} role={role}>
      <Icon size={26} />
      <strong>{title}</strong>
      {children}
    </div>
  )
}

export function LoadingState({
  label,
  description,
}: {
  label: string
  description?: string
}) {
  return (
    <div className="loading-state" role="status">
      <Activity className="spin" size={24} />
      <strong>Loading research</strong>
      <span>{label}</span>
      {description && <span>{description}</span>}
    </div>
  )
}

export function EmptyState({
  icon: Icon = Building2,
  title,
  description,
}: {
  icon?: React.ComponentType<{ size?: number }>
  title: string
  description?: string
}) {
  return (
    <div className="empty-state">
      <Icon size={26} />
      <strong>{title}</strong>
      {description && <p>{description}</p>}
    </div>
  )
}

/** Slate state: data does not exist for this scope. Not an error. */
export function UnavailableState({
  title = "Not available",
  description,
  icon: Icon = HelpCircle,
}: {
  title?: string
  description?: string
  icon?: React.ComponentType<{ size?: number }>
}) {
  return (
    <StateShell icon={Icon} tone="unavailable" title={title}>
      {description && <p>{description}</p>}
    </StateShell>
  )
}

/** Amber state: data exists but is out of its freshness window. */
export function StaleState({
  asOf,
  description,
}: {
  asOf?: string
  description?: string
}) {
  return (
    <StateShell icon={Clock} tone="stale" title="Data may be stale">
      <p>
        {asOf ? `Last verified ${asOf}. ` : ""}
        {description ?? "Treat values as indicative until re-verified."}
      </p>
    </StateShell>
  )
}

/** Amber state: sources disagree. Both values are shown upstream. */
export function ConflictState({
  description,
}: {
  description?: string
}) {
  return (
    <StateShell icon={GitMerge} tone="conflict" title="Conflicting evidence">
      <p>{description ?? "Sources disagree on this value; both records are retained."}</p>
    </StateShell>
  )
}

/** Neutral "no results after filtering" — distinct from empty dataset. */
export function NoResultsState({ description }: { description?: string }) {
  return (
    <EmptyState
      icon={HelpCircle}
      title="No results"
      description={description ?? "Try adjusting filters or search terms."}
    />
  )
}

function ErrorDetails({ details }: { details: Record<string, unknown> }) {
  const rows = Object.entries(details)

  if (rows.length === 0) return null

  return (
    <div className="error-details">
      {rows.map(([key, value]) => (
        <span key={key}>
          <b>{key}</b>: {String(value)}
        </span>
      ))}
    </div>
  )
}

export function ErrorState({
  error,
  retryLabel,
  onRetry,
}: {
  error: ApiError | string
  retryLabel?: string
  onRetry?: () => void
}) {
  const message =
    typeof error === "string" ? error : error.message

  const isApiError = error instanceof ApiError

  // Honest framing per failure class: a server-side data problem is not a
  // connectivity outage, and neither is a contract-level rejection.
  let heading = "Research could not be generated"
  let hint: string | null = null
  if (isApiError && error.code === "server_unavailable") {
    heading = "Research area unavailable"
    hint =
      "The rest of the workspace is unaffected; this area can be retried."
  } else if (isApiError && error.code === "network_error") {
    heading = "Cannot reach the research service"
  }

  return (
    <div className="empty-state error" role="alert">
      <XCircle size={26} />
      <strong>{heading}</strong>
      <p>{message}</p>
      {hint && <p className="error-hint">{hint}</p>}
      {isApiError && error.code !== "network_error" ? (
        <span className="error-code">Error code: {error.code}</span>
      ) : null}
      {isApiError ? <ErrorDetails details={error.details} /> : null}
      {onRetry ? (
        <button className="btn-primary refresh-button retry-button" onClick={onRetry}>
          {retryLabel ?? "Try again"}
        </button>
      ) : null}
    </div>
  )
}

export function DegradedAlerts({
  alerts,
  danger,
  label,
}: {
  alerts: string[]
  danger: boolean
  label: string
}) {
  if (alerts.length === 0) return null

  return (
    <div
      className={`alert-banner ${danger ? "alert-danger" : "alert-warn"}`}
      role="status"
    >
      <TriangleAlert size={16} />
      <div>
        <strong>{label}</strong>
        <ul>
          {alerts.map((alert) => (
            <li key={alert}>{alert}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}
