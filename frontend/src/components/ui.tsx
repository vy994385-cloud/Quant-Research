/**
 * Small shared UI primitives reused across dashboard sections.
 */

import type { ReactNode } from "react"
import type { Tone } from "../lib/signal"

export function Tag({
  text,
  tone,
}: {
  text: string
  tone: Tone
}) {
  return <span className={`tag ${tone}`}>{text}</span>
}

export function SectionTitle({
  eyebrow,
  title,
  detail,
}: {
  eyebrow: string
  title: string
  detail: string
}) {
  return (
    <header className="section-title">
      <span>{eyebrow}</span>
      <h2>{title}</h2>
      <p>{detail}</p>
    </header>
  )
}

export function PanelHead({
  title,
  subtitle,
}: {
  title: string
  subtitle: string
}) {
  return (
    <div className="panel-head">
      <div>
        <h3>{title}</h3>
        <span>{subtitle}</span>
      </div>
    </div>
  )
}

export function EmptyCopy({ text }: { text: string }) {
  return <p className="empty-copy">{text}</p>
}

export function Metric({
  label,
  value,
  detail,
  icon,
  tone = "",
}: {
  label: string
  value: string
  detail: string
  icon: ReactNode
  tone?: string
}) {
  return (
    <article className={`metric ${tone}`}>
      <div>
        {icon}
        <span>{label}</span>
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  )
}

export function ScoreDonut({
  value,
  color,
  suffix,
}: {
  value: number
  color: string
  suffix?: string
}) {
  const clamped = Math.max(0, Math.min(100, value))

  return (
    <div
      className="score-donut"
      style={{
        background: `conic-gradient(${color} ${clamped}%, #e5ebf1 0)`,
      }}
      role="img"
      aria-label={`Score ${clamped.toFixed(0)} out of 100`}
    >
      <div className="score-donut-inner">
        <strong>{clamped.toFixed(0)}</strong>
        {suffix ? <span>{suffix}</span> : null}
      </div>
    </div>
  )
}
