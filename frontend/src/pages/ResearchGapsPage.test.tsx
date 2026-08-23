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

async function selectTCS() {
  await waitFor(() => {
    expect(screen.getByText("TCS")).toBeInTheDocument()
  })
  fireEvent.click(screen.getByText("TCS"))
  await waitFor(() => {
    expect(mockFetchResearchGaps).toHaveBeenCalledWith("TCS")
  })
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe("ResearchGapsPage", () => {
  it("renders the page hero", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Research Gaps & Coverage")).toBeInTheDocument()
    })
  })

  it("shows loading state initially", () => {
    renderPage()
    expect(screen.getByText("Loading research gap data")).toBeInTheDocument()
  })

  it("loads company list after discovery", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("TCS")).toBeInTheDocument()
    })
    expect(screen.getByText("Tata Consultancy Services")).toBeInTheDocument()
  })

  it("shows coverage summary with gap count after selecting company", async () => {
    renderPage()
    await selectTCS()
    await waitFor(() => {
      expect(screen.getByText("gaps")).toBeInTheDocument()
    })
  })

  it("shows missing evidence count in summary", async () => {
    renderPage()
    await selectTCS()
    await waitFor(() => {
      expect(screen.getByText("missing")).toBeInTheDocument()
    })
    expect(screen.getByText("stale")).toBeInTheDocument()
  })

  it("shows domain coverage section after selecting company", async () => {
    renderPage()
    await selectTCS()
    await waitFor(() => {
      expect(screen.getByText("Domain Coverage")).toBeInTheDocument()
    })
  })

  it("renders missing evidence section", async () => {
    renderPage()
    await selectTCS()
    await waitFor(() => {
      expect(screen.getByText("Missing Evidence")).toBeInTheDocument()
    })
  })

  it("renders stale evidence section", async () => {
    renderPage()
    await selectTCS()
    await waitFor(() => {
      expect(screen.getByText("Stale Evidence")).toBeInTheDocument()
    })
  })

  it("renders gap details section", async () => {
    renderPage()
    await selectTCS()
    await waitFor(() => {
      expect(screen.getByText("Gap Details")).toBeInTheDocument()
    })
  })

  it("displays empty state when no company selected", async () => {
    mockFetchDiscovery.mockResolvedValue({ count: 0, results: [] })
    render(
      <MemoryRouter initialEntries={["/research-gaps"]}>
        <ResearchGapsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText("Select companies to view research gaps")).toBeInTheDocument()
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
    await selectTCS()
    await waitFor(() => {
      expect(screen.getByText("No matching gaps")).toBeInTheDocument()
    })
  })
})
