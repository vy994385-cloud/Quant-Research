import { describe, expect, it, vi } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { fetchUniverseRankings } from "../api/client"
import { RESEARCH, UNIVERSE } from "../test/fixtures"
import RankingsPanel from "./RankingsPanel"

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>()
  return {
    ...actual,
    fetchUniverseRankings: vi.fn(),
  }
})

const mockedFetchUniverse = vi.mocked(fetchUniverseRankings)

describe("RankingsPanel", () => {
  it("renders the three company horizon rankings", () => {
    render(<RankingsPanel data={RESEARCH} />)

    const panel = screen.getByText("Company rankings").closest("section")!

    expect(within(panel).getByText("Intraday")).toBeInTheDocument()
    expect(within(panel).getByText("Swing")).toBeInTheDocument()
    expect(within(panel).getByText("Long Term")).toBeInTheDocument()
  })

  it("flags degraded rankings with missing evidence", () => {
    render(<RankingsPanel data={RESEARCH} />)

    expect(
      screen.getByText(/Missing evidence: Future Readiness, Ai Participation/),
    ).toBeInTheDocument()
  })

  it("switches to the universe comparison and fetches rankings", async () => {
    mockedFetchUniverse.mockResolvedValue(UNIVERSE)

    const user = userEvent.setup()
    render(<RankingsPanel data={RESEARCH} />)

    await user.click(screen.getByText("Universe comparison"))

    expect(await screen.findByText(/As of 2026-08-10T12:00:00\+00:00/)).toBeInTheDocument()

    expect(mockedFetchUniverse).toHaveBeenCalledWith("LONG_TERM")
    expect(screen.getByText("Tata Consultancy Services")).toBeInTheDocument()
  })

  it("supports switching the universe horizon", async () => {
    mockedFetchUniverse.mockResolvedValue(UNIVERSE)

    const user = userEvent.setup()
    render(<RankingsPanel data={RESEARCH} />)

    await user.click(screen.getByText("Universe comparison"))
    await user.click(screen.getByText("Swing"))

    expect(mockedFetchUniverse).toHaveBeenLastCalledWith("SWING")
  })
})
