import { describe, expect, it, vi, beforeEach } from "vitest"
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { RESEARCH_GAPS } from "../test/fixtures"
import type { CompanyResearchGapsResponse } from "../api/types"

vi.mock("../api/client", () => ({
  fetchDiscovery: vi.fn(),
  fetchResearchGaps: vi.fn(),
}))

import { fetchDiscovery, fetchResearchGaps } from "../api/client"
import ResearchGapsPage from "./ResearchGapsPage"

const mockFetchDiscovery = vi.mocked(fetchDiscovery)
const mockFetchResearchGaps = vi.mocked(fetchResearchGaps)

function renderPage(data: CompanyResearchGapsResponse = RESEARCH_GAPS) {
  mockFetchDiscovery.mockResolvedValue({
    count: 1,
    results: [
      {
        symbol: "TCS",
        company_name: "Tata Consultancy Services",
        sector: "information technology",
        research_available: true,
      },
    ],
  })
  mockFetchResearchGaps.mockResolvedValue(data)
  render(
    <MemoryRouter initialEntries={["/research-gaps"]}>
      <ResearchGapsPage />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe("ResearchGapsPage", () => {
  it("renders the page header", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Research Coverage")).toBeInTheDocument()
    })
  })

  it("shows loading state initially", () => {
    renderPage()
    expect(screen.getByText("Loading coverage data")).toBeInTheDocument()
  })

  it("loads company picker after discovery and auto-selects the first company", async () => {
    renderPage()
    await waitFor(() => {
      expect(mockFetchResearchGaps).toHaveBeenCalledWith("TCS")
    })
    expect(screen.getByText("TCS")).toBeInTheDocument()
  })

  it("shows the coverage status strip with counts", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Missing")).toBeInTheDocument()
    })
    expect(screen.getAllByText("Stale").length).toBeGreaterThan(0)
    expect(screen.getByText("Available")).toBeInTheDocument()
  })

  it("groups gaps into a status stream", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Forward guidance from management not available for latest period.")).toBeInTheDocument()
    })
    // Distinct gap rows render once even with one company selected.
    expect(mockFetchResearchGaps).toHaveBeenCalledTimes(1)
  })

  it("expands a gap row to reveal reason and resolution", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/Forward guidance from management/i)).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole("button", { name: /forward guidance from management not available/i }))
    await waitFor(() => {
      expect(screen.getByText("Why this gap exists")).toBeInTheDocument()
    })
    expect(screen.getByText(/No earnings call transcript or investor presentation found/i)).toBeInTheDocument()
  })

  it("displays empty state when no companies are researchable", async () => {
    mockFetchDiscovery.mockResolvedValue({ count: 0, results: [] })
    render(
      <MemoryRouter initialEntries={["/research-gaps"]}>
        <ResearchGapsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText("Select companies to view coverage")).toBeInTheDocument()
    })
  })

  it("shows no-data message when research_gaps is null", async () => {
    const noGapsData: CompanyResearchGapsResponse = {
      company: {
        symbol: "TCS",
        company_name: "Tata Consultancy Services",
        sector: "information technology",
        as_of: "2026-08-10T12:00:00+00:00",
      },
      research_gaps: null,
    }
    mockFetchDiscovery.mockResolvedValue({
      count: 1,
      results: [
        {
          symbol: "TCS",
          company_name: "Tata Consultancy Services",
          sector: "information technology",
          research_available: true,
        },
      ],
    })
    mockFetchResearchGaps.mockResolvedValue(noGapsData)
    render(
      <MemoryRouter initialEntries={["/research-gaps"]}>
        <ResearchGapsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(mockFetchResearchGaps).toHaveBeenCalledWith("TCS")
    })
    await waitFor(() => {
      expect(screen.getByText("No matching gaps")).toBeInTheDocument()
    })
  })
})
