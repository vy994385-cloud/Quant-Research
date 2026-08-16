import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ApiError, fetchDiscovery, fetchResearch } from "./api/client"
import type { CompanyResearch } from "./api/types"
import { DEGRADED_RESEARCH, DISCOVERY, RESEARCH } from "./test/fixtures"
import App from "./App"

vi.mock("./api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api/client")>()
  return {
    ...actual,
    fetchDiscovery: vi.fn(),
    fetchResearch: vi.fn(),
  }
})

const mockedFetchDiscovery = vi.mocked(fetchDiscovery)
const mockedFetchResearch = vi.mocked(fetchResearch)

async function selectCompany(symbol: string) {
  const user = userEvent.setup()
  const input = screen.getByLabelText("Company search")

  await user.type(input, symbol)
  await user.click(await screen.findByText(symbol))

  return user
}

describe("App", () => {
  it("starts with an empty research state", () => {
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)
    mockedFetchResearch.mockResolvedValue(RESEARCH)

    render(<App />)

    expect(
      screen.getByText("Start company research"),
    ).toBeInTheDocument()
  })

  it("renders the full research dashboard after selecting a company", async () => {
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)
    mockedFetchResearch.mockResolvedValue(RESEARCH)

    render(<App />)
    await selectCompany("TCS")

    // Company identity + as-of bar
    expect(
      await screen.findByText("Tata Consultancy Services"),
    ).toBeInTheDocument()
    expect(screen.getByLabelText("Point-in-time as-of date")).toBeInTheDocument()

    // Overview
    expect(screen.getByText("OVERALL CONCLUSION")).toBeInTheDocument()
    expect(
      screen.getByText("TCS shows a predominantly positive research profile across the available evidence."),
    ).toBeInTheDocument()

    // Rankings
    expect(screen.getByText("Intraday")).toBeInTheDocument()

    // Evidence
    expect(screen.getAllByText("Supporting evidence").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Rising Debt Trend").length).toBeGreaterThan(0)

    // Trends + signals
    expect(screen.getByText("Financial trends component")).toBeInTheDocument()
    expect(screen.getAllByText("Increasing revenue").length).toBeGreaterThan(0)

    // Risks
    expect(screen.getByText("Negative evidence & exceptions")).toBeInTheDocument()

    // Intelligence
    expect(screen.getByText("Business quality")).toBeInTheDocument()

    // Timeline + research status
    expect(screen.getByText("Company evidence timeline")).toBeInTheDocument()
    expect(
      screen.getByText("TCS ANNUAL financials for the period ending 2026-03-31"),
    ).toBeInTheDocument()
    expect(screen.getByText("Freshness")).toBeInTheDocument()

    // Deep financial insights
    expect(screen.getByText("Deep financial insights")).toBeInTheDocument()

    // Source statuses
    expect(screen.getByText("Source statuses")).toBeInTheDocument()
    expect(screen.getAllByText("recorded_intel_sources").length).toBeGreaterThan(0)

    // Sources, provenance, and point-in-time
    expect(screen.getByText("Point-in-time context")).toBeInTheDocument()
    expect(screen.getByText("PIT CHECKS PASSED")).toBeInTheDocument()
    expect(screen.getByText("Market source")).toBeInTheDocument()
    expect(screen.getByText("yahoo_finance_chart")).toBeInTheDocument()

    expect(mockedFetchResearch).toHaveBeenCalledWith("TCS", undefined)
  })

  it("shows the loading state while research is pending", async () => {
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)

    let resolveResearch!: (value: CompanyResearch) => void

    mockedFetchResearch.mockImplementation(
      () =>
        new Promise<CompanyResearch>((resolve) => {
          resolveResearch = resolve
        }),
    )

    render(<App />)
    await selectCompany("TCS")

    expect(
      await screen.findByText("Loading research"),
    ).toBeInTheDocument()

    resolveResearch(RESEARCH)

    expect(
      await screen.findByText("Tata Consultancy Services"),
    ).toBeInTheDocument()
  })

  it("renders the structured error contract on failure", async () => {
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)
    mockedFetchResearch.mockRejectedValue(
      new ApiError("Unsupported company", "unknown_company", 404, {
        symbol: "TCS",
      }),
    )

    render(<App />)
    await selectCompany("TCS")

    expect(
      await screen.findByText("Unsupported company"),
    ).toBeInTheDocument()
    expect(screen.getByText("Error code: unknown_company")).toBeInTheDocument()
  })

  it("surfaces degraded research context", async () => {
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)
    mockedFetchResearch.mockResolvedValue(DEGRADED_RESEARCH)

    render(<App />)
    await selectCompany("TCS")

    expect(
      await screen.findByText("Degraded research context"),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        "1 research source provider(s) failed and were isolated from this report.",
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        "1 intelligence source provider(s) failed and were isolated from this snapshot.",
      ),
    ).toBeInTheDocument()
    expect(screen.getByText("PIT CHECKS FAILED")).toBeInTheDocument()
  })
})
