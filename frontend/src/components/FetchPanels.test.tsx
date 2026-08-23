/**
 * Tests for the F6 panels that own their own fetch lifecycle.
 *
 * Focus: state transitions are driven by props changes without
 * synchronous setState inside effects — when the symbol changes,
 * the panel returns to its loading state and refetches.
 */

import { beforeEach, describe, expect, it, vi } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import NewsPanel from "./NewsPanel"
import CorporateActionsPanel from "./CorporateActionsPanel"
import { ApiError, fetchCompanyNews, fetchCorporateActions } from "../api/client"
import type {
  CompanyCorporateActionsResponse,
  CompanyNewsResponse,
} from "../api/types"

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>(
    "../api/client",
  )
  return {
    ...actual,
    fetchCompanyNews: vi.fn(),
    fetchCorporateActions: vi.fn(),
  }
})

const mockedFetchNews = vi.mocked(fetchCompanyNews)
const mockedFetchActions = vi.mocked(fetchCorporateActions)

function newsResponse(symbol: string, headline: string): CompanyNewsResponse {
  return {
    company: {
      symbol,
      company_name: `${symbol} Ltd`,
      sector: "information technology",
      as_of: "2026-08-10T12:00:00Z",
    },
    news: {
      symbol,
      as_of: "2026-08-10T12:00:00Z",
      items: [
        {
          news_id: `${symbol}-news-1`,
          symbol,
          headline,
          summary: "Summary text",
          category: "EARNINGS_RESULTS",
          direction: "POSITIVE",
          source_name: "Exchange Filing",
          source_url: "",
          source_type: "filing",
          published_at: "2026-08-01T10:00:00Z",
          available_at: "2026-08-01T10:05:00Z",
          event_date: null,
          related_metrics: [],
          evidence_refs: ["ev-1"],
          as_of: null,
          provenance_id: "prov-news-1",
        },
      ],
      item_count: 1,
      category_counts: { EARNINGS_RESULTS: 1 },
      source_count: 1,
      source_names: ["Exchange Filing"],
      notes: [],
    },
  }
}

function actionsResponse(
  symbol: string,
  title: string,
): CompanyCorporateActionsResponse {
  return {
    company: {
      symbol,
      company_name: `${symbol} Ltd`,
      sector: "information technology",
      as_of: "2026-08-10T12:00:00Z",
    },
    corporate_actions: {
      symbol,
      as_of: "2026-08-10T12:00:00Z",
      items: [
        {
          action_id: `${symbol}-action-1`,
          symbol,
          action_type: "DIVIDEND",
          title,
          description: "",
          announcement_date: "2026-07-15",
          effective_date: null,
          record_date: null,
          value: null,
          ratio: null,
          source_name: "Board Announcement",
          source_url: "",
          provenance_id: "prov-action-1",
          published_at: null,
          available_at: null,
          as_of: null,
        },
      ],
      item_count: 1,
      type_counts: { DIVIDEND: 1 },
      source_count: 1,
      notes: [],
    },
  }
}

beforeEach(() => {
  mockedFetchNews.mockReset()
  mockedFetchActions.mockReset()
})

describe("NewsPanel fetch lifecycle", () => {
  it("renders items after the fetch resolves", async () => {
    mockedFetchNews.mockResolvedValue(newsResponse("TCS", "TCS beats estimates"))
    render(<NewsPanel symbol="TCS" />)

    expect(screen.getByText(/loading news/i)).toBeInTheDocument()
    await waitFor(() =>
      expect(screen.getByText("TCS beats estimates")).toBeInTheDocument(),
    )
    expect(mockedFetchNews).toHaveBeenCalledWith("TCS", undefined)
    expect(screen.getByText("1 items")).toBeInTheDocument()
  })

  it("returns to the loading state and refetches when the symbol changes", async () => {
    mockedFetchNews.mockResolvedValueOnce(newsResponse("TCS", "TCS beats estimates"))
    let resolveInfy!: (v: CompanyNewsResponse) => void
    mockedFetchNews.mockImplementationOnce(
      () =>
        new Promise<CompanyNewsResponse>((resolve) => {
          resolveInfy = resolve
        }),
    )

    const { rerender } = render(<NewsPanel symbol="TCS" />)
    await waitFor(() =>
      expect(screen.getByText("TCS beats estimates")).toBeInTheDocument(),
    )

    rerender(<NewsPanel symbol="INFY" />)

    expect(screen.getByText(/loading news/i)).toBeInTheDocument()
    expect(screen.queryByText("TCS beats estimates")).not.toBeInTheDocument()

    resolveInfy(newsResponse("INFY", "Infosys wins large deal"))
    await waitFor(() =>
      expect(screen.getByText("Infosys wins large deal")).toBeInTheDocument(),
    )
    expect(mockedFetchNews).toHaveBeenLastCalledWith("INFY", undefined)
  })

  it("surfaces structured API errors verbatim", async () => {
    mockedFetchNews.mockRejectedValue(
      new ApiError("Request failed with status 503.", "request_failed", 503),
    )
    render(<NewsPanel symbol="TCS" />)

    await waitFor(() =>
      expect(
        screen.getByText("Request failed with status 503."),
      ).toBeInTheDocument(),
    )
  })
})

describe("CorporateActionsPanel fetch lifecycle", () => {
  it("renders actions after the fetch resolves", async () => {
    mockedFetchActions.mockResolvedValue(
      actionsResponse("TCS", "Interim dividend declared"),
    )
    render(<CorporateActionsPanel symbol="TCS" />)

    await waitFor(() =>
      expect(screen.getByText("Interim dividend declared")).toBeInTheDocument(),
    )
    expect(mockedFetchActions).toHaveBeenCalledWith("TCS", undefined)
    expect(screen.getByText("1 actions")).toBeInTheDocument()
  })

  it("returns to the loading state and refetches when the symbol changes", async () => {
    mockedFetchActions.mockResolvedValueOnce(
      actionsResponse("TCS", "Interim dividend declared"),
    )
    let resolveReliance!: (v: CompanyCorporateActionsResponse) => void
    mockedFetchActions.mockImplementationOnce(
      () =>
        new Promise<CompanyCorporateActionsResponse>((resolve) => {
          resolveReliance = resolve
        }),
    )

    const { rerender } = render(<CorporateActionsPanel symbol="TCS" />)
    await waitFor(() =>
      expect(screen.getByText("Interim dividend declared")).toBeInTheDocument(),
    )

    rerender(<CorporateActionsPanel symbol="RELIANCE" />)

    expect(screen.getByText(/loading corporate actions/i)).toBeInTheDocument()
    expect(
      screen.queryByText("Interim dividend declared"),
    ).not.toBeInTheDocument()

    resolveReliance(
      actionsResponse("RELIANCE", "Buyback approved"),
    )
    await waitFor(() =>
      expect(screen.getByText("Buyback approved")).toBeInTheDocument(),
    )
    expect(mockedFetchActions).toHaveBeenLastCalledWith("RELIANCE", undefined)
  })

  it("shows the explicit empty state when no actions exist", async () => {
    mockedFetchActions.mockResolvedValue({
      company: {
        symbol: "TCS",
        company_name: null,
        sector: null,
        as_of: "2026-08-10T12:00:00Z",
      },
      corporate_actions: null,
    })
    render(<CorporateActionsPanel symbol="TCS" />)

    await waitFor(() =>
      expect(
        screen.getByText("No corporate actions available for this company."),
      ).toBeInTheDocument(),
    )
  })
})
