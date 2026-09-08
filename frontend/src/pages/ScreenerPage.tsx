/**
 * RESEARCH SCREENER — backend-driven screen builder.
 *
 *   header → field catalog → filter builder → POST /api/v1/screener → rows
 *
 * Fields loaded from /screener/fields (categorical catalog).
 * Operators derived from value_type; screen runs server-side.
 * No scores, no rankings — evidence-backed filtering only.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Link } from "react-router-dom"
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  ArrowUpDown,
  Filter,
  Plus,
  X,
} from "lucide-react"
import { fetchScreenerFields, runScreen } from "../api/client"
import type {
  ScreenerFieldSpec,
  ScreenExecutionOutput,
  ScreenFilter,
} from "../api/types"
import { formatLabel } from "../lib/format"
import { FilterChip } from "../components/ResearchPrimitives"

/* ── Operator config ─────────────────────────────────────────────── */

const OPERATORS_BY_TYPE: Record<string, string[]> = {
  number: ["eq", "ne", "gt", "gte", "lt", "lte", "between", "has", "missing"],
  integer: ["eq", "ne", "gt", "gte", "lt", "lte", "between", "has", "missing"],
  boolean: ["is_true", "is_false"],
  string: ["eq", "ne", "contains", "has", "missing"],
}

const OPERATOR_LABELS: Record<string, string> = {
  eq: "=",
  ne: "\u2260",
  gt: ">",
  gte: "\u2265",
  lt: "<",
  lte: "\u2264",
  between: "between",
  has: "has",
  missing: "missing",
  is_true: "yes",
  is_false: "no",
  contains: "contains",
  in: "in",
}

const NUMBER_OPERATORS = new Set(["eq", "ne", "gt", "gte", "lt", "lte"])
const SECOND_VALUE_OPERATORS = new Set(["between"])

type BuilderFilter = {
  field: string
  operator: string
  value: string
  secondValue: string
}

/* ── Component ───────────────────────────────────────────────────── */

export default function ScreenerPage() {
  const [fields, setFields] = useState<ScreenerFieldSpec[]>([])
  const [fieldsLoading, setFieldsLoading] = useState(true)
  const [fieldsError, setFieldsError] = useState<string | null>(null)

  const [activeFilters, setActiveFilters] = useState<BuilderFilter[]>([])
  const [builder, setBuilder] = useState<BuilderFilter>({
    field: "",
    operator: "eq",
    value: "",
    secondValue: "",
  })

  const [output, setOutput] = useState<ScreenExecutionOutput | null>(null)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)
  const [sortKey, setSortKey] = useState<string>("symbol")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")

  const abortRef = useRef(0)

  /* ── Load field catalog ──────────────────────────────────────── */

  useEffect(() => {
    let cancelled = false
    fetchScreenerFields()
      .then((res) => {
        if (!cancelled) {
          setFields(res.fields.filter((f) => f.available))
          setFieldsLoading(false)
          if (res.fields.length === 0) {
            setFieldsError("No screener fields available.")
          }
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setFieldsError(err instanceof Error ? err.message : "Screener fields unavailable")
          setFieldsLoading(false)
        }
      })
    return () => { cancelled = true }
  }, [])

  /* ── Grouped fields for the select ───────────────────────────── */

  const groupedFields = useMemo(() => {
    const map = new Map<string, ScreenerFieldSpec[]>()
    for (const f of fields) {
      const arr = map.get(f.category) ?? []
      arr.push(f)
      map.set(f.category, arr)
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [fields])

  /* ── Run screen ──────────────────────────────────────────────── */

  const execute = useCallback(async (filters: BuilderFilter[]) => {
    const generation = ++abortRef.current
    setRunning(true)
    setRunError(null)

    try {
      const filtersPayload: ScreenFilter[] = filters.map((f) => {
        const value: unknown =
          NUMBER_OPERATORS.has(f.operator) || f.operator === "between"
            ? (f.value === "" ? null : Number(f.value))
            : f.operator === "is_true"
              ? true
              : f.operator === "is_false"
                ? false
                : f.value === ""
                  ? null
                  : f.value
        const secondValue: unknown =
          f.operator === "between" && f.secondValue !== ""
            ? Number(f.secondValue)
            : undefined
        return { field: f.field, operator: f.operator, value, second_value: secondValue }
      })

      const result = await runScreen(
        {
          name: "Frontend screen",
          description: "Composed in the research screener",
          combine: "AND",
          groups: [{ logic: "AND", filters: filtersPayload }],
        },
        undefined,
      )

      if (generation === abortRef.current) {
        setOutput(result)
      }
    } catch (err: unknown) {
      if (generation === abortRef.current) {
        setRunError(err instanceof Error ? err.message : "Screen run failed")
      }
    } finally {
      if (generation === abortRef.current) {
        setRunning(false)
      }
    }
  }, [])

  /* Auto-run when filters change (skip initial empty state). */
  const ranOnceRef = useRef(false)
  useEffect(() => {
    if (!fieldsLoading && activeFilters.length === 0 && ranOnceRef.current) {
      void execute([])
      return
    }
    if (fieldsLoading) return
    ranOnceRef.current = true
    void execute(activeFilters)
  }, [activeFilters, fieldsLoading, execute])

  /* ── Builder helpers ─────────────────────────────────────────── */

  const selectedFieldSpec = useMemo(
    () => fields.find((f) => f.name === builder.field) ?? null,
    [fields, builder.field],
  )

  const availableOperators = useMemo(
    () => (selectedFieldSpec ? OPERATORS_BY_TYPE[selectedFieldSpec.value_type] ?? [] : []),
    [selectedFieldSpec],
  )

  const fieldDefaults = useMemo(
    () =>
      Object.fromEntries(
        fields.map((f) => {
          const ops = OPERATORS_BY_TYPE[f.value_type] ?? []
          return [f.name, ops[0] ?? "eq"]
        }),
      ),
    [fields],
  )

  function setBuilderField(fieldName: string) {
    setBuilder({
      field: fieldName,
      operator: fieldDefaults[fieldName] ?? "eq",
      value: "",
      secondValue: "",
    })
  }

  function addFilter() {
    if (!builder.field) return
    const isPresence = builder.operator === "has" || builder.operator === "missing"
    const isBooleanOp = builder.operator === "is_true" || builder.operator === "is_false"
    if (!isPresence && !isBooleanOp && builder.value.trim() === "") return

    setActiveFilters((prev) => [
      ...prev,
      {
        field: builder.field,
        operator: builder.operator,
        value: isBooleanOp ? builder.operator : builder.value.trim(),
        secondValue: builder.secondValue.trim(),
      },
    ])
    setBuilder((prev) => ({
      ...prev,
      value: "",
      secondValue: "",
    }))
  }

  function removeFilterAt(index: number) {
    setActiveFilters((prev) => prev.filter((_, i) => i !== index))
  }

  function clearAllFilters() {
    setActiveFilters([])
  }

  /* ── Sorted rows ─────────────────────────────────────────────── */

  const sortedRows = useMemo(() => {
    if (!output) return []
    const rows = [...output.rows]
    rows.sort((a, b) => {
      let cmp = 0
      if (sortKey === "symbol") cmp = a.symbol.localeCompare(b.symbol)
      else if (sortKey === "company_name") cmp = (a.company_name ?? "").localeCompare(b.company_name ?? "")
      else if (sortKey === "sector") cmp = (a.sector ?? "").localeCompare(b.sector ?? "")
      else {
        const colA = a.columns.find((c) => c.field === sortKey)
        const colB = b.columns.find((c) => c.field === sortKey)
        const va = colA?.value ?? ""
        const vb = colB?.value ?? ""
        cmp = va.localeCompare(vb, undefined, { numeric: true })
      }
      return sortDir === "asc" ? cmp : -cmp
    })
    return rows
  }, [output, sortKey, sortDir])

  /* ── Visible columns ────────────────────────────────────────────
     Prefer columns with populated values across the result set so
     cards show the most meaningful fields.                         */

  const visibleColumns = useMemo(() => {
    if (!output || output.selected_columns.length === 0) return []
    const ranking = output.selected_columns.map((field) => {
      let present = 0
      for (const row of output.rows) {
        const cell = row.columns.find((c) => c.field === field)
        if (cell?.available && cell.value != null) present++
      }
      return { field, present }
    })
    ranking.sort(
      (a, b) => b.present - a.present ||
        output.selected_columns.indexOf(a.field) - output.selected_columns.indexOf(b.field),
    )
    return ranking.slice(0, 8).map((r) => r.field)
  }, [output])

  /* ── Render ──────────────────────────────────────────────────── */

  return (
    <div className="page-screener">
      <section className="page-hero">
        <p className="page-kicker">Screen</p>
        <h1>Research Screener</h1>
        <p className="page-subtitle">
          Compose evidence-backed filters against the recorded data universe.
          Every result carries its column context. No scores, no rankings.
        </p>
      </section>

      {fieldsLoading && (
        <div className="loading-state" role="status">
          <Activity className="spin" size={26} />
          <strong>Loading field catalog</strong>
        </div>
      )}

      {fieldsError && (
        <div className="empty-state error" role="alert">
          <AlertTriangle size={28} />
          <strong>Screener unavailable</strong>
          <p>{fieldsError}</p>
        </div>
      )}

      {runError && !fieldsLoading && (
        <div className="empty-state error" role="alert" style={{ marginTop: "var(--space-4)" }}>
          <AlertTriangle size={20} />
          <p>{runError}</p>
        </div>
      )}

      {!fieldsLoading && !fieldsError && (
        <>
          {/* ── Context bar ─────────────────────────────────────── */}
          <div className="scr-context scr-section mt-5">
            <span className="scr-context-item">
              <strong>{output?.universe_size ?? "—"}</strong> universe companies
            </span>
            <span className="scr-context-sep" />
            <span className="scr-context-item">
              <strong>{activeFilters.length}</strong> filter{activeFilters.length === 1 ? "" : "s"}
            </span>
            <span className="scr-context-sep" />
            <span className="scr-context-item">
              <strong>{output?.matched_count ?? "—"}</strong> matched
            </span>
            {running && (
              <>
                <span className="scr-context-sep" />
                <span className="scr-context-item" style={{ color: "var(--color-text-muted)" }}>running…</span>
              </>
            )}
          </div>

          {/* ── Filter builder ──────────────────────────────────── */}
          <section className="scr-builder scr-section" aria-label="Filter builder">
            <div className="scr-builder-head">
              <strong className="scr-builder-title">Filters</strong>
              <span className={`scr-filter-count${activeFilters.length === 0 ? " zero" : ""}`}>
                {activeFilters.length}
              </span>
            </div>

            <div className="scr-builder-grid">
              <div>
                <label className="scr-field-label" htmlFor="scr-field">
                  Field
                </label>
                <select
                  id="scr-field"
                  className="scr-select"
                  value={builder.field}
                  onChange={(e) => setBuilderField(e.target.value)}
                >
                  <option value="">Select field…</option>
                  {groupedFields.map(([cat, catFields]) => (
                    <optgroup key={cat} label={formatLabel(cat)}>
                      {catFields.map((f) => (
                        <option key={f.name} value={f.name}>
                          {f.label}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </div>

              <div>
                <label className="scr-field-label" htmlFor="scr-operator">
                  Operator
                </label>
                <select
                  id="scr-operator"
                  className="scr-select"
                  value={builder.operator}
                  onChange={(e) =>
                    setBuilder((prev) => ({ ...prev, operator: e.target.value, secondValue: "" }))
                  }
                  disabled={!builder.field}
                >
                  {availableOperators.map((op) => (
                    <option key={op} value={op}>
                      {OPERATOR_LABELS[op] ?? op}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="scr-field-label" htmlFor="scr-value">
                  {selectedFieldSpec?.value_type === "boolean" ? "Value" : "Value"}
                </label>
                {selectedFieldSpec?.value_type === "boolean" || builder.operator === "is_true" || builder.operator === "is_false" || builder.operator === "has" || builder.operator === "missing" ? (
                  <span className="scr-select" style={{ display: "flex", alignItems: "center", height: 38, color: "var(--color-text-muted)" }}>
                    {builder.operator === "has" || builder.operator === "missing"
                      ? "presence check"
                      : builder.operator === "is_true"
                        ? "matches true"
                        : builder.operator === "is_false"
                          ? "matches false"
                          : ""}
                  </span>
                ) : selectedFieldSpec?.value_type === "string" ? (
                  <input
                    id="scr-value"
                    className="scr-select"
                    type="text"
                    value={builder.value}
                    onChange={(e) => setBuilder((prev) => ({ ...prev, value: e.target.value }))}
                    placeholder="Text value…"
                  />
                ) : (
                  <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}>
                    <input
                      id="scr-value"
                      className="scr-select"
                      type="number"
                      value={builder.value}
                      onChange={(e) => setBuilder((prev) => ({ ...prev, value: e.target.value }))}
                      placeholder="Number…"
                      style={{ flex: 1, minWidth: 0 }}
                    />
                    {SECOND_VALUE_OPERATORS.has(builder.operator) && (
                      <input
                        className="scr-select"
                        type="number"
                        value={builder.secondValue}
                        onChange={(e) => setBuilder((prev) => ({ ...prev, secondValue: e.target.value }))}
                        placeholder="Second…"
                        style={{ flex: 1, minWidth: 0 }}
                      />
                    )}
                  </div>
                )}
              </div>

              <button
                className="scr-add-btn"
                onClick={addFilter}
                disabled={
                  !builder.field ||
                  (builder.operator !== "has" &&
                    builder.operator !== "missing" &&
                    builder.operator !== "is_true" &&
                    builder.operator !== "is_false" &&
                    builder.value.trim() === "")
                }
              >
                <Plus size={14} />
                Add filter
              </button>
            </div>

            {/* Active filter chips */}
            {activeFilters.length > 0 && (
              <div className="scr-chips" role="list" aria-label="Active filters">
                {activeFilters.map((f, i) => {
                  const spec = fields.find((field) => field.name === f.field)
                  return (
                    <FilterChip
                      key={`${f.field}-${f.operator}-${f.value}-${i}`}
                      label={spec?.label ?? f.field}
                      value={
                        f.operator === "has" || f.operator === "missing"
                          ? OPERATOR_LABELS[f.operator]
                          : f.operator === "is_true" || f.operator === "is_false"
                            ? OPERATOR_LABELS[f.operator]
                            : f.operator === "between"
                              ? `${f.value}..${f.secondValue}`
                              : `${OPERATOR_LABELS[f.operator] ?? f.operator} ${f.value}`
                      }
                      onRemove={() => removeFilterAt(i)}
                    />
                  )
                })}
              </div>
            )}

            {activeFilters.length > 0 && (
              <div className="scr-more">
                <button className="scr-more-toggle" onClick={clearAllFilters}>
                  <X size={13} />
                  Clear all
                </button>
              </div>
            )}
          </section>

          {/* ── Results ─────────────────────────────────────────── */}
          <section className="scr-section" aria-label="Screener results">
            <div className="scr-results-head">
              <span className="scr-results-label">Matching companies</span>
              <span className="scr-results-count">
                {sortedRows.length} <small>of {output?.universe_size ?? "—"}</small>
              </span>
              <div className="scr-results-tools">
                <ArrowUpDown size={13} className="icon-muted" />
                <select
                  className="scr-sort"
                  value={sortKey}
                  onChange={(e) => {
                    const val = e.target.value
                    setSortKey(val)
                    if (val !== sortKey) setSortDir("asc")
                  }}
                  aria-label="Sort results by"
                >
                  <option value="symbol">Sort: Symbol</option>
                  <option value="company_name">Sort: Company</option>
                  <option value="sector">Sort: Sector</option>
                  {visibleColumns.map((field) => {
                    const spec = fields.find((f) => f.name === field)
                    return (
                      <option key={field} value={field}>
                        Sort: {spec?.label ?? field}
                      </option>
                    )
                  })}
                </select>
                <button
                  className="scr-sort"
                  onClick={() => setSortDir((d) => (d === "asc" ? "desc" : "asc"))}
                  aria-label={`Sort direction ${sortDir === "asc" ? "ascending" : "descending"}`}
                >
                  {sortDir === "asc" ? "↑ Asc" : "↓ Desc"}
                </button>
              </div>
            </div>

            {output && output.notes.length > 0 && (
              <p className="scr-more-note" style={{ marginBottom: "var(--space-3)" }}>
                {output.notes[0]}
              </p>
            )}

            {sortedRows.length === 0 ? (
              <div className="empty-state">
                <Filter size={24} />
                <strong>No matching companies</strong>
                <p>
                  {activeFilters.length > 0
                    ? "Loosen or clear the current filters to widen the match."
                    : "The tracked universe is empty right now."}
                </p>
                {activeFilters.length > 0 && (
                  <button className="refresh-button retry-button" onClick={clearAllFilters}>
                    Clear all filters
                  </button>
                )}
              </div>
            ) : (
              <div className="scr-results-list">
                {sortedRows.map((row) => (
                  <article key={row.symbol} className="result-card">
                    <div className="result-card-id">
                      <Link
                        to={`/companies/${encodeURIComponent(row.symbol)}`}
                        className="result-symbol"
                      >
                        {row.symbol}
                      </Link>
                      <span className="result-company">{row.company_name ?? "\u2014"}</span>
                      <span className="result-sector">{formatLabel(row.sector ?? "")}</span>
                    </div>

                    <div className="result-card-main">
                      <div className="scr-result-columns">
                        {row.columns
                          .filter((col) => visibleColumns.includes(col.field))
                          .map((col) => (
                            <span
                              key={col.field}
                              className={`scr-col-chip${col.available ? "" : " unavailable"}`}
                              title={`${col.label}${col.unit ? ` (${col.unit})` : ""}`}
                            >
                              <span className="scr-col-label">{col.label}</span>
                              <span className="scr-col-value">
                                {col.available && col.value != null ? col.value : "\u2014"}
                              </span>
                              {col.unit && col.available && col.value != null && (
                                <span className="scr-col-unit">{col.unit}</span>
                              )}
                            </span>
                          ))}
                        {row.columns.filter((col) => visibleColumns.includes(col.field)).length === 0 && (
                          <span className="scr-context-item" style={{ color: "var(--color-text-muted)" }}>
                            No columns selected
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="result-actions">
                      <Link
                        to={`/companies/${encodeURIComponent(row.symbol)}`}
                        className="result-open"
                      >
                        Open Research
                        <ArrowRight size={14} />
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
