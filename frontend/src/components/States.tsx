/**
 * Loading, empty, and structured-error states for the dashboard.
 */

import { Activity, TriangleAlert, XCircle } from "lucide-react"
import { ApiError } from "../api/client"

export function LoadingState({
  label,
}: {
  label: string
}) {
  return (
    <div className="loading-state" role="status">
      <Activity className="spin" size={26} />
      <strong>Loading research</strong>
      <span>{label}</span>
    </div>
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

  return (
    <div className="empty-state error" role="alert">
      <XCircle size={28} />
      <strong>Research could not be generated</strong>
      <p>{message}</p>
      {isApiError && error.code !== "network_error" ? (
        <span className="error-code">Error code: {error.code}</span>
      ) : null}
      {isApiError ? <ErrorDetails details={error.details} /> : null}
      {onRetry ? (
        <button className="refresh-button retry-button" onClick={onRetry}>
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
