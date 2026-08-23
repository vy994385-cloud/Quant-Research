/**
 * Shared discovery state contract + hook.
 * Kept separate from DiscoveryProvider so the provider file exports
 * only components (react-refresh / fast-refresh requirement).
 */

import { createContext, useContext } from "react"
import type { DiscoveryItem } from "./api/types"

export interface DiscoveryState {
  items: DiscoveryItem[]
  loading: boolean
  error: string | null
}

export const DiscoveryContext = createContext<DiscoveryState>({
  items: [],
  loading: true,
  error: null,
})

export function useDiscovery(): DiscoveryState {
  return useContext(DiscoveryContext)
}
