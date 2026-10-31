import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import CompanyEventsPanel from "./CompanyEventsPanel"
import { fetchCompanyNews, fetchCorporateActions } from "../api/client"

vi.mock("../api/client", () => ({
  fetchCompanyNews: vi.fn(),
  fetchCorporateActions: vi.fn(),
}))

const mockedNews = vi.mocked(fetchCompanyNews)
const mockedActions = vi.mocked(fetchCorporateActions)

const company = {
  symbol: "TCS",
  company_name: "Tata Consultancy Services",
  sector: "IT",
  as_of: "2026-10-31T00:00:00Z",
}

describe("CompanyEventsPanel source status", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("shows a failed source even when the other source succeeds", async () => {
    mockedNews.mockRejectedValue(new Error("news endpoint unavailable"))
    mockedActions.mockResolvedValue({
      company,
      corporate_actions: {
        symbol: "TCS",
        as_of: company.as_of,
        items: [],
        item_count: 0,
        type_counts: {},
        source_count: 0,
        notes: [],
      },
    })

    render(<CompanyEventsPanel symbol="TCS" timelineEntries={[]} />)

    await waitFor(() => {
      expect(screen.getByText(/News feed: Unavailable/)).toBeInTheDocument()
      expect(screen.getByText(/Corporate actions: No records returned/)).toBeInTheDocument()
    })
  })

  it("labels successful empty responses as no records returned", async () => {
    mockedNews.mockResolvedValue({
      company,
      news: {
        symbol: "TCS",
        as_of: company.as_of,
        items: [],
        item_count: 0,
        category_counts: {},
        source_count: 0,
        source_names: [],
        notes: [],
      },
    })
    mockedActions.mockResolvedValue({
      company,
      corporate_actions: {
        symbol: "TCS",
        as_of: company.as_of,
        items: [],
        item_count: 0,
        type_counts: {},
        source_count: 0,
        notes: [],
      },
    })

    render(<CompanyEventsPanel symbol="TCS" timelineEntries={[]} />)

    await waitFor(() => {
      expect(screen.getByText(/News feed: No records returned/)).toBeInTheDocument()
      expect(screen.getByText(/Corporate actions: No records returned/)).toBeInTheDocument()
    })
  })
})
