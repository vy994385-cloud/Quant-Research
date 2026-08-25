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
  it("renders the primary side navigation", async () => {
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)
    mockedFetchResearch.mockResolvedValue(RESEARCH)
    // "/" redirects into the Discover page.
    const { container } = renderAtRoute("/")
    expect(screen.getByText("Quant Research")).toBeInTheDocument()
    // The lazy-loaded page resolves async, so await the page heading first.
    await screen.findByRole("heading", { name: /What.*new in the research universe/ })
    // Nav links are scoped to the side navigation: once page data resolves,
    // the page body legitimately contains the same words.
    const sideNav = container.querySelector<HTMLElement>(".side-nav")!
    // "Discover" and "Evidence" name both a nav group and a page link.
    expect(within(sideNav).getAllByText("Discover").length).toBeGreaterThanOrEqual(1)
    expect(within(sideNav).getByText("Companies")).toBeInTheDocument()
    expect(within(sideNav).getByText("Industries")).toBeInTheDocument()
    expect(within(sideNav).getByText("Themes")).toBeInTheDocument()
    expect(within(sideNav).getByText("Watchlists")).toBeInTheDocument()
    expect(within(sideNav).getByText("Compare")).toBeInTheDocument()
    expect(within(sideNav).getAllByText("Evidence").length).toBeGreaterThanOrEqual(1)
  })

  it("renders the Discover page with discovery data", async () => {
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)
    mockedFetchResearch.mockResolvedValue(RESEARCH)
    renderAtRoute("/discover")

    expect(
      await screen.findByText("Tata Consultancy Services"),
    ).toBeInTheDocument()
    expect(screen.getByText("Infosys")).toBeInTheDocument()
  })

  it("renders the company workspace with tabbed sections", async () => {
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)
    mockedFetchResearch.mockResolvedValue(RESEARCH)
    renderAtRoute("/companies/TCS")

    expect(
      await screen.findByRole("heading", { name: "Tata Consultancy Services" }),
    ).toBeInTheDocument()

    // Overview is the default tab: composed dashboard blocks only —
    // no full evidence tables or coverage matrices on first paint.
    expect(screen.getByText("Research snapshot")).toBeInTheDocument()
    expect(screen.queryByText("Evidence Record")).not.toBeInTheDocument()
    expect(screen.queryByText("Data Coverage")).not.toBeInTheDocument()

    // Financials tab
    fireEvent.click(screen.getByRole("tab", { name: "Financials" }))
    expect(await screen.findByText("Financial Performance")).toBeInTheDocument()

    // Evidence tab: dated evidence record. Titles render sentence-cased
    // with the symbol prefix stripped.
    fireEvent.click(screen.getByRole("tab", { name: "Evidence" }))
    expect(await screen.findByText("Evidence Record")).toBeInTheDocument()
    expect(
      screen.getAllByText("Board meeting scheduled for June").length,
    ).toBeGreaterThanOrEqual(1)

    // Business tab carries the derived observations register — titles render
    // as recorded (sentence case).
    fireEvent.click(screen.getByRole("tab", { name: "Business" }))
    expect(
      await screen.findAllByText("Increasing revenue").then((matches) => matches.length),
    ).toBeGreaterThan(0)

    // Provenance tab renders humanised source labels; raw identifiers
    // survive only in the technical provenance lineage records below.
    fireEvent.click(screen.getByRole("tab", { name: "Provenance" }))
    expect(await screen.findByText("Recorded Intel Sources")).toBeInTheDocument()
    expect(screen.getByText("Market source record")).toBeInTheDocument()
    expect(screen.getAllByText("Yahoo Finance Market").length).toBeGreaterThanOrEqual(1)

    // Coverage tab: structured data coverage matrix
    fireEvent.click(screen.getByRole("tab", { name: "Coverage" }))
    expect(await screen.findByText("Data Coverage")).toBeInTheDocument()

    expect(mockedFetchResearch).toHaveBeenCalledWith("TCS")
  })

  it("shows the loading state while research is pending", async () => {
    let resolveResearch!: (value: CompanyResearch) => void

    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)
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
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)
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
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)
    mockedFetchResearch.mockResolvedValue(DEGRADED_RESEARCH)
    renderAtRoute("/companies/TCS")

    // Overview surfaces the PIT warning without digging through tabs
    await screen.findByRole("heading", { name: "Tata Consultancy Services" })
    expect(
      await screen.findByText(
        "Point-in-time checks did not all pass for this snapshot; review evidence timestamps with extra caution.",
      ),
    ).toBeInTheDocument()

    // Structured data coverage lives in the Coverage tab
    fireEvent.click(screen.getByRole("tab", { name: "Coverage" }))
    expect(await screen.findByText("Data Coverage")).toBeInTheDocument()

    // Provider failures are listed inside the expandable Missing group
    fireEvent.click(screen.getByRole("button", { name: /Missing/ }))
    expect(
      screen.getByText(
        "2 research providers failed and were isolated from this snapshot (missing-sources-provider, missing-intel-provider)",
      ),
    ).toBeInTheDocument()
  })
})
