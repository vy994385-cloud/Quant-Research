/**
 * Command-bar company search backed by the /api/v1 discovery contract.
 *
 * Provides free-text search across symbol, company name, and sector with a
 * keyboard-navigable dropdown. Selecting a company triggers research.
 */

import { useEffect, useMemo, useRef, useState } from "react"
import type { FormEvent, KeyboardEvent } from "react"
import { Activity, Building2, Search } from "lucide-react"
import { fetchDiscovery } from "../api/client"
import type { DiscoveryItem } from "../api/types"
import { filterDiscovery, normalizeSymbol } from "../lib/discovery"

interface CompanySearchProps {
  onSelect: (symbol: string) => void
  disabled?: boolean
}

export default function CompanySearch({
  onSelect,
  disabled,
}: CompanySearchProps) {
  const [query, setQuery] = useState("")
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const listboxRef = useRef<HTMLUListElement | null>(null)

  useEffect(() => {
    let cancelled = false

    fetchDiscovery()
      .then((response) => {
        if (cancelled) return
        setItems(response.results)
        setLoading(false)
      })
      .catch((requestError: unknown) => {
        if (cancelled) return
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Company discovery is unavailable.",
        )
        setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const matches = useMemo(
    () => filterDiscovery(items, query),
    [items, query],
  )

  function choose(symbol: string) {
    setQuery("")
    setOpen(false)
    setActiveIndex(0)
    onSelect(symbol)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (matches.length > 0) {
      choose(matches[Math.min(activeIndex, matches.length - 1)].symbol)
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!open) return

    if (event.key === "ArrowDown") {
      event.preventDefault()
      setActiveIndex((index) =>
        Math.min(index + 1, matches.length - 1),
      )
    } else if (event.key === "ArrowUp") {
      event.preventDefault()
      setActiveIndex((index) => Math.max(index - 1, 0))
    } else if (event.key === "Escape") {
      setOpen(false)
    }
  }

  function focusActive(index: number) {
    listboxRef.current
      ?.querySelectorAll<HTMLLIElement>("[data-index]")
      .forEach((node) => {
        const nodeIndex = Number(node.dataset.index)

        if (nodeIndex === index) {
          node.scrollIntoView({ block: "nearest" })
        }
      })
  }

  useEffect(() => {
    focusActive(activeIndex)
  }, [activeIndex])

  return (
    <form onSubmit={handleSubmit} className="command-search">
      <Search size={17} />
      <input
        value={query}
        onChange={(event) => {
          setQuery(event.target.value)
          setActiveIndex(0)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={handleKeyDown}
        placeholder="Search company — TCS, INFY, HDFCBANK, M&M"
        aria-label="Company search"
        aria-expanded={open}
        autoComplete="off"
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || loading}>
        {loading ? (
          <Activity className="spin" size={16} />
        ) : (
          "Research"
        )}
      </button>

      {open && !disabled ? (
        <div className="discovery-dropdown">
          {loading ? (
            <div className="discovery-empty">
              <Activity className="spin" size={15} />
              Loading supported companies…
            </div>
          ) : error ? (
            <div className="discovery-empty discovery-error">{error}</div>
          ) : matches.length > 0 ? (
            <ul ref={listboxRef} role="listbox">
              {matches.map((item, index) => (
                <li
                  key={item.symbol}
                  data-index={index}
                  role="option"
                  aria-selected={index === activeIndex}
                  className={index === activeIndex ? "discovery-active" : ""}
                  onMouseDown={(event) => {
                    event.preventDefault()
                    choose(item.symbol)
                  }}
                  onMouseEnter={() => setActiveIndex(index)}
                >
                  <Building2 size={14} />
                  <span>
                    <b>{item.symbol}</b>
                    <small>
                      {item.company_name ?? item.symbol} · {item.sector}
                    </small>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="discovery-empty">
              No supported company matches “{normalizeSymbol(query)}”.
            </div>
          )}
        </div>
      ) : null}
    </form>
  )
}
