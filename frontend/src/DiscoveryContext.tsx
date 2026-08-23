/**
 * DiscoveryProvider: shared discovery data cache.
 * Avoids redundant fetchDiscovery calls across 15+ pages.
 * Fetches once on mount; provides items + loading/error to consumers
 * via useDiscovery() (see ./useDiscovery.ts).
 */

import { useEffect, useState } from "react"
import { fetchDiscovery } from "./api/client"
import { DiscoveryContext } from "./useDiscovery"
import type { DiscoveryItem } from "./api/types"

export function DiscoveryProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchDiscovery()
      .then((res) => {
        if (!cancelled) { setItems(res.results); setLoading(false) }
      })
      .catch((err: unknown) => {
        if (!cancelled) { setError(err instanceof Error ? err.message : "Discovery unavailable"); setLoading(false) }
      })
    return () => { cancelled = true }
  }, [])

  return (
    <DiscoveryContext.Provider value={{ items, loading, error }}>
      {children}
    </DiscoveryContext.Provider>
  )
}
