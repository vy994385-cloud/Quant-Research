import { describe, expect, it, vi } from "vitest"
import { render, screen, fireEvent, within } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { ApiError, fetchDiscovery, fetchResearch } from "./api/client"
import type { CompanyResearch } from "./api/types"
import { DEGRADED_RESEARCH, DISCOVERY, RESEARCH } from "./test/fixtures"
import { AppRoutes } from "./App"
import { DiscoveryProvider } from "./DiscoveryContext"

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

function renderAtRoute(route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <DiscoveryProvider>
        <AppRoutes />
      </DiscoveryProvider>
    </MemoryRouter>,
  )
}
describe("App", () => {
  it("renders the sidebar navigation", async () => {
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)
    const { container } = renderAtRoute("/")
    expect(screen.getByText("Quant Research")).toBeInTheDocument()
    // The lazy-loaded page resolves async, so await the page heading first.
    await screen.findByRole("heading", { name: "Research Home" })
    // Nav links are scoped to the sidebar navigation: once the home data
    // resolves, the page body legitimately contains the same words.
    const sidebarNav = container.querySelector<HTMLElement>(".sidebar-nav")!
    expect(within(sidebarNav).getByText("Research Home")).toBeInTheDocument()
    expect(within(sidebarNav).getByText("Companies")).toBeInTheDocument()
    expect(within(sidebarNav).getByText("Industries")).toBeInTheDocument()
    expect(within(sidebarNav).getByText("Themes")).toBeInTheDocument()
    expect(within(sidebarNav).getByText("Signals")).toBeInTheDocument()
    expect(within(sidebarNav).getByText("Compare")).toBeInTheDocument()
    expect(within(sidebarNav).getByText("Evidence")).toBeInTheDocument()
  })

  it("renders the Research Home page with discovery data", async () => {
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)
    renderAtRoute("/")

    expect(
      await screen.findByText("Tata Consultancy Services"),
    ).toBeInTheDocument()
    expect(screen.getByText("Infosys")).toBeInTheDocument()
  })

  it("renders the full company research dashboard via route", async () => {
    mockedFetchResearch.mockResolvedValue(RESEARCH)
    renderAtRoute("/companies/TCS")

    expect(
      await screen.findByRole("heading", { name: "Tata Consultancy Services" }),
    ).toBeInTheDocument()

    // Research overview
    expect(screen.getByText("Research Overview")).toBeInTheDocument()

    // Evidence record with dated timeline entries. The newest entry also
    // appears in the overview "What changed" summary, hence getAllByText.
    // Titles render sentence-cased with the symbol prefix stripped.
    expect(screen.getByText("Evidence Record")).toBeInTheDocument()
    expect(
      screen.getAllByText("Board meeting scheduled for June").length,
    ).toBeGreaterThanOrEqual(1)

    // Derived observations register — titles render as recorded (sentence case).
    expect(screen.getAllByText("Increasing revenue").length).toBeGreaterThan(0)

    // Source coverage table renders humanised source labels; raw identifiers
    // survive only in the technical provenance lineage records below.
    expect(
      screen.getAllByText("Recorded Intel Sources").length,
    ).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("Market source record")).toBeInTheDocument()
    expect(screen.getAllByText("yahoo_finance_market").length).toBeGreaterThanOrEqual(1)

    // Structured data coverage section
    expect(screen.getByText("Data Coverage")).toBeInTheDocument()

    expect(mockedFetchResearch).toHaveBeenCalledWith("TCS")
  })

  it("shows the loading state while research is pending", async () => {
    let resolveResearch!: (value: CompanyResearch) => void

    mockedFetchResearch.mockImplementation(
      () =>
        new Promise<CompanyResearch>((resolve) => {
          resolveResearch = resolve
        }),
    )

    renderAtRoute("/companies/TCS")

    expect(
      await screen.findByText(/Retrieving research data/),
    ).toBeInTheDocument()

    resolveResearch(RESEARCH)

    expect(
      await screen.findByRole("heading", { name: "Tata Consultancy Services" }),
    ).toBeInTheDocument()
  })

  it("renders the structured error contract on failure", async () => {
    mockedFetchResearch.mockRejectedValue(
      new ApiError("Unsupported company", "unknown_company", 404, {
        symbol: "TCS",
      }),
    )

    renderAtRoute("/companies/TCS")

    expect(
      await screen.findByText("Unsupported company"),
    ).toBeInTheDocument()
    expect(screen.getByText("Error code: unknown_company")).toBeInTheDocument()
  })

  it("surfaces degraded research context", async () => {
    mockedFetchResearch.mockResolvedValue(DEGRADED_RESEARCH)
    renderAtRoute("/companies/TCS")

    // Structured data coverage replaces warning banners
    expect(await screen.findByText("Data Coverage")).toBeInTheDocument()

    // Provider failures are listed inside the expandable Missing group
    fireEvent.click(screen.getByRole("button", { name: /Missing/ }))
    expect(
      screen.getByText(
        "2 research providers failed and were isolated from this snapshot (missing-sources-provider, missing-intel-provider)",
      ),
    ).toBeInTheDocument()

    expect(
      screen.getByText(
        "Point-in-time checks did not all pass for this snapshot; review evidence timestamps with extra caution.",
      ),
    ).toBeInTheDocument()
  })
})
