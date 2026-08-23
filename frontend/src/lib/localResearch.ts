/**
 * Client-side research context — watchlist and recently-viewed companies.
 *
 * These capabilities run entirely on this device (localStorage); no backend
 * API exists for them yet, so nothing here pretends to be server-synced.
 * Surfaces that DO need a backend (saved screens, alerts, notification
 * preferences) are intentionally absent from this module.
 */

import type { DiscoveryItem } from "../api/types"

const WATCHLIST_KEY = "qrt.watchlist.v1"
const RECENTS_KEY = "qrt.recents.v1"
const MAX_RECENTS = 12

function readNames(key: string): string[] {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((entry): entry is string => typeof entry === "string")
  } catch {
    return []
  }
}

function writeNames(key: string, symbols: string[]): void {
  try {
    localStorage.setItem(key, JSON.stringify(symbols))
  } catch {
    // Storage unavailable (private mode / quota): degrade to in-session only.
  }
}

export function getWatchlist(): string[] {
  return readNames(WATCHLIST_KEY)
}

export function isWatched(symbol: string): boolean {
  return getWatchlist().includes(symbol)
}

/** Returns the list after toggling `symbol`. */
export function toggleWatch(symbol: string): string[] {
  const current = getWatchlist()
  const next = current.includes(symbol)
    ? current.filter((entry) => entry !== symbol)
    : [...current, symbol]
  writeNames(WATCHLIST_KEY, next)
  return next
}

export function removeFromWatchlist(symbol: string): string[] {
  const next = getWatchlist().filter((entry) => entry !== symbol)
  writeNames(WATCHLIST_KEY, next)
  return next
}

export function getRecentSymbols(): string[] {
  return readNames(RECENTS_KEY)
}

/** Records a company visit, newest first, capped at MAX_RECENTS. */
export function trackRecentVisit(symbol: string): void {
  const next = [symbol, ...getRecentSymbols().filter((s) => s !== symbol)].slice(
    0,
    MAX_RECENTS,
  )
  writeNames(RECENTS_KEY, next)
}

/** Hydrate stored symbols into display items; drops unknown symbols. */
export function hydrateItems(
  symbols: string[],
  universe: DiscoveryItem[],
): Array<{ symbol: string; name: string; sector: string }> {
  const bySymbol = new Map(universe.map((item) => [item.symbol, item]))
  const out: Array<{ symbol: string; name: string; sector: string }> = []
  for (const symbol of symbols) {
    const item = bySymbol.get(symbol)
    if (!item) continue
    out.push({
      symbol: item.symbol,
      name: item.company_name ?? item.symbol,
      sector: item.sector,
    })
  }
  return out
}
