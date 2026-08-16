/**
 * Company discovery search helpers used by the command-bar search.
 */

import type { DiscoveryItem } from "../api/types"

export function normalizeSymbol(value: string): string {
  return value.trim().toUpperCase()
}

export function matchesQuery(item: DiscoveryItem, query: string): boolean {
  const lower = query.trim().toLowerCase()

  if (!lower) return true

  return (
    item.symbol.toLowerCase().includes(lower) ||
    (item.company_name ?? "").toLowerCase().includes(lower) ||
    item.sector.toLowerCase().includes(lower)
  )
}

export function filterDiscovery(
  items: DiscoveryItem[],
  query: string,
): DiscoveryItem[] {
  const researchable = items.filter((item) => item.research_available)
  const matches = researchable.filter((item) => matchesQuery(item, query))

  return matches.sort((a, b) => a.symbol.localeCompare(b.symbol))
}
